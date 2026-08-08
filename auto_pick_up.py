import interception
import threading
import keyboard
import time
import os
import win32gui

import time
"""
一個簡單的自動撿拾腳本

"""
AUTO_PICK_DELAY = 0.3
GAME_TITLE = "新楓之谷：經典版"
PICK_UP_KEY = "z"

#放按鍵忽略清單
filter_typing = ['left','right','up','down']

class Bat:
    def __init__(self):
        #初始化
        interception.auto_capture_devices(keyboard=True, mouse=False)
        self.enable_pick = False
        self.MapleStory_hhwnd = self.is_MapleStory_window()
        self.last_key_time = 0
        self.typing_timeout = 1  #超過多少時間沒輸入，則自動拾取。 
        #states
        self.state_busy = False


    def _pick_up_action(self):

        if  self.state_busy:
            return
        while self.enable_pick is True:
            current_time = time.time()
            if win32gui.GetForegroundWindow() == self.MapleStory_hhwnd:

                if current_time - self.last_key_time > AUTO_PICK_DELAY:
                    self.state_busy = False
                if  self.state_busy is False:
                    interception.press(PICK_UP_KEY)
                    time.sleep(AUTO_PICK_DELAY)


    def _check_tpying(self,event):
        if event.name in filter_typing:
            return
        self.last_key_time = time.time()
        self.state_busy = True



    def is_MapleStory_window(self):
        try:
            MapleStory_hhwnd = win32gui.FindWindow(None,GAME_TITLE) 
            print(f"找到視窗{GAME_TITLE}，窗柄{MapleStory_hhwnd}")
            return MapleStory_hhwnd
        except:
            print(f"沒找到視窗{GAME_TITLE}")
            return False

    def diable_pick_up(self):
        '''
        開啟撿拾模式
        '''
        if self.enable_pick is False:
            print('開啟拾取')
            self.enable_pick = True
            threading.Thread(target=self._pick_up_action, daemon=True).start()

        else:
            print('退出拾取')
            self.enable_pick = False

    def run(self):
        print('='* 6)
        print("F2:開/關自動撿拾/nF3:退出程式")
        #綁定事件
        keyboard.add_hotkey('f2',self.diable_pick_up)
        keyboard.add_hotkey('f3',self.exit_process)
        
        #鍵盤監聽
        keyboard.hook(self._check_tpying)
        #等待(用途：阻斷程序結束)
        keyboard.wait()




    def exit_process(self):
        print("退出結束")
        keyboard.unhook_all() # 安全解除
        os._exit(0)

if __name__ == "__main__":
    run = Bat()
    run.run()

        