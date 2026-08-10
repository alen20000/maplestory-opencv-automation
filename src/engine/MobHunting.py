import yaml
import os
import cv2
import numpy as np
from config.config_loader import config 
import logging
from src.utils.common import cent_coord
import time
from concurrent.futures import ThreadPoolExecutor
'''
mob template resource :https://maplestory.wiki/GMS/65/mob/100101

'''

class MobDetector:
    def __init__(self):
        #Config
        Map_Name = config.get("quickly_choice_map")
        self.min_threshold = config.get("image_processing.min_threshold")
        self.mobs_in_map =  config.get(f"map.{Map_Name}")

        #放匹配模板字典
        self.mobs_templates: dict[str, np.ndarray] = {}
        self._load_mob_templates()

    def _load_mob_templates(self):
        '''
        從路徑資料夾讀取匹配怪物模板後存入字典
        key:mob ID ;value:img
        '''
        if not os.path.exists(self.mobs_in_map):
            logging.info(f"{self.mobs_in_map} 地圖不存在")
            return

        for mobs in os.listdir(self.mobs_in_map):
            if mobs.lower().endswith("png"):
                img_path = os.path.join(self.mobs_in_map, mobs)
                mob_name = os.path.splitext(mobs)[0]

                mob_img = cv2.imread(img_path,cv2.IMREAD_GRAYSCALE)
                if mob_img is not None:
                    self.mobs_templates[mob_name] = mob_img

    def run(self):
        self._load_mob_templates()

    def searching_mob(self, crop_frame_gray):
        '''
        接收ROI範圍畫面與範圍座標
        回傳怪物座標
        '''
        all_detected_boxes = []

        # 定義單一模板的處理函式（包含原圖與翻轉）
        def process_template(item):
            mob_name, img = item
            h, w = img.shape[:2]
            flipped_img = cv2.flip(img, 1)
            boxes = []
            # start = time.time()
            # [原圖樣版比對]
            matches_normal = cv2.matchTemplate(crop_frame_gray, img, cv2.TM_CCOEFF_NORMED)
            loc_n = np.where(matches_normal >= self.min_threshold)
            for y, x in zip(loc_n[0], loc_n[1]):
                boxes.append({
                    "mob_name": mob_name,
                    "top_left" : (int(x), int(y)),
                    "center" : cent_coord((int(x), int(y)),(w, h)),
                    "size" : (w, h),
                    "score" : float(matches_normal[y, x])
                })

            # print(f"{mob_name} 耗時: {time.time() - start:.3f}")
            # [翻轉比對]
            matches_flipped = cv2.matchTemplate(crop_frame_gray, flipped_img, cv2.TM_CCOEFF_NORMED)
            loc_f = np.where(matches_flipped >= self.min_threshold)
            for y, x in zip(loc_f[0], loc_f[1]):
                boxes.append({
                    "mob_name": mob_name,
                    "top_left" : (int(x), int(y)),
                    "center" : cent_coord((int(x), int(y)),(w, h)),
                    "size" : (w, h),
                    "score" : float(matches_flipped[y, x])
                })
            return boxes

        # 使用執行緒池並行處理所有模板
        with ThreadPoolExecutor() as executor:
            # executor.map 會把 self.mobs_templates.items()  توزيع到多個執行緒同時運算
            results = executor.map(process_template, self.mobs_templates.items())
            for res in results:
                all_detected_boxes.extend(res)

        '''
        NMS core
        先簡單用硬像素距離判斷
        '''
        #封包用
        all_mobs_locs =[]
        #比對用
        final_mobs_dict = {}
        
        for box in all_detected_boxes:
            mob_name = box["mob_name"]
            cx, cy = box["center"]
            
            if mob_name not in final_mobs_dict:
                final_mobs_dict[mob_name] = []

            # 檢查是否跟已經被收錄的同種類怪物距離太近
            is_dup = False
            for existing in final_mobs_dict[mob_name]:
                ex_cx, ex_cy = existing["center"]
                # 如果中心點距離小於 25 像素，視為同一隻怪物的重複殘影，直接過濾掉
                if abs(cx - ex_cx) < 25 and abs(cy - ex_cy) < 25:
                    is_dup = True
                    break

            if not is_dup:

                final_mobs_dict[mob_name].append(box)
        all_mobs_locs = [(mob_name, boxes) for mob_name, boxes in final_mobs_dict.items() if boxes]
        return all_mobs_locs

