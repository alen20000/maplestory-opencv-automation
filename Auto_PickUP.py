import interception
import threading
import keyboard
import time
import os
import win32gui
import ctypes
import sys
import win32con
import logging
"""
半自動撿拾腳本

當有觸發"方向鍵"的"上下左右"時，會自動觸發撿拾按鍵
"""


'''參數(可以在這裡調整)'''
AUTO_PICK_DELAY = 0.25
GAME_TITLE = "新楓之谷：經典版"
PICK_UP_KEY = "z" #<-撿拾預設鍵
PICK_UP_COOLDOWN = 0.05 #<-撿拾冷卻時間(秒)

class Bat:
    def __init__(self):
        # 初始化
        interception.auto_capture_devices(keyboard=True, mouse=False)
        self.MapleStory_hhwnd = None

        # Lock
        self._pick_up_lock = threading.Lock()
        self._lock = threading.Lock()
        # Flag
        self._pick_up = False
        self.is_picking_up = True

        # 開關旗標：set() = 開啟撿拾，clear() = 暫停撿拾
        # 背景執行緒只建立一次，靠這個旗標控制動/靜，不用每次都開新執行緒
        self.pick_event = threading.Event()


    #===================
    #按鍵模塊
    #===================
    def _pick_up_command(self, key):
        try:
            interception.key_down(key)
            time.sleep(PICK_UP_COOLDOWN)
        except Exception as e:
            pass
        finally:
            interception.key_up(key)
            self._pick_up = False

    def enable_pick_up(self):
        current_hwnd = win32gui.GetForegroundWindow()
        # 限定命令只發生在遊戲內
        if current_hwnd != self.MapleStory_hhwnd:
            return

        if not self.is_picking_up:
            return
        
        with self._pick_up_lock:
            if not PICK_UP_KEY:
                return
            self._pick_up = True
        threading.Thread(target=self._pick_up_command, args=(PICK_UP_KEY,), daemon=True).start()

    def toggle_pick_up(self):
        '''
        開/關 撿拾模式
        '''
        if self.is_picking_up:
            self.is_picking_up = False
            print("關閉自動撿拾")
        else:
            self.is_picking_up = True
            print("開啟自動撿拾")

    def exit_process(self):
        print("退出結束")
        keyboard.unhook_all()  # 安全解除
        os._exit(0)
    #===================
    # 遊戲窗口管理
    #===================
    def is_MapleStory_window(self):
        try:
            MapleStory_hhwnd = win32gui.FindWindow(None, GAME_TITLE)
            logging.info(f"找到視窗{GAME_TITLE}，窗柄{MapleStory_hhwnd}")
            return MapleStory_hhwnd
        except Exception as e:
            logging.warning(f"沒找到視窗{GAME_TITLE}，異常{e}")
            return False
        
    def bring_to_front_and_center_origin(self,hwnd:int):
        '''
        整理窗口位置
        將視窗帶到最前、初始化位置
        '''
        try:
            # 如果視窗被最小化了，先將它恢復正常大小
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # 將視窗帶到最前台
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"置頂視窗失敗: {e}")

        win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        #========================
        # 初始化訊息
        #========================
    def _pre_loading(self):
        self.MapleStory_hhwnd = self.is_MapleStory_window()

    def run(self):
        #========================
        # 前置處理
        self._pre_loading()
        if self.MapleStory_hhwnd:
            self.bring_to_front_and_center_origin(self.MapleStory_hhwnd)
        #========================
        print('=' * 20)
        print("F2:開/關自動撿拾\nF3:退出程式")
        print('=' * 20)

        # HOTKEY
        keyboard.add_hotkey('f2', self.toggle_pick_up)
        keyboard.add_hotkey('f3', self.exit_process)
        keyboard.add_hotkey('left', self.enable_pick_up)
        keyboard.add_hotkey('right', self.enable_pick_up)
        keyboard.add_hotkey('up', self.enable_pick_up)
        keyboard.add_hotkey('down', self.enable_pick_up)
        # Hooking
        keyboard.wait()


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

    #---主程序
    run = Bat()
    run.run()