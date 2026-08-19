import cv2
from config.config_loader import config
import logging
import src.utils.logger as logger
from src.utils.common import get_window_handle_and_rect_by,bring_to_front_and_center_origin
import win32gui
from PIL import ImageGrab
import numpy as np
import ctypes
import sys
import os
import time
from src.engine.MinimapDetector import MinimapDetector
import src.action.HotkeyManager as hk
import win32con
from pathlib import Path
import yaml


'''
還不確定是測試用，還是模組一部分。

fuction:橋接遊戲即時畫面與 MinimapDetector.py，紀錄我的座標與操作紀錄。

先預設 幾種模式  walk : 走路 ; rope : 繩子點 ; ; jump_down : 直接跳下

[注意!] 連續兩個 walk 會判定為平台; 連續兩個rope會判定為垂直通道。確保walk "高度" 差不多，而rope x軸要一樣
 
[Example] ... -> walk -> walk -> rope -> rope 這樣兩個walk會判定為平台，平台才會觸發戰鬥模式；兩個rope點會判定為垂直通道

熟建:

F5 設立走位點
F6 設立爬繩點向上
F7 設立爬繩點向下
F8 設立跳下點
F12 儲存行為座標於minimap目錄下
'''



HOTKEYS = {
    win32con.VK_F6: "walk",
    win32con.VK_F7: "rope_up",
    win32con.VK_F8: "rope_down",
    win32con.VK_F9: "jump_down",
}

class OperationLogger:
    def __init__(self):

        #---視窗設定
        self.game_title = config.get("game.title")
        self.hwnd = None
        self.frame_size = None
        #---路徑設定
        self.map_name = config.get("quickly_choice_map")
        self.mini_map =  Path(config.get(f"mini_map.{self.map_name}"))
        #--- 模組實例
        self.minimap_detector = None
        self.hk = None

        #--- 資料容器
        self.player_loc = None
        self.recored_data = []

    #=================
    # 初始化與加載資源
    #=================
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
        self.hk = hk.HotkeyManager()
        #--熟建載入
        self.hk.register(win32con.VK_F5, self._walk_point)
        self.hk.register(win32con.VK_F6, self._rope_point)
        self.hk.register(win32con.VK_F8, self._jump_down_point)
        self.hk.register(win32con.VK_F12,self._save_actions_to_yaml)
        self.hk.register(win32con.VK_F1,self._exit_app)
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
        print("="*20)
        print("F1 離開程式//F5 Walk行動點 // F6 繩子行動點 //F8 下跳點 // F12 儲存")
        print("="*20)
        #process
        self.screen_loop()

    def screen_loop(self):
        '''
        全螢幕刷新
        
        '''
        
        try:
            while True:
                self.frame_bgr = self._scan_full_screen()
                #==按鍵監聽==================
                self.hk.poll() 
                #===========================
                player_loc = self.MinimapDetector(self.frame_bgr)
                self.player_loc = player_loc
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
        與小圖偵測模組進行互動：傳送當前BGR圖
        return : 人物位置(x,y)
        '''
        result = self.minimap_detector.run(frame)
        return result
    
    def _show_player_loc(self,player_loc):
        
        cv2.putText(self.frame_bgr, f"人物座標: {player_loc}", org=(10, 250),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0, 0, 0), thickness=2)

    def _walk_point(self):
        '''
        移動點
        '''
        print(f"紀錄點位:{self.player_loc}，行為:walk")
        self.recored_data.append({"loc": list(self.player_loc), "action": "walk"})
        print(self.recored_data)

    #=================
    # 熟鍵綁定
    #=================
    def _rope_point(self):
        '''
        爬繩點
        '''
        print(f"紀錄點位:{self.player_loc}，行為:rope")
        self.recored_data.append({"loc": list(self.player_loc), "action": "rope"})

    def _jump_down_point(self):
        '''
        跳下點
        '''
        print(f"紀錄點位:{self.player_loc}，行為:jump_down")
        self.recored_data.append({"loc": list(self.player_loc), "action": "jump_down"})

    def _save_actions_to_yaml(self):
        '''
        把座標與行為，儲存為ymal格式
        '''
        folder_path = self.mini_map.parent

        yaml_path = folder_path / f"{self.map_name}.yaml"
        print(yaml_path)
        try:
            with open(yaml_path, "w") as f:
                yaml.dump(self.recored_data, f)
        except Exception as e:
            logging.error(f"儲存資料錯誤:{e}")
        pass

    def _exit_app(self):
        '''
        功能:關掉程式
        '''
        logging.info("正在關閉應用程式...")
        self.bot_enabled = False
        
        # 銷毀所有 OpenCV 視窗
        cv2.destroyAllWindows()
        import sys
        sys.exit(0)

    #=================
    # 作業系統管理員權限
    #=================
def is_admin():
    """檢查當前是否擁有管理員權限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理員權限重新執行當前腳本"""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

if __name__ == "__main__":
        #---管理員權限
        if not is_admin():
            run_as_admin()
            sys.exit()
        #---日誌模組
        logger.setup_logging()
        #--- run
        run = OperationLogger()
        run.run()


