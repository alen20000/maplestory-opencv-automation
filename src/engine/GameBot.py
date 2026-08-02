import time
import yaml
import cv2
import numpy as np
import win32gui
import mss
from PIL import ImageGrab
from src.utils.common import get_mask, get_window_handle_and_rect_by,window_infront_dest,bring_to_front_and_center_origin
import os

import logging

# --- 這裡放常數與參數設定 ---
MAX_THRESHOLD = 0.07
MIN_THRESHOLD = 0.8
# --- 日誌初始化設定 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(current_dir, "logs")
log_file = os.path.join(log_dir, "game_debug.log")

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=log_file, 
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'
)



class GameBot:
    def __init__(self):
        #config
        with open('config/global.yaml', "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        #init
        self.game_title = self.config["game"]["title"]
        self.hwnd = None
        # self.client_rect = None
        self.last_loc = None  # 記住上一次找到的位置

        #img about
        self.my_char_template_path = 'img/nametag/new_char.png'
        self.my_char_template = None
        self.template_h, self.template_w = None, None
        self.frame_bgr = None

    def run(self):

        #預處理
        self.connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        self.preload_img()

        #process
        self.screen_loop()

    def connect_window(self):
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")
    def preload_img(self):
        """預先載入圖片"""

        #loard_char_template
        self.my_char_template = cv2.imread(self.my_char_template_path)
        #get hight and width of template
        self.template_h, self.template_w = self.my_char_template.shape[:2]

    def _bid_char(self):
        '''角色座標判斷(全圖掃描)'''
        frame = self.BGR2Binary(self.frame_bgr)
        template = self.BGR2Binary(self.my_char_template)
        result = cv2.matchTemplate(frame,template,cv2.TM_CCOEFF_NORMED)

        #找到角色
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > MAX_THRESHOLD:
            # print(f"找到角色，Location:{max_loc}")
            return max_loc
        else:
            # print("未找到角色")
            pass

    def cent_coord(self,loc,template) -> tuple[int,int]: 
        '''計算location中心點'''
        t_h,t_w = template.shape[:2]
        center_w = int(loc[0]+(t_w/2))
        center_h = int(loc[1]+(t_h/2))
        return center_w,center_h
    
    def get_roi_box(self,x,y,template) -> tuple[tuple[int,int],tuple[int,int]]:
        '''計算ROI區塊'''

        t_h, t_w = template.shape[:2]
        left_top = (x - t_w//2, y - t_h//2)
        right_bottom = (x + t_w//2,y + t_h//2)
        return left_top,right_bottom
    def draw_dectection_box(self,frame,left_top,right_bottom,label="Target",color=(0,255,0),thickness=2,
                            top_padding=0, bottom_padding=0, left_padding=0, right_padding=0):
        '''繪製ROI區塊，參數:frame,左上角座標,右下角座標,標籤名稱,顏色,線條粗細,擴大值'''

        #Box變動算法
        left_top = (left_top[0] - left_padding, left_top[1] - top_padding)
        right_bottom = (right_bottom[0] + right_padding, right_bottom[1] + bottom_padding)

        cv2.rectangle(frame, left_top, right_bottom, color, thickness)

        cv2.putText(
            frame, 
            label, 
            (left_top[0], left_top[1] - 10), # 文字位置在框框左上方稍微偏上一點
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            color, 
            2
        )
        return frame

    def BGR2Binary(self,img):
        '''圖片取灰階並二值化'''

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return binary
    def scan_full_screen(self):
        '''全螢幕判斷'''
        try:
            screen_rect = win32gui.GetClientRect(self.hwnd)
            screen_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (screen_rect[0], screen_rect[1]))
            screen_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (screen_rect[2], screen_rect[3]))
            screen_rect = (screen_rect_point_top_left[0], screen_rect_point_top_left[1], screen_rect_point_bottom_right[0], screen_rect_point_bottom_right[1])  
            # print(f"DEBUG -> 全螢幕範圍: {screen_rect}，左上點:{screen_rect_point_top_left}，右下點:{screen_rect_point_bottom_right}")
        except Exception as e:
            print(f"Error: {e}")
            return None

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR
        return frame_bgr
    def screen_loop(self):
        '''全螢幕刷新'''
        
        try:
            while True:
                self.frame_bgr = self.scan_full_screen()
                """這裡放判斷opencv查找函式"""

                max_loc = self._bid_char()
                c_w,c_h = self.cent_coord(max_loc,self.my_char_template)
                # print(f"角色中心點:({c_w},{c_h})")
                left_top,right_bottom = self.get_roi_box(c_w,c_h,self.my_char_template)
                # print(f"角色ROI區塊:({left_top},{right_bottom})")
                self.draw_dectection_box(self.frame_bgr,left_top,right_bottom,label="我的角色",
                top_padding=100, bottom_padding=0, left_padding=0, right_padding=0)

                cv2.imshow("Game Debug View", self.frame_bgr)
                if cv2.waitKey(33) & 0xFF == ord('q'):
                    break
        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()
            


if __name__ == "__main__":
    pass