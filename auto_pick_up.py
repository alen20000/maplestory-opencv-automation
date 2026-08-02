import interception
import threading
import keyboard
import time
import os
import win32gui
"""
自動撿拾

"""

class Bat:
    def __init__(self):
        #config
        self.game_title = "新楓之谷：經典版"
        self.auto_pick_delay = 0.3
        #初始化
        interception.auto_capture_devices(keyboard=True, mouse=False)
        self.enable_pick = False
        self.MapleStory_hhwnd = self.is_MapleStory_window()



        
    def run(self):
        print('='* 6)
        #綁定事件
        keyboard.add_hotkey('f2',self.swithch_pick_model)
        keyboard.add_hotkey('f3',self.exit_process)
        

        #keeping run
        keyboard.wait()

    def is_MapleStory_window(self):
        print(self.game_title)
        try:
            MapleStory_hhwnd = win32gui.FindWindow(None,self.game_title) 
            print(f"找到視窗{self.game_title}，窗柄{MapleStory_hhwnd}")
            return MapleStory_hhwnd
        except:
            print(f"沒找到視窗{self.game_title}")
            return False

    def swithch_pick_model(self):

        if self.enable_pick is False:
            print('開啟拾取')
            self.enable_pick = True
            threading.Thread(target=self.auto_pick_up, daemon=True).start()

        else:
            print('退出拾取')
            self.enable_pick = False

    def auto_pick_up(self):
        while self.enable_pick is True:
            if win32gui.GetForegroundWindow() == self.MapleStory_hhwnd:
                interception.press("z")
            time.sleep(self.auto_pick_delay)

    def exit_process(self):
        print("退出結束")
        keyboard.unhook_all() # 安全解除
        os._exit(0)

if __name__ == "__main__":
    s = Bat()
    s.run()

        