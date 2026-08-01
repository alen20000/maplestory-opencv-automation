import time
import interception
'''
attack 
'''
# 自動捕捉裝置
interception.auto_capture_devices(keyboard=True, mouse=True)

print("測試中...")
time.sleep(2)

# 測試送出一次 z 鍵
interception.press("z")
print("已透過驅動送出 Z 鍵")
class behavior:
    def __init__(self):
        interception.auto_capture_devices(keyboard=True, mouse=True)

    def press_shift(self):
        interception.press("ctrl")
        
    def auto_pick_up(self):
        while True:
            interception.press("z")
            time.sleep(0.1)

if __name__ == "__main__":
    behavior_instance = behavior()
    behavior_instance.auto_pick_up()