import ctypes
import time

# 定義 F2 的 Windows 虛擬鍵碼 (0x71)
KEY_F2 = 0x71

print("【暴力監聽測試中】")
print("請隨便打開一個記事本，或者切到遊戲視窗內，按下 F2 看看...")
print("按 Ctrl + C 可以隨時終止程式。\n")

try:
    while True:
        # 直接去問 Windows 系統：「現在 F2 有被按下嗎？」
        # 0x8000 代表此時此刻按鍵正在被壓著
        if ctypes.windll.user32.GetAsyncKeyState(KEY_F2) & 0x8000:
            print(">>> 成功抓到 F2 被按下！<<<")
            time.sleep(0.5)  # 避免按一次被連續觸發好幾次
            
        time.sleep(0.05)  # 每 0.05 秒檢查一次，不耗 CPU
        
except KeyboardInterrupt:
    print("\n程式已結束。")