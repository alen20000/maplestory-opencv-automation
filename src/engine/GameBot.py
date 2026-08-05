import yaml
import cv2
import numpy as np
import win32gui
from PIL import ImageGrab
from src.utils.common import (get_mask, get_window_handle_and_rect_by,
bring_to_front_and_center_origin,cent_coord,get_bbox_from_center,draw_dectection_box,BGR2Binary,convert_img2xy
)
import os
import logging
from src.engine.MobHunting import MobDetector
import ctypes
from src.utils.boxes import BBox

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

        #---window config
        self.game_title = self.config["game"]["title"]
        self.hwnd = None
        #---player parameter 
        self.my_character_template_path = 'img/nametag/MyRoleNameTag.png'
        self.my_character_template = None
        self.my_character_template_size = None
        self.my_character_template_gray = None
        self.my_character_template_binary = None

        self.frame_bgr = None
        #---Frame data
        self.roi_crop_frame_gray = None
        self.frame_size:tuple[int, int] = None # (x,y)typle
        self.dectect_False_count = 0
        #---計算資料
        self.role_BBOX:BBox = None
        self.roi_BBOX:BBox = None
        self.last_loc = None  # 記住上一次找到的位置
        self.player_center_loc = None


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
        self.my_character_template_size =  convert_img2xy(self.my_character_template)
        self.my_character_template_gray =cv2.cvtColor(self.my_character_template, cv2.COLOR_BGR2GRAY)
        self.my_character_template_binary = BGR2Binary(self.my_character_template)


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

        if frame_bgr is not None:
            self.frame_bgr = frame_bgr
            
            # 記錄畫面尺寸
            if self.frame_size is None:
                y, x = frame_bgr.shape[:2]  # (height, width)
                self.frame_size = (x ,y)

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
                self.frame_bgr = self._scan_full_screen()
                '''
                1.資料回來 2.畫圖
                ================
                '''
                self.player_tracking_logic()
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


    def player_tracking_logic(self):
        '''method: 一次全圖掃描，得出中心座標，以中心做標求範圍座標'''
        try:
            if self.player_center_loc is None:
                #全圖掃

                player_loc = self._locate_player_globally()

                #防止max_loc 為None時，取中心炸掉
                if player_loc is not None:

                    self.player_center_loc = cent_coord(player_loc,self.my_character_template_size)

            
            else:
                #進入ROI掃
                fund_result = self._locate_player_locally()

                #用回傳的True/False，來做失敗紀錄
                if not fund_result:
                    self.dectect_False_count += 1
                    if self.dectect_False_count > 10:
                        self.player_center_loc = None
                        self.dectect_False_count = 0

            #得到中心座標，則繪製bounding box
            if self.player_center_loc is not None:
                #計算角色BBOX
                self.role_BBOX = get_bbox_from_center(self.player_center_loc,self.my_character_template_size)

                #繪製角色BBOX
                draw_dectection_box(self.frame_bgr,self.role_BBOX.top_left,self.role_BBOX.bottom_right,label="我的角色",
                top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)
            else:
                pass

        except Exception as e:
            logging.error(e)

    def _locate_player_globally(self):
        '''
        全局掃描人物
        '''
        if MATCH_MODEL == 1:
            current_frame = cv2.cvtColor(self.frame_bgr, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(current_frame,self.my_character_template_gray,cv2.TM_CCOEFF_NORMED)

            #找到角色
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > MAX_THRESHOLD:
                # print(f"全圖掃描找到角色，位置:{max_loc},置信度:{max_val}")
                return max_loc
            else:
                pass

    def _locate_player_locally(self):
        '''
        局部掃描:
        '''
        try:
            # 設定搜尋範圍的位移量[!] 之後變數要移走
            x_offset, y_offset = 300, 250
            # Tuple都是[x,y]位置
            top = max(0, self.player_center_loc[1] - y_offset)
            left = max(0, self.player_center_loc[0] - x_offset)
            bottom = min(self.frame_size[1], self.player_center_loc[1] + y_offset )
            right = min(self.frame_size[0], self.player_center_loc[0]  + x_offset)

            # 計算ROI範圍
            self.roi_BBOX = BBox(left, top, right, bottom)

            #[!]OpenCV 陣列切片強制要求 [y軸範圍, x軸範圍]，小心切錯
            roi_crop_frame = self.frame_bgr[top:bottom, left:right]
            self.roi_crop_frame_gray  =  cv2.cvtColor(roi_crop_frame, cv2.COLOR_BGR2GRAY)
            matches = cv2.matchTemplate(self.roi_crop_frame_gray ,self.my_character_template_gray,cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(matches)

            if max_val > MIN_THRESHOLD:

                #相對座標轉全局座標；全局座標= 相對座標x + roi全局座標x, 相對座標y + roi全局座標y 
                player_loc_globally = (max_loc[0] + self.roi_BBOX.x1, max_loc[1] + self.roi_BBOX.y1)

                self.player_center_loc = cent_coord(player_loc_globally , self.my_character_template_size)
                self.role_BBOX = get_bbox_from_center(self.player_center_loc , self.my_character_template_size)
                # print(f"ROI掃描找到角色，位置:{player_loc_globally},置信度:{max_val}")

                # 繪製偵查範圍
                draw_dectection_box(self.frame_bgr, self.roi_BBOX.top_left, self.roi_BBOX.bottom_right, label="偵測範圍",
                top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)
                return  True
            
            else:
                logging.info('ROI掃描，未找到角色')
                return False    

        except Exception as e:
            logging.error(e)


    def Mobdector(self):
        '''
        傳輸 roi灰階圖
        '''
        if self.roi_crop_frame_gray is not None:
            #push data
            mob_detector = MobDetector()
            mob_result = mob_detector.searching_mob(self.roi_crop_frame_gray)
            print(mob_result)
            # if  mob_result is None:
            #     pass
            # else:
            #     mb_left_top,mb_right_bottom = mob_result
            #     draw_dectection_box(
            #         self.frame_bgr,
            #         mb_left_top,
            #         mb_right_bottom,
            #         label="怪物",color = (0, 0, 255),
            #     top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)



if __name__ == "__main__":
    pass