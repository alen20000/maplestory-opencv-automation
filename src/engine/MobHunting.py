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
        self.min_threshold = config.get("image_processing.mob_min_threshold")
        self.mobs_in_map =  config.get(f"map.{Map_Name}")
        self.nms_threshold = 0.7 # <- NMS 阈值
        #放匹配模板字典
        self.mobs_templates: dict[str, np.ndarray] = {}
        self._load_mob_templates()

        cv2.setNumThreads(1)

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

            results = executor.map(process_template, self.mobs_templates.items())
            for res in results:
                all_detected_boxes.extend(res)

        result = self._nms_filter(all_detected_boxes)
        return result

    def _pix_filter_method(self,all_detected_boxes:list):

        '''
        過濾方法:中心距離閾值過濾法
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

    def _nms_filter(self,all_detected_boxes:list):
        '''
        過濾方法:NMS方法
        '''
        if not all_detected_boxes:
            return []
        #先以分數大至小排序
        sorted_boxes = sorted(all_detected_boxes, key=lambda x: x["score"], reverse=True)
        
        final_filtered_boxes = []
        mobs_by_name = {}

        for box in sorted_boxes:
            name = box["mob_name"]
            if name not in mobs_by_name:
                mobs_by_name[name] = []
            mobs_by_name[name].append(box)

            #要先解開 怪物 與 目標資訊
        for mob_name, boxes in mobs_by_name.items():
            mob_sorted_boxes = sorted(boxes, key=lambda x: x["score"], reverse=True)
            matching_boxes = []

            for i in mob_sorted_boxes:
                keep = True

                i_x1,i_y1 = i["top_left"]
                i_x2,i_y2 =i_x1 + i["size"][0], i_y1 + i["size"][1]
                area_i = (i_x2 - i_x1) * (i_y2 - i_y1)

                for target in  matching_boxes:

                    t_x1, t_y1 = target["top_left"]
                    t_x2, t_y2 = t_x1 + target["size"][0], t_y1 + target["size"][1]
                    area_target = (t_x2 - t_x1) * (t_y2 - t_y1)

                    #交集計算
                    inter_x1 = max(t_x1, i_x1)
                    inter_y1 = max(t_y1, i_y1)
                    inter_x2 = min(t_x2, i_x2)
                    inter_y2 = min(t_y2, i_y2)

                    inter_w  = max(0, inter_x2 - inter_x1)
                    inter_h  = max(0, inter_y2 - inter_y1)
                    inter_area = inter_w * inter_h

                    #併集計算
                    union_are = area_target + area_i - inter_area


                    if union_are > 0:
                        iou = inter_area / union_are
                    else:
                        iou = 0

                    # 如果重疊度大於阈值，則過濾出去
                    if iou >= self.nms_threshold:
                        keep = False
                        break
                if keep:
                    matching_boxes.append(i)
            final_filtered_boxes.extend(matching_boxes)
        final_mobs_dict = {}
        for box in final_filtered_boxes:
            mob_name = box["mob_name"]
            if mob_name not in final_mobs_dict:
                final_mobs_dict[mob_name] = []
            final_mobs_dict[mob_name].append(box)

        all_mobs_locs = [(mob_name, boxes) for mob_name, boxes in final_mobs_dict.items() if boxes]
        return all_mobs_locs