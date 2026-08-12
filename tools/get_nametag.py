import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import time
import yaml
import cv2
import numpy as np
import win32gui
import win32con
from PIL import ImageGrab
from src.utils.common import get_mask, get_window_handle_and_rect_by, bring_to_front_and_center_origin
from config.config_loader import config
import logging
''''
人物名牌捕捉器:
程序會捕捉畫面，進到畫面後，找一個能夠清楚顯示明白的場景，按下拍照鍵"Z"即可製作名牌

'''

LOWER_GREEN = np.array([35, 100, 100], dtype=np.uint8)
UPPER_GREEN = np.array([85, 255, 255], dtype=np.uint8)

class GetRoleImg():
    def __init__(self):
        #config
        self.game_title = config.get("game.title")
        self.template_nametag_path = config.get("folder_path.template_nametag_path")
        self.hwnd,self.client_rect =None, None
        self.MyRole_img_path = config.get("folder_path.my_character_template_path")
        
        #img
        self.role_template = None
        self.role_template_hsv = None
        self.mask = None
        self.img_char_template_mask = None


        #char location 
        self.role_top_left = None
        self.role_bottom_right =None

        #paramter
        self.max_threshold = config.get("image_processing.max_threshold")

    def run(self):
        # pre_load
        self.connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        self.preload_img()

        #main run
        self.get_new_char_img()

    def connect_window(self):
        self.hwnd, self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")

    def preload_img(self):
        """預先載入圖片"""  

        #讀取模板轉hsv
        self.role_template = cv2.imread(self.MyRole_img_path)
        self.role_template_hsv = cv2.cvtColor(self.role_template, cv2.COLOR_BGR2HSV)
        #bgr是三通到、mask是單通道，沒辦法使用，轉灰階變單通道
        self.role_template = cv2.imread(self.MyRole_img_path, cv2.IMREAD_GRAYSCALE)
        #遮罩模板與反轉
        role_green_mask = cv2.inRange(self.role_template_hsv, LOWER_GREEN, UPPER_GREEN)
        self.mask = cv2.bitwise_not(role_green_mask)

    def _save_role_NameTag(self,frame_bgr):
        '''儲存人物名白 '''

        x1,y1 = self.role_top_left
        x2,y2 = self.role_bottom_right
        crop_img = frame_bgr[y1:y2,x1:x2]

        result =cv2.imwrite(self.MyRole_img_path,crop_img)
        if result:
            print(f"\n角色標籤已儲存至:{self.MyRole_img_path}")
        else:
            print("角色標籤儲存失敗")

    def _capture_screen(self) -> cv2.Mat:
        '''單純負責：抓取遊戲相機視窗、縮放、轉換色彩格式，並回傳處理好的影像'''

        try:
            camera_rect = win32gui.GetClientRect(self.hwnd)
            camera_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (camera_rect[0], camera_rect[1]))
            camera_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (camera_rect[2], camera_rect[3]))
            camera_rect = (camera_rect_point_top_left[0], camera_rect_point_top_left[1], camera_rect_point_bottom_right[0], camera_rect_point_bottom_right[1])  

        except Exception:
            raise RuntimeError("視窗已關閉或遺失。")

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=camera_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

        #裁切螢幕[y,x]
        crop_frame = frame_bgr[300:540,400:850]
        return crop_frame 

    def _get_role_NameTag(self,frame_bgr):
        '''判斷人物角色位置'''
        crop_frame = cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2GRAY)
        method = cv2.TM_CCORR_NORMED
        result = cv2.matchTemplate(crop_frame, self.role_template, method, mask=self.mask)

        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        self.role_top_left = max_loc
        h, w = self.role_template.shape[:2]
        self.role_bottom_right = (self.role_top_left[0] + w, self.role_top_left[1] + h)

        cv2.rectangle(frame_bgr, self.role_top_left, self.role_bottom_right, (100, 0, 255), 2)

    def get_new_char_img(self):
        '''顯示畫面、手動抓圖'''
        while True:
            try:
                crop_frame  = self._capture_screen()
                self._get_role_NameTag(crop_frame )
                cv2.imshow("Game Debug View", crop_frame )
                #找到人物，觸發抓取在跳出

                # 拍照鍵 "Z"
                key = cv2.waitKey(1) & 0xFF
                if key == ord('z'):
                    self._save_role_NameTag(crop_frame )
                    break

                # 離開鍵 "Q"
                elif key == ord('q'):
                    break
            except RuntimeError as e:
                print(e)
                break

        cv2.destroyAllWindows()



if __name__ == "__main__":
    run =GetRoleImg()
    time.sleep(2)
    run.run()