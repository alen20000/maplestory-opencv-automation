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



class OperationLogger:
    def __init__(self):

        #---視窗設定
        self.game_title = config.get("game.title")
        self.hwnd = None
        self.frame_size = None
        #---路徑設定
        self.map_name = config.get("quickly_choice_map")
        self.map_url = Path(config.get(f"mini_map.{self.map_name}"))
        self.mini_map = cv2.imread(str(self.map_url))
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
        key_mappings = {
            win32con.VK_F1: self._save_actions_to_yaml,
            win32con.VK_F2: self._exit_app,
            win32con.VK_F4: self._walk_point,
            win32con.VK_F5: self._rope_point,
            win32con.VK_F6: self._jump_to_right_point,
            win32con.VK_F7: self._jump_to_left_point,
            win32con.VK_F8: self._jump_down_point,
        }
        
        for vk, func in key_mappings.items():
            self.hk.register(vk, func)
    # === 螢幕操作
    def _setting_cv2_map(self):
        '''
        預先幫cv2 設立空視窗，可以拉長變形、拖曳窗口
        '''
        cv2.namedWindow("Min_iMap", cv2.WINDOW_NORMAL)
        cv2.moveWindow("Min_iMap", 1500, 0)

        cv2.namedWindow("Big_Map", cv2.WINDOW_NORMAL)    
        cv2.moveWindow("Big_Map", 1280, 700)

    def _draw_map(self):
        '''
        功能:
            匯出各種咚咚
        '''
        cv2.imshow("Min_iMap", self.mini_map)
        self.draw_recorded_points(self.mini_map)
        cv2.imshow("Big_Map", self.frame_bgr)
        self.draw_recorded_points
        cv2.putText(self.frame_bgr, f"人物座標: {self.player_loc}", org=(10, 275),
            fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=2, color=(0, 0, 255), thickness=2)
    def _is_window_valid(self):
        if not win32gui.IsWindow(self.hwnd):
            logging.info("沒有偵測到窗口")
            return False
        if win32gui.IsIconic(self.hwnd):
            logging.info("沒有偵測到窗口")
            return False
        rect = win32gui.GetClientRect(self.hwnd)
        if rect[2] < 100 or rect[3] < 100:
            return False
        return True
    
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
        self._setting_cv2_map()
        self._connect_window()
        self._loading_config()
        bring_to_front_and_center_origin(self.hwnd)
        time.sleep(0.5)
        self.print_msg()
        #process
        self.screen_loop()

        print("=" * 45)

    def screen_loop(self):
        '''
        全螢幕刷新
        
        '''
        
        try:
            while True:
                #==防呆保護==================
                if not self._is_window_valid():
                    time.sleep(1)
                    continue
                #==按鍵監聽==================
                self.hk.poll() 
                #==畫面更新==================
                self.frame_bgr = self._scan_full_screen()
                #==主邏輯====================

                player_loc = self.MinimapDetector(self.frame_bgr)
                self.player_loc = player_loc
                self._show_player_loc(self.player_loc)
                
                #===========================
                #畫面更新
                self._draw_map()
                cv2.waitKey(1)

        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    def MinimapDetector(self,frame)-> tuple[int,int]:
        '''
        與小圖偵測模組進行互動：傳送當前BGR圖
        return : 人物位置(x,y)
        '''
        result = self.minimap_detector.run(frame)
        return result
    
    def _show_player_loc(self,player_loc):
        
        cv2.putText(self.frame_bgr, f"人物座標: {player_loc}", org=(10, 275),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=2, color=(0, 0, 255), thickness=2)
    def draw_recorded_points(self, frame):
        '''
        功能: 將自定義的記錄座標畫在畫面上，
        並將連續兩個 walk 畫成平台 BBOX，連續兩個 rope 畫成通道 BBOX。
        '''
        if not self.recored_data:
            return frame

        # 1. 單獨點畫出
        for index, item in enumerate(self.recored_data, start=1):
            loc = item.get('loc')
            action = item.get('action')
            
            if loc is not None:
                x, y = int(loc[0]), int(loc[1])
                #預設顏色(防CTD)

                if action == "walk":
                    color = (128, 128, 128)
                elif action == "rope":
                    color = (51, 0, 25)
                elif action == "JumpRight":
                    color = (204, 204, 0)     
                elif action == "JumpLeft":
                    color = (255, 153, 51)      
                elif action == "JumpDown":
                    color = (255, 51, 153)   
                else:
                    color = (128, 128, 128)  
                cv2.rectangle(frame, (x-3, y-3), (x+3, y+3),  color, 1)



        # 2. 連續點畫出
        for i in range(len(self.recored_data) - 1):
            current_item = self.recored_data[i]
            next_item = self.recored_data[i + 1]
            
            curr_action = current_item.get('action')
            next_action = next_item.get('action')
            
            curr_loc = current_item.get('loc')
            next_loc = next_item.get('loc')
            
            if curr_loc is None or next_loc is None:
                continue
                
            x1, y1 = int(curr_loc[0]), int(curr_loc[1])
            x2, y2 = int(next_loc[0]), int(next_loc[1])
            
            # 判斷情況 A：連續兩個 walk -> 判定為平台 
            if curr_action == "walk" and next_action == "walk":
                # 以兩個點為對角線畫一個矩形
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 1)

            # 判斷情況 B：連續兩個 rope -> 判定為垂直通道
            elif curr_action == "rope" and next_action == "rope":

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)


        return frame

                            

    #=================
    # 熟鍵綁定
    #=================
    def _walk_point(self):
        '''
        移動點
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "walk"})
        self._show_last_item()
        self._show_recorded_data()

    def _rope_point(self):
        '''
        爬繩點
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "rope"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_down_point(self):
        '''
        跳下點
        '''

        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpDown"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_to_right_point(self):
        '''
        向右跳
        '''
        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpRight"})
        self._show_last_item()
        self._show_recorded_data()

    def _jump_to_left_point(self):
        '''
        向左跳
        '''
        self.recored_data.append({"loc": list(self.player_loc), "action": "JumpLeft"})
        self._show_last_item()
        self._show_recorded_data()
    #=================
    # 文書操作
    #=================
    def print_msg(self):

        print("=" * 45)
        print(" 遊戲操作與座標記錄器已啟動 - 快捷鍵說明：")
        print("=" * 45)
        print(" [F1] 儲存行為座標至 YAML")
        print(" [F2] 離開程式")
        print(" [F4] 紀錄點位：Walk (移動點)")
        print(" [F5] 紀錄點位：Rope (爬繩點)")
        print(" [F6] 紀錄點位：JumpRight(向右跳)")
        print(" [F7] 紀錄點位：JumpLeft(向左跳)")
        print(" [F8] 紀錄點位：JumpDow(向下跳)")


    def _show_last_item(self):
        if self.recored_data:  # 確保清單不是空的，避免報錯
            self.recored_data_list = self.recored_data[-1]
            print(f"最後一個記錄 -> 動作點: {self.recored_data_list.get('action')}, 座標: {self.recored_data_list.get('loc')}")

    def _show_recorded_data(self):
        '''
        功能:
            顯示所儲存的數據
        '''
        print("=" * 30)
        print(" 目前已記錄的操作資料：")

        for index, item in enumerate(self.recored_data, start=1):
            action = item.get('action', '未知動作')
            loc = item.get('loc', '無座標')
            print(f" [{index:2d}] 動作: {action:<15} | 座標: {loc}")

        print("=" * 30)

    def _save_actions_to_yaml(self):
        '''
        把座標與行為，儲存為ymal格式
        '''
        folder_path = self.map_url.parent
        yaml_path = folder_path / f"{self.map_name}.yaml"
        
        try:
            with open(yaml_path, "w") as f:
                yaml.dump(self.recored_data, f)
            print(f"檔案儲存成功，儲存檔案路徑:{yaml_path}")

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


