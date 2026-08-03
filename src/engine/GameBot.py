import time
import yaml
import cv2
import numpy as np
import win32gui
import mss
from PIL import ImageGrab
from src.utils.common import (get_mask, get_window_handle_and_rect_by,
window_infront_dest,bring_to_front_and_center_origin,cent_coord,get_roi_box,draw_dectection_box,BGR2Binary
)
import os

import logging

# --- 這裡放常數與參數設定 ---
MAX_THRESHOLD = 0.07
MIN_THRESHOLD = 0.6
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

        self.last_loc = None  # 記住上一次找到的位置
        self.character_center_loc = None

        #img about
        self.my_char_template_path = 'img/nametag/new_char.png'
        self.my_char_template = None
        self.template_h, self.template_w = None, None
        self.frame_bgr = None

    def _connect_window(self):
        '''
        bid gamewindow
        '''
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")

    def run(self):

        #pre_process
        self._connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        self.preload_img()

        #process
        self.screen_loop()

    def screen_loop(self):
        '''全螢幕刷新'''
        
        try:
            while True:
                self.frame_bgr = self.scan_full_screen()
                """這裡放判斷opencv查找函式"""

                self.character_tracking_logic()
                c_w,c_h = self.character_center_loc

                #Character bounding box detection
                char_left_top,char_right_bottom = get_roi_box(c_w,c_h,self.my_char_template)

                #draw character bounding box
                draw_dectection_box(self.frame_bgr,char_left_top,char_right_bottom,label="我的角色",
                top_padding=100, bottom_padding=0, left_padding=0, right_padding=0)

                cv2.imshow("Game Debug View", self.frame_bgr)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()


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

    def character_tracking_logic(self):
        '''邏輯: 一次全圖掃描，得出中心座標，以中心做標求範圍座標'''
        if self.character_center_loc is None:
            max_loc = self._bid_char()
            self.character_center_loc = cent_coord(max_loc,self.my_char_template)
            print(f"角色中心座標: {self.character_center_loc}")
        else:
            new_center = self.scan_scope()

    def scan_scope(self):
        '''範圍掃描:角色中心座標為錨定,做範圍掃描'''
        h_frame, w_frame = self.frame_bgr.shape[:2]
        frame_processed = self.BGR2Binary(self.frame_bgr)
        template = self.BGR2Binary(self.my_char_template)
        h_tmpl, w_tmpl = template.shape[:2]

        #人物中心座標
        x,y = self.character_center_loc

        # 設定搜尋範圍的大小（可以自行調整，例如以角色為中心向外擴展 100 像素）
        top_offset, bottom_offset, left_offset, right_offset = 200,0,50,200

        # 以中心座標 (x, y) 為基準，計算出上下左右邊界
        left = max(0, x - left_offset)
        top = max(0, y - top_offset)
        right = min(w_frame, x + w_tmpl + right_offset)
        bottom = min(h_frame, y + h_tmpl + bottom_offset)

        #計算範圍
        left_top = (left, top)
        right_bottom = (right, bottom)
        box_width = right - left
        box_height = bottom - top
        print(f"目前追蹤範圍的大小: 寬 {box_width} 像素, 高 {box_height} 像素")
        #range of box
        draw_dectection_box(self.frame_bgr,left_top ,right_bottom,label="偵測範圍",
        top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)

        #切割範圍
        search_frame = frame_processed[top:bottom, left:right]
        result = cv2.matchTemplate(search_frame ,template,cv2.TM_CCOEFF_NORMED)

        #找到角色
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > MIN_THRESHOLD:
            print(f"找到角色，Location:{max_loc}")
            global_x = max_loc[0] + left
            global_y = max_loc[1] + top
            #更新座標
            self.character_center_loc = cent_coord((global_x, global_y), self.my_char_template)
            return 
        else:
            print("未找到角色")
            pass


    def BGR2Binary(self,img):
        '''圖片取灰階並二值化'''

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return binary

    def scan_full_screen(self):
        '''全螢幕掃描'''
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

    
            
    def testing(self):
        ''''''

            

if __name__ == "__main__":
    pass