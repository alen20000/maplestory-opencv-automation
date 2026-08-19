import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
                pass
import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.common import get_window_handle_and_rect_by, bring_to_front_and_center_origin
import time
import cv2
import numpy as np
import win32gui
import win32con
from PIL import ImageGrab
class GetMpBar():
    def __init__(self):
        self.frame_bgr = None   
        self.hwnd = None
        self.client_rect = None 
        self.game_title = "新楓之谷：經典版"
        self.frame_size = None
    def _connect_window(self):
        '''
        hook the game window
        '''
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            logging.info(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            logging.info(f"未匹配到指定窗口{self.game_title }")

    def _scan_full_screen(self):
        '''以窗柄去掃描遊戲畫面'''
        try:
            #這邊還能優化 以後看到記得改
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

    
    def screen_loop(self):
        try:    
            while True:

                self.frame_bgr = self._scan_full_screen()
                x1, y1, x2, y2 = (504,755,608,766)
                cropped_frame = self.frame_bgr[y1:y2, x1:x2]
                cv2.imshow("Game Debug View", cropped_frame)
                cv2.waitKey(1)


                
        finally:
            cv2.destroyAllWindows()
    def run (self):
        """#pre_process"""
        # 強制讓 Python 程式識別真實的螢幕 DPI 像素，避免抓圖範圍縮水

        self._connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        time.sleep(2)
        self.screen_loop()


if __name__ == "__main__":
    run =GetMpBar()

    

    run.run()