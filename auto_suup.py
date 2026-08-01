import interception
import threading
import keyboard
import time
import os

"""
自動撿拾

"""

class Bat:
    def __init__(self):
        #初始化
        interception.auto_capture_devices(keyboard=True, mouse=False)
        self.enable_pick = False


        
    def run(self):
        print('='* 6)
        #綁定事件
        keyboard.add_hotkey('f2',self.swithch_pick_model)
        keyboard.add_hotkey('f3',self.exit_process)
        

        #keeping run
        keyboard.wait()

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
            interception.press("z")
            time.sleep(0.1)

    def exit_process(self):
        print("退出結束")
        keyboard.unhook_all() # 安全解除
        os._exit(0)

if __name__ == "__main__":
    s = Bat()
    s.run()

        