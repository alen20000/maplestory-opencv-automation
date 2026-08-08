import yaml
import os
import cv2
import numpy as np
from config.config_loader import config 
import logging

'''
嘗試用
TM_SQDIFF_NORMED、MASK 以及NMS匹配。 但是很效果不好
'''

class MobDetector:
    def __init__(self):
        #Config
        self.min_threshold = config.get("image_processing.min_threshold")
        self.max_threshold = config.get("image_processing.max_threshold")
        self.mobs_in_map =  config.get("map.test_map")
        #放匹配模板字典
        self.mobs_templates: dict[str, np.ndarray] = {}
        self.mobs_gray_templates: dict[str, np.ndarray] = {}
        self.mobs_masks: dict[str, np.ndarray] = {}

    def _mask_match_mode(self,template_bgr: np.ndarray):
        '''
        Input: bgr圖片
        Output: masked 灰階圖片
        '''
        try:
            img_hsv = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2HSV)
            lower= np.array([35, 43, 46])  # 綠色下限
            upper = np.array([77, 255, 255])  # 綠色上限
            mask = cv2.inRange(img_hsv, lower, upper)
            mask = cv2.bitwise_not(mask)
            if np.count_nonzero(mask) == 0:
                print(
                    "[警告] 發現有圖片完全沒有綠幕背景！請檢查資料夾內的圖片是否符合格式"
                    "。"
                )

            return mask
        except Exception as e:
            logging.error(f"mask_match_mode 發生例外錯誤: {e}")
            return

    def _load_mob_templates(self):
        '''
        從路徑資料夾讀取模板，並【在這裡一次性算好】灰階與 Mask，不要在迴圈裡重複算！
        '''
        if not os.path.exists(self.mobs_in_map):
            return

        #遍歷載入怪物模板
        for mobs in os.listdir(self.mobs_in_map):
            if mobs.lower().endswith("png"):
                img_path = os.path.join(self.mobs_in_map, mobs)
                mob_name = os.path.splitext(mobs)[0]

                mob_img = cv2.imread(img_path,cv2.IMREAD_COLOR)
                if mob_img is not None:
                    self.mobs_templates[mob_name] = mob_img
                    self.mobs_gray_templates[mob_name] = cv2.cvtColor(
                        mob_img, cv2.COLOR_BGR2GRAY
                    )
                    self.mobs_masks[mob_name] = self._mask_match_mode(mob_img)

    def run(self):
        self._load_mob_templates()

    def searching_mob(self,crop_frame_gray):
        '''
        input: crop_frame_gray from gamebot
        returen: mob location
        '''

        #加載mob模板:BGR、Gray、Mask
        if not self.mobs_templates:
            self._load_mob_templates()

        all_mobs_locs = []
        #輪尋查怪
        try:
            for mob_name, img in self.mobs_templates.items():
                
                #過濾無效mask
                mask = self.mobs_masks.get(mob_name)
                if mask is None or np.count_nonzero(mask) == 0:
                    logging.warning(f"{mob_name} 的 mask 無效,跳過此模板")
                    continue

                template_gray = self.mobs_gray_templates[mob_name]
                h, w = template_gray.shape[:2]

                # 1.原圖樣版
                matches = cv2.matchTemplate(
                    crop_frame_gray, 
                    self.mobs_gray_templates[mob_name],
                    cv2.TM_SQDIFF_NORMED,
                    mask=mask
                    )
                locs_normal = self._extract_locations(matches, w, h)

                # 2.翻轉圖樣
                flipped_template_gray = cv2.flip(template_gray, 1)
                flipped_mob_template_mask= cv2.flip(mask, 1)
                matches_flipped = cv2.matchTemplate(
                    crop_frame_gray,
                    flipped_template_gray,
                    cv2.TM_SQDIFF_NORMED,
                    mask=flipped_mob_template_mask
                    )
                locs_flipped = self._extract_locations(matches_flipped, w, h)
                print(f"{mob_name} normal: {locs_normal}, flipped: {locs_flipped}")
                combined_locs = locs_normal + locs_flipped

                # 如果合併後有任何座標，就塞進回傳清單裡
                if combined_locs:
                    all_mobs_locs.append((mob_name, combined_locs))

            return all_mobs_locs

        except Exception as e:
            logging.error(f"尋怪異常:{e}")
            return
        
    def _extract_locations(self, matches, tmpl_w, tmpl_h):
        '''
        從相似度矩陣中取出候選點，並做 NMS 去除同一隻怪物周圍的重疊點
        SQDIFF_NORMED: 分數越低越相似，所以用 <=
        '''
        loc = np.where(matches <= self.max_threshold)
        if len(loc[0]) == 0:
            return []

        candidates = list(zip(loc[1], loc[0]))  # (x, y)
        scores = matches[loc[0], loc[1]]

        return self._nms(candidates, scores, tmpl_w, tmpl_h)

    def _nms(self, points, scores, tmpl_w, tmpl_h, overlap_thresh=0.3):
        '''
        簡易 NMS：分數越低（越像）優先保留，移除與其重疊過多的其他候選點
        '''
        if not points:
            return []

        points = np.array(points)
        scores = np.array(scores)

        # 分數越低越好，所以由小到大排序
        order = np.argsort(scores)

        x1 = points[:, 0]
        y1 = points[:, 1]
        x2 = x1 + tmpl_w
        y2 = y1 + tmpl_h
        areas = tmpl_w * tmpl_h

        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(tuple(points[i]))

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            inter = w * h
            iou = inter / areas

            remaining = np.where(iou <= overlap_thresh)[0]
            order = order[remaining + 1]

        return keep