import yaml
import cv2
import numpy as np
import win32gui
from PIL import ImageGrab
from src.utils.common import (get_mask, get_window_handle_and_rect_by,
window_infront_dest,bring_to_front_and_center_origin,cent_coord,get_roi_box,draw_dectection_box,BGR2Binary
)
import os
import logging
from src.engine.MobHunting import MobDetector
import ctypes

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

# --- 遊戲掃描模式 ---
# 1 為 grayscale 2 為 測試模式
MATCH_MODEL = 1
# --- 這裡放常數與參數設定 ---
MAX_THRESHOLD = 0.07
MIN_THRESHOLD = 0.6


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

        #img parameters
        self.my_character_template_path = 'img/nametag/MyRoleNameTag.png'
        self.my_character_template = None
        self.my_character_template_gray = None
        self.my_character_telplate_binary = None
        self.my_character_telplate_h, self.my_character_telplate_w = None, None
        self.frame_bgr = None
        
        self.frame_h, self.frame_w = None, None
        self.dectect_False_count = 0
        #ROI Range
        self.ROI_left_top = None, None
        self.ROI_right_bottom = None, None
        self.crop_frame_gray = None
    def _connect_window(self):
        '''
        hook the game window
        '''
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")

    def _preload_img(self):
        """預先載入圖片、提取參數"""

        self.my_character_template = cv2.imread(self.my_character_template_path)
        self.my_character_template_gray =cv2.cvtColor(self.my_character_template, cv2.COLOR_BGR2GRAY)
        self.my_character_telplate_binary = BGR2Binary(self.my_character_template)
        self.my_character_telplate_h, self.my_character_telplate_w = self.my_character_template.shape[:2]

    def _scan_full_screen(self):
        '''以窗柄去掃描遊戲畫面'''
        try:
            screen_rect = win32gui.GetClientRect(self.hwnd)
            screen_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (screen_rect[0], screen_rect[1]))
            screen_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (screen_rect[2], screen_rect[3]))
            screen_rect = (screen_rect_point_top_left[0], screen_rect_point_top_left[1], screen_rect_point_bottom_right[0], screen_rect_point_bottom_right[1])  

        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
            return None

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR
        return frame_bgr
    def run(self):

        """#pre_process"""
        # 強制讓 Python 程式識別真實的螢幕 DPI 像素，避免抓圖範圍縮水
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
        self._connect_window()
        #adjusying display window
        bring_to_front_and_center_origin(self.hwnd)
        self._preload_img()

        #process
        self.screen_loop()

    def screen_loop(self):
        '''
        全螢幕刷新
        
        '''
        
        try:
            while True:
                '''
                預計所有作圖都放進這裡
                ================
                '''
                self.frame_bgr = self._scan_full_screen()

                self.character_tracking_logic()
                self.Mobdector()



                '''
                ================
                '''
                cv2.imshow("Game Debug View", self.frame_bgr)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    def _locate_character(self):
        '''全圖掃描，角色座標判斷、繪製bounding box'''
        if MATCH_MODEL == 1:
            current_frame = cv2.cvtColor(self.frame_bgr, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(current_frame,self.my_character_template_gray,cv2.TM_CCOEFF_NORMED)

            #找到角色
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > MAX_THRESHOLD:
                print(f"全圖掃描找到角色，位置:{max_loc},置信度:{max_val}")
                return max_loc
            else:
                # print("全圖掃描，未找到角色")
                pass

    def _scan_local_area(self):
        '''ROI角色掃描:角色中心座標為錨定,做範圍掃描'''

        #畫面與人物樣本取高寬、二階化
        h_frame, w_frame = self.frame_bgr.shape[:2]
        #人物中心座標
        role_x,role_y = self.character_center_loc
        # 設定搜尋範圍的大小（之後要移動到Config 用 yaml外部設定）
        x_offset, y_offset = 300,250
        # 以中心座標 (x, y) 為基準，計算出上下左右邊界
        left = max(0, role_x - x_offset)
        top = max(0, role_y  - y_offset)
        right = min(w_frame, role_x + self.my_character_telplate_w + x_offset)
        bottom = min(h_frame, role_y  + self.my_character_telplate_h + y_offset -250 )
        #ROI範圍
        self.ROI_left_top = (left, top)
        self.ROI_right_bottom = (right, bottom)

        #限定範圍: 先切割再轉灰階
        crop_frame = self.frame_bgr[top:bottom, left:right]
        self.crop_frame_gray  =  cv2.cvtColor(crop_frame, cv2.COLOR_BGR2GRAY)
        #匹配掃描中
        matches = cv2.matchTemplate(self.crop_frame_gray ,self.my_character_template_gray,cv2.TM_CCOEFF_NORMED)
        #從匹配中選擇最優為目標
        _, max_val, _, max_loc = cv2.minMaxLoc(matches)
        #目標過濾，通過為合格
        if max_val > MIN_THRESHOLD:

            # print(f"ROI掃描找到角色，位置:{max_loc}，置信度:{max_val}")
            
            #目標全局座標(左上基準點) = 目標的區域左上X + ROI 左上 X, 區域左上Y +ROI 左上Y 
            global_role_loc = (max_loc[0] + self.ROI_left_top[0], max_loc[1] + self.ROI_left_top[1])

            #更新人物座標
            self.character_center_loc = cent_coord(global_role_loc , self.my_character_template)

            #在 frame_bgr 畫出ROI範圍
            draw_dectection_box(self.frame_bgr,self.ROI_left_top ,self.ROI_right_bottom,label="怪物偵測範圍",
            top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)
            return  True
        else:
            print("ROI掃描失敗")
            return False


    def character_tracking_logic(self):
        '''method: 一次全圖掃描，得出中心座標，以中心做標求範圍座標'''

        if self.character_center_loc is None:
            #全圖掃

            max_loc = self._locate_character()

            #防止max_loc 為None時，取中心炸掉
            if max_loc is not None:
                #if max_loc is None ,trying+ to get character_center_loc
                self.character_center_loc = cent_coord(max_loc,self.my_character_template)
                # print(f"角色中心座標: {self.character_center_loc}")
        
        else:
            #進入ROI掃
            fund_result = self._scan_local_area()

            #用回傳的True/False，來做失敗紀錄
            if not fund_result:
                self.dectect_False_count += 1
                if self.dectect_False_count > 10:
                    self.character_center_loc = None
                    self.dectect_False_count = 0
        #得到中心座標，則繪製bounding box
        if self.character_center_loc is not None:
            c_w,c_h = self.character_center_loc

            #Character bounding box detection
            char_left_top,char_right_bottom = get_roi_box(c_w,c_h,self.my_character_template)

            #draw character bounding box
            draw_dectection_box(self.frame_bgr,char_left_top,char_right_bottom,label="我的角色",
            top_padding=100, bottom_padding=0, left_padding=0, right_padding=0)
        else:
            pass

    def Mobdector(self):
        '''
        傳輸ROI範圍畫面與範圍座標
        '''
        if self.crop_frame_gray is not None:
            #push data
            mob_detector = MobDetector()
            mob_result = mob_detector.searching_mob(self.crop_frame_gray,self.ROI_left_top)

            if  mob_result is None:
                pass
            else:
                mb_left_top,mb_right_bottom = mob_result
                draw_dectection_box(
                    self.frame_bgr,
                    mb_left_top,
                    mb_right_bottom,
                    label="怪物",color = (0, 0, 255),
                top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)



if __name__ == "__main__":
    pass