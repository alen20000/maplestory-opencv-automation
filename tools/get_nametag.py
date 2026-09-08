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



class GetRoleImg():
    def __init__(self):
        #config
        self.game_title = config.get("game.title")  # 遊戲視窗標題
        self.template_nametag_path = config.get("folder_path.template_nametag_path") #名牌模板
        self.hwnd,self.client_rect =None, None
        self.MyRole_img_path = config.get("folder_path.my_character_template_path") #儲存路徑
        
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

        LOWER_GREEN = np.array([35, 100, 100], dtype=np.uint8)
        UPPER_GREEN = np.array([85, 255, 255], dtype=np.uint8)

        # 讀取模板
        self.role_template_bgr = cv2.imread(self.template_nametag_path)

        #轉HSV製作遮罩
        self.role_template_hsv = cv2.cvtColor(self.role_template_bgr, cv2.COLOR_BGR2HSV)
        role_green_mask = cv2.inRange(self.role_template_hsv, LOWER_GREEN, UPPER_GREEN)
        self.mask = cv2.bitwise_not(role_green_mask)

        #bgr是三通到、mask是單通道，沒辦法使用，轉灰階變單通道
        self.role_template = cv2.cvtColor(self.role_template_bgr, cv2.COLOR_BGR2GRAY)


    def _save_role_NameTag(self,frame_bgr):
        '''捕捉人物名牌 '''

        x1,y1 = self.role_top_left
        x2,y2 = self.role_bottom_right
        crop_img = frame_bgr[y1:y2,x1:x2]

        result =cv2.imwrite(self.MyRole_img_path,crop_img)
        if result:
            print(f"\n角色標籤已儲存至:{self.MyRole_img_path}")
        else:
            print("角色標籤儲存失敗")



    def _process_nametag(self):
        '''後製圖片'''
        img = cv2.imread(self.MyRole_img_path)
        if img is None:
            print("無法讀取圖片")
            return

        # 1. 建立一個全綠色的畫布 (BGR格式，純綠色為 0, 255, 0)
        # 尺寸與原圖相同
        processed_img = np.full(img.shape, (0, 255, 0), dtype=np.uint8)

        # 2. 設定你要保留的固定區塊座標範圍 (y1:y2, x1:x2)
        # 【注意】這裡的數值需要依據你實際抓圖的大小來微調
        # 假設圖片高度為 H、寬度為 W，你只想保留中間包含稱號、名字、勳章的某個固定矩形範圍：
        h, w, _ = img.shape
        
        # 範例：保留從垂直 10% 到 90%、水平 15% 到 85% 的區域（請依你的實際畫面調整）
        y1, y2 = int(h * 0.05), int(h * 0.95)
        x1, x2 = int(w * 0.10), int(w * 0.90)

        # 3. 將原圖的指定區塊覆蓋到綠色畫布上，其餘部分維持綠色背景
        processed_img[y1:y2, x1:x2] = img[y1:y2, x1:x2]

        # 儲存或回傳處理後的圖片
        cv2.imwrite(self.MyRole_img_path, processed_img)
        print(f"\n角色標籤已儲存至:{self.MyRole_img_path}")


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
        method = cv2.TM_CCOEFF_NORMED
        result = cv2.matchTemplate(crop_frame, self.role_template, method, mask=self.mask)

        # 異常值處理: 用numpy的布林引索，處理異常值"無限""
        result[result > 1] = 0
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        # 位置座標處理
        self.role_top_left = max_loc
        h, w = self.role_template.shape[:2]
        self.role_bottom_right = (self.role_top_left[0] + w, self.role_top_left[1] + h)

        # 畫框
        cv2.rectangle(frame_bgr, (self.role_top_left[0]-1, self.role_top_left[1]-1),
                    (self.role_bottom_right[0]+1, self.role_bottom_right[1]+1), (100, 0, 255), 2)
        cv2.putText(frame_bgr,f"匹配值:{max_val:.2f}",(self.role_top_left[0]-10, self.role_top_left[1]-10),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0, 0, 225), thickness=1)
        # cv2.imshow("Mask (White = Keep, Black = Ignore)", self.mask)
        # cv2.imshow("roler)", self.role_template)
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
                    self._process_nametag()
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