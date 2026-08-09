import yaml
import os
import cv2
import numpy as np
from config.config_loader import config 
import logging
from src.utils.common import cent_coord
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

    def searching_mob(self,crop_frame_gray):
        '''
        接收ROI範圍畫面與範圍座標
        回傳怪物座標
        '''

        all_detected_boxes = []
        #輪尋查怪
        for mob_name, img in self.mobs_templates.items():
            h, w = img.shape[:2] # 取得模板高與寬 (注意尺寸是 h, w，但傳入要對應 x, y)

            # 1.原圖樣版
            matches = cv2.matchTemplate(crop_frame_gray, img, cv2.TM_CCOEFF_NORMED)
            loc = np.where(matches >= self.min_threshold)
            # 這裡是做矩陣翻轉，來得到正確的x,y   
            loc_normal = list(zip(loc[1], loc[0]))

            # 樣板左右翻轉， 這原理只是做矩陣變換，不太會消耗很多運算
            flipped_img = cv2.flip(img, 1)
            matches_flipped = cv2.matchTemplate(crop_frame_gray, flipped_img, cv2.TM_CCOEFF_NORMED)
            loc_f = np.where(matches_flipped >= self.min_threshold)
            loc_flipped = list(zip(loc_f[1], loc_f[0]))

            # 把正常方向與翻轉方向找到的座標全部合併在一起
            combined_locs = loc_normal + loc_flipped

            # 如果合併後有任何座標，就塞進回傳清單裡
            if combined_locs:
                mob_detail = []
                for pt in combined_locs:
                    x1 ,y1 = int(pt[0]), int(pt[1])

                    center_x, center_y = cent_coord((x1, y1),(w, h))
                    all_detected_boxes.append({
                        "mob_name": mob_name,
                        "top_left" : (x1, y1),
                        "center" : (center_x, center_y),
                        "size" : (w, h)
                    })
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

