import interception
import threading
import keyboard
import time
import os
import win32gui
import ctypes
import sys
import os
"""
一個簡單的自動撿拾腳本
"""
AUTO_PICK_DELAY = 0.25

GAME_TITLE = "新楓之谷：經典版"
PICK_UP_KEY = "z" #<-撿拾預設鍵

# 放按鍵忽略清單
filter_typing = ['left', 'right', 'up', 'down']


class Bat:
    def __init__(self):
        # 初始化
        interception.auto_capture_devices(keyboard=True, mouse=False)
        self.MapleStory_hhwnd = self.is_MapleStory_window()
        self.last_key_time = 0
        self.typing_timeout = 0.3  # 超過多少時間沒輸入，則自動拾取。

        # states
        self.state_busy = False
        self._lock = threading.Lock()

        # 開關旗標：set() = 開啟撿拾，clear() = 暫停撿拾
        # 背景執行緒只建立一次，靠這個旗標控制動/靜，不用每次都開新執行緒
        self.pick_event = threading.Event()

    def _pick_up_action(self):
        '''撿拾行為（背景常駐執行緒，永遠不結束）'''
        while True:
            # 沒開啟時卡在這裡等待，不耗 CPU；被 set() 後才會往下執行
            self.pick_event.wait()

            current_time = time.time()
            if win32gui.GetForegroundWindow() == self.MapleStory_hhwnd:
                with self._lock:
                    if current_time - self.last_key_time > AUTO_PICK_DELAY:
                        self.state_busy = False
                    is_busy = self.state_busy

                if is_busy is False:
                    interception.press(PICK_UP_KEY)

            time.sleep(AUTO_PICK_DELAY)

    def _check_tpying(self, event):
        '''檢查有沒有在輸入'''
        if event.name in filter_typing:
            return
        with self._lock:
            self.last_key_time = time.time()
            self.state_busy = True

    def is_MapleStory_window(self):
        try:
            MapleStory_hhwnd = win32gui.FindWindow(None, GAME_TITLE)
            print(f"找到視窗{GAME_TITLE}，窗柄{MapleStory_hhwnd}")
            return MapleStory_hhwnd
        except Exception as e:
            print(f"沒找到視窗{GAME_TITLE}，異常{e}")
            return False

    def toggle_pick_up(self):
        '''
        開/關 撿拾模式
        '''
        
        if self.pick_event.is_set():
            print('退出拾取')
            self.pick_event.clear()
        else:
            print('開啟拾取')
            self.state_busy = False  # 清空上次殘留的狀態
            self.pick_event.set()

    def run(self):
        print('=' * 6)
        print("F2:開/關自動撿拾\nF3:退出程式")

        # 開一個線程(唯一)
        threading.Thread(target=self._pick_up_action, daemon=True).start()

        # 綁定事件
        keyboard.add_hotkey('f2', self.toggle_pick_up)
        keyboard.add_hotkey('f3', self.exit_process)

        # 鍵盤監聽
        keyboard.hook(self._check_tpying)
        # 等待(用途：阻斷程序結束)
        keyboard.wait()

    def exit_process(self):
        print("退出結束")
        keyboard.unhook_all()  # 安全解除
        os._exit(0)

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