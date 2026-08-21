import logging
from config.config_loader import config
import cv2
import numpy as np


class HealthDetector():
    """

    量測記錄：
        螢幕解析度:2560 x 1600；DPI倍率:125% 之下之座標

        HP bar: (503, 751, 608, 754)
        MP bar: (611, 751, 716, 754)
    """

    def __init__(self):

        #優先讀 config，沒設定就用量測好的預設值
        self.hp_bar_loc = tuple(config.get("health_detector.hp_bar_loc", (503, 751, 608, 754)))
        self.mp_bar_loc = tuple(config.get("health_detector.mp_bar_loc", (611, 751, 716, 754)))

        #Bar顏色範圍(HSV)
        self.lower_hp_color = config.get("health_detector.lower_hp_color")
        self.upper_hp_color = config.get("health_detector.upper_hp_color")
        self.lower_mp_color = config.get("health_detector.lower_mp_color")
        self.upper_mp_color = config.get("health_detector.upper_mp_color")

    def run(self, frame: np.ndarray):
        hp_status = self.hp_detect(frame)
        mp_status = self.mp_detect(frame)
        return hp_status, mp_status

    def hp_detect(self, frame: np.ndarray):
        '''
        偵測血量
        '''
        x1, y1, x2, y2 = self.hp_bar_loc
        crop_frame = frame[y1:y2, x1:x2]
        hsv_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2HSV)
        max_hp = crop_frame.shape[1]

        #雖然楓之谷大概沒有光汙問題，但還是做一下，
        lower_bound = np.array(self.lower_hp_color, dtype=np.uint8)
        upper_bound = np.array(self.upper_hp_color, dtype=np.uint8)
        mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)

        # axis=0 把垂直方向有True則True，把多排matrix壓成一排
        hp_remain = np.any(mask > 0, axis=0)
        # 把True的數量算出來，得到目前血量
        hp_remain = np.count_nonzero(hp_remain)

        return round(hp_remain / max_hp * 100, 1)

    def mp_detect(self, frame: np.ndarray):
        '''
        跟上面差不多
        '''
        x1, y1, x2, y2 = self.mp_bar_loc
        crop_frame = frame[y1:y2, x1:x2]
        hsv_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2HSV)
        max_mp = crop_frame.shape[1]

        lower_bound = np.array(self.lower_mp_color, dtype=np.uint8)
        upper_bound = np.array(self.upper_mp_color, dtype=np.uint8)
        mask = cv2.inRange(hsv_frame, lower_bound, upper_bound)

        mp_remain = np.any(mask > 0, axis=0)
        mp_remain = np.count_nonzero(mp_remain)

        return round(mp_remain / max_mp * 100, 1)


if __name__ == "__main__":
    run = HealthDetector()
    run.run()