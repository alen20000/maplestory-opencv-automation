import cv2
import logging
from config.config_loader import config
from src.utils.common import draw_dectection_box
import numpy as np
class HealthDetector():
    def __init__(self):
        #HP&MP Bar範圍
        self.hp_bar_loc = None
        self.mp_bar_loc = None
        #Bar顏色範圍(HSV)
        self.lower_hp_color = config.get("health_detector.lower_hp_color")
        self.upper_hp_color = config.get("health_detector.upper_hp_color")
        self.lower_mp_color = config.get("health_detector.lower_mp_color")
        self.upper_mp_color = config.get("health_detector.upper_mp_color")
        #temaplate
        self.hp_bar_template = config.get("health_detector.hp_bar_template")
        self.mp_bar_template = config.get("health_detector.mp_bar_template")
    def _fetch_bar_lt_loc(self,frame:np.ndarray):
        """
        抓取健康條的範圍
        """
        try:
            hp_img = cv2.imread(self.hp_bar_template)
            mp_img = cv2.imread(self.mp_bar_template)

            hp_result = cv2.matchTemplate(frame, hp_img ,cv2.TM_CCOEFF_NORMED)
            mp_result = cv2.matchTemplate(frame, mp_img ,cv2.TM_CCOEFF_NORMED)
            _, hp_max_val, _, hp_max_loc = cv2.minMaxLoc(hp_result)
            _, mp_max_val, _, mp_max_loc = cv2.minMaxLoc(mp_result)
            if hp_max_val > 0.6:
                #寬度正常；高度抓3像素
                _, hp_img_w = hp_img.shape[:2]
                self.hp_bar_loc = hp_max_loc[0], hp_max_loc[1], hp_max_loc[0]+hp_img_w, hp_max_loc[1]+3

            if mp_max_val > 0.6:
                _, mp_img_w = mp_img.shape[:2]
                self.mp_bar_loc = mp_max_loc[0], mp_max_loc[1], mp_max_loc[0]+mp_img_w, mp_max_loc[1]+3


        except Exception as e:
            logging.error(f"抓取狀態欄錯誤:{e}")



    def run(self,frame:np.ndarray):

        self._fetch_bar_lt_loc(frame)
        hp_status = self.hp_detect(frame)
        mp_status = self.mp_detect(frame)

        return hp_status , mp_status
        
    def hp_detect(self, frame:np.ndarray):
        '''
        偵測血量
        '''
        x1 , y1 ,x2 , y2 = self.hp_bar_loc
        crop_frame = frame[y1:y2, x1:x2]
        hsv_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2HSV)
        max_hp = crop_frame.shape[1]

        #雖然楓之谷大概沒有光汙問題，但還是做一下，
        lower_bound = np.array(self.lower_hp_color, dtype=np.uint8)
        upper_bound = np.array(self.upper_hp_color, dtype=np.uint8)
        mask = cv2.inRange(hsv_frame,lower_bound, upper_bound)

        # axis=0 把垂直方向有True則True，把多排matrix壓成一排
        hp_remain = np.any(mask > 0, axis=0)
        # 把True的數量算出來，得到目前血量
        hp_remain = np.count_nonzero(hp_remain)

        return round(hp_remain/max_hp*100,1)

    def mp_detect(self, frame:np.ndarray):
        '''
        跟上面差不多
        '''
        x1,y1,x2,y2 = self.mp_bar_loc
        crop_frame = frame[y1:y2, x1:x2]
        hsv_frame = cv2.cvtColor(crop_frame, cv2.COLOR_BGR2HSV)
        max_mp = crop_frame.shape[1]

        lower_bound = np.array(self.lower_mp_color, dtype=np.uint8)
        upper_bound = np.array(self.upper_mp_color, dtype=np.uint8)
        mask = cv2.inRange(hsv_frame,lower_bound, upper_bound)

        mp_remain = np.any(mask > 0, axis=0)
        mp_remain = np.count_nonzero(mp_remain)

        return round(mp_remain/max_mp*100,1)


if __name__ == "__main__":
    run = HealthDetector()
    run.run()