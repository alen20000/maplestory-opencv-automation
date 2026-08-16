
from config.config_loader import config
import logging
import src.utils.logger as logger
from src.utils.common import get_window_handle_and_rect_by,bring_to_front_and_center_origin
import win32gui
from PIL import ImageGrab
import numpy as np
import ctypes
import time
from src.engine.MinimapDetector import MinimapDetector
'''
還不確定是測試用，還是模組一部分。

fuction:橋接遊戲即時畫面與 MinimapDetector.py，紀錄我的座標與操作紀錄。

'''
import cv2


class OperationLogger:
    def __init__(self):

        #---視窗設定
        self.game_title = config.get("game.title")
        self.hwnd = None
        self.frame_size = None
        #--- 模組實例
        self.minimap_detector = None

    def _connect_window(self):
        '''
        掛勾遊戲視窗
        '''
        self.hwnd,_ =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            logging.info(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            logging.info(f"未匹配到指定窗口{self.game_title }")

    def _scan_full_screen(self):
        '''
        hwnd 讀取遊戲視窗，並取得新的遊戲畫面
        '''
        try:

            client_rect = win32gui.GetClientRect(self.hwnd)
            client_tl = win32gui.ClientToScreen(self.hwnd, (client_rect[0], client_rect[1]))
            client_br = win32gui.ClientToScreen(self.hwnd, (client_rect[2], client_rect[3]))
            screen_rect  = (client_tl[0], client_tl[1], client_br[0], client_br[1])

        except Exception as e:
            logging.error(f"螢幕讀取錯誤:{e}")
            return None
        
        #抓圖-轉陣-轉BRG

        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

        if frame_bgr is not None:

            # 記錄畫面尺寸
            if self.frame_size is None:
                y, x = frame_bgr.shape[:2]  # (height, width)
                self.frame_size = (x ,y)

            return frame_bgr

        return frame_bgr
    
    def _loading_config(self):
        #--載入模組
        self.minimap_detector = MinimapDetector()

    def run(self):

        #pre_process
        # 強制讓 Python 程式識別真實的螢幕 DPI 像素，避免抓圖範圍縮水
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
        self._connect_window()
        self._loading_config()
        bring_to_front_and_center_origin(self.hwnd)
        time.sleep(0.5)
        #process
        self.screen_loop()

    def screen_loop(self):
        '''
        全螢幕刷新
        
        '''
        
        try:
            while True:
                self.frame_bgr = self._scan_full_screen()


                #===========================
                player_loc = self.MinimapDetector(self.frame_bgr)
                self._show_player_loc(player_loc)
                
                #===========================

                cv2.imshow("Loc_Logger", self.frame_bgr)
                cv2.waitKey(1)

        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    def MinimapDetector(self,frame)-> tuple[int,int]:
        '''
        WIP
        與小圖偵測模組進行互動：傳送當前灰階圖，並取得回傳的怪物封包。
        '''
        result = self.minimap_detector.run(frame)
        return result
    
    def _show_player_loc(self,player_loc):
        
        cv2.putText(self.frame_bgr, f"人物座標: {player_loc}", org=(10, 250),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1.5, color=(0, 0, 0), thickness=2)
        
if __name__ == "__main__":
        #---日誌模組
        logger.setup_logging()

        #--- run
        run = OperationLogger()
        run.run()