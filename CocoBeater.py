import ctypes
# 強制讓 Python 程式識別真實的螢幕 DPI 像素，避免抓圖範圍縮水
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
from src.engine.GameBot import GameBot
import src.utils.logger as logger
import logging
import os
import sys
import cv2
import logging
from pathlib import Path
import src.utils.logger as logger
from src.utils.common import get_window_handle_and_rect_by,bring_to_front_and_center_origin
import win32gui
from PIL import ImageGrab
import numpy as np

'''
WIP
打可可果實腳本


'''
class MaibBot:



    def __init__(self):
        #視窗信息
        self.game_title = "新楓之谷：經典版"
        self.hwnd = None
        self.client_rec = None

        #地圖容器
        self.minimap = None
        #畫面資訊
        self.frame_bgr = None
        self.frame_size = None
        #模組實例容器
        self.map_detector = None
    def _instantiation(self):
        '''
        模組實例化
        '''
        self.map_detector = MapDectector()
        self.minimap_detector = MinimapDetector()
    def _load_res(self):
        '''
        載入資源
        '''

        self.minimap = self.map_detector.load_map()
    def _setting_windows(self):
        '''
        功能:
            事前窗口校正與準備
        取得:
            遊戲窗柄
        '''
        self.hwnd = self.map_detector.connect_window()
        

    def run(self):

        #預處理
        self._instantiation()
        self._load_res()
        self._setting_windows()

        #主程式
        self.loop()

    def loop(self):
        '''主迴圈'''
        try:
            while True:

                #資料蒐集
                self.frame_bgr = self.map_detector.scan_full_screen()
                self._get_window_rect()
                mini_player_loc = self.MinimapDetector() 
                # print(self.frame_size)
                #圖片繪製
                self._render_cv2_view()
                self._render_minimap_overlay(mini_player_loc)
        except Exception as e:
            logging.error(f"視窗更新發生錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    #渲染圖片

    def _render_cv2_view(self):
        '''
        功能:
            統一渲染畫面
        '''
        try:
            cv2.imshow("CoCoBeater", self.frame_bgr)
            cv2.waitKey(1)
        except Exception as e:
            print(f"渲染畫面發生錯誤: {e}")
            logging.error(f"渲染畫面發生錯誤: {e}", exc_info=True)

    def _render_minimap_overlay(self,mini_player_loc):
        '''
        小地圖渲染
        '''
        #防呆:沒資料會導致CTD的，直接攔截
        if self.minimap_detector.crop_frame_bgr is None or mini_player_loc is None:
            return
        overlay = self.minimap_detector.crop_frame_bgr.copy()
        # dx , dy = 8,0

        cv2.circle(overlay, (mini_player_loc[0] , mini_player_loc[1]), 3, [255,255,0], 1)
        cv2.imshow("Minimap Debug", overlay)

    #========
    # 功能函式
    #========

    def _get_window_rect(self):
        '''
        功能:
            若沒有畫面尺寸，則偵測畫面尺寸並記錄
        得到:
            self.frame_size
        '''
        if self.frame_bgr is not None and self.frame_size is None:
            y, x = self.frame_bgr.shape[:2]  # (height, width)
            self.frame_size = (x ,y)

    #=================
    # 偵測器:小地圖
    #=================
    def MinimapDetector(self)-> tuple[int,int]:
        '''
        WIP
        與小圖偵測模組進行互動：傳送當前BGR圖
        return : 人物位置(x,y)
        '''
        mini_player_loc = self.minimap_detector.run(self.frame_bgr)
        return mini_player_loc
    
class MapDectector:
    '''
    處理圖像相關
    '''
    def __init__(self):
        #視窗信息
        self.game_title = "新楓之谷：經典版"
        self.hwnd = None

        self.frame_bgr = None   
        self.client_rect = None 


    def load_map(self):
        '''
        載入地圖
        '''
        map_name_is = "Florina_Beach_Lorang's_Sandy_Beach"
        minimap_folder = "img/mini_map"
        current_dir = Path.cwd()
        print(current_dir)
        minimap_dir= current_dir / minimap_folder / map_name_is / f"{map_name_is}.png"
        if minimap_dir.exists():
            print("地圖載入成功")

        else:
            e = f"{minimap_dir}不存在"
            print(e)
            logging.error(f"{e}")

        minimap = cv2.imread(str(minimap_dir), cv2.IMREAD_COLOR)
        return minimap

    def connect_window(self):
        '''
        功能:
            hook 視窗，帶到前台(0,0)位置
        return:
            視窗句柄, 視窗尺寸

        '''
        self.hwnd, _ =  get_window_handle_and_rect_by(self.game_title)

        if self.hwnd :
            bring_to_front_and_center_origin(self.hwnd)
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
            logging.info(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")

        else:
            print(f"未匹配到指定窗口{self.game_title }")
            logging.info(f"未匹配到指定窗口{self.game_title }")

        return self.hwnd
    
    def scan_full_screen(self):
        '''
        功能:
            掃描遊戲畫面與更新
        要求:
            視窗與窗柄
        '''
        try:

            client_rect = win32gui.GetClientRect(self.hwnd)
            client_tl = win32gui.ClientToScreen(self.hwnd, (client_rect[0], client_rect[1]))
            client_br = win32gui.ClientToScreen(self.hwnd, (client_rect[2], client_rect[3]))
            screen_rect  = (client_tl[0], client_tl[1], client_br[0], client_br[1])
            self.client_window_tl = client_tl
        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
            return None

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

        return frame_bgr

class MinimapDetector:
    def __init__(self):

        self.current_frame_bgr =None
        self.crop_frame_bgr = None

        #load config
        self._load_minimap_config()

    def _load_minimap_config(self):
        '''
        地圖載入
        '''
        try:
            #load map img

            map_name_is = "Florina_Beach_Lorang's_Sandy_Beach"
            minimap_folder = "img/mini_map"
            current_dir = Path.cwd()

            map= current_dir / minimap_folder / map_name_is / f"{map_name_is}.png"

            self.minimap_template = cv2.imread(map,cv2.IMREAD_COLOR)
        except Exception as e:
            logging.error(f"載入地圖失敗{e}")


    def _crop_minimap(self,frame_bgr):
        '''
        輸入: 全圖彩色
        動作: 裁切小地圖範圍，並存入 self.crop_frame_bgr
        '''
        h,w = self.minimap_template.shape[:2]
        x1 , y1 = 6 , 72 #<-- 這邊寫死
        return frame_bgr[y1 : y1 + h, x1 : x1 + w]

    def run(self,frame_bgr):

        self.crop_frame_bgr = self._crop_minimap(frame_bgr)

        #防呆:沒畫面就不偵測
        if self.crop_frame_bgr is None:
            return
        
        # 取得人物座標
        player_loc = self._detect_player_loc(self.crop_frame_bgr)

        return player_loc

    def _detect_player_loc(self,frame):
        '''
        在frame偵測範圍內找人物座標像素
        '''

        frame_hsv = cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        lower_player_color = np.array([25, 100, 180])
        upper_player_color = np.array([35, 255, 255])

        mask = cv2.inRange(frame_hsv,lower_player_color,upper_player_color)


        #抓住符合顏色最大那塊。 cv2.findContours搭配cv2.RETR_EXTERNAL與cv2.CHAIN_APPROX_SIMPLE 抓最大輪廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # 只取面積最大的色塊，視為玩家
        largest = max(contours, key=cv2.contourArea)

        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        player_x = int(M["m10"] / M["m00"])
        player_y = int(M["m01"] / M["m00"])

        return (player_x, player_y)
    
class State:
    def __init__(self):
        pass

if __name__ == "__main__":

    # I. 日誌仔入
    logger.setup_logging()
    try:
        run = MaibBot()
        run.run()
    except Exception as e:
        logging.exception(f"腳本啟動失敗: {e}")