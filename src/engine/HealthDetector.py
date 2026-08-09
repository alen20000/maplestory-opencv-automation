import cv2
import logging
from config.config_loader import config
from src.utils.common import draw_dectection_box
import numpy as np
class HealthDetector():
    def __init__(self) -> None:
        #HP
        self.hp_bar = config.get("health_detector.hp_lect")
        #血條顏色範圍(HSV)
        self.lower_hp_color = config.get("health_detector.lower_hp_color")
        self.upper_hp_color = config.get("health_detector.upper_hp_color")
    def run(self, frame:np.ndarray):
        '''
        接收:current_frame
        輸出:
        '''
        # print(self.hp_bar)
        # print(type(frame))
        x1 , y1 ,x2 , y2 = self.hp_bar[0], self.hp_bar[1], self.hp_bar[2], self.hp_bar[3]
        crop_frame = frame[y1:y2, x1:x2]
        hsv_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2HSV)

        #雖然楓之谷大概沒有光汙問題，但還是做一下
        mask = cv2.inRange(hsv_frame, self.lower_hp_color, self.upper_hp_color)

        #測試用
        list = x1 , y1 ,x2 , y2
        return list