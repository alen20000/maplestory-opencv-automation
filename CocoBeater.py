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
'''
WIP
打可可果實腳本


'''
class MaibBot:



    def __init__(self):
        #地圖容器
        self.minimap = None

    def _load_map(self):
        self.minimap = MapDectector().load_map()

    def run(self):

        #預處理
        self._load_map()
    def loop(self):
        pass

class MapDectector:
    '''
    處理圖像相關
    '''
    def __init__(self):

        self.frame_bgr = None   
        self.hwnd = None
        self.client_rect = None 
        self.game_title = "新楓之谷：經典版"
        self.frame_size = None

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

class State:
    def __init__(self):
        pass

if __name__ == "__main__":

    # I. 日誌仔入
    logger.setup_logging()
    run = MaibBot()
    run.run()