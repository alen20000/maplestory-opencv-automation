import time
import pyautogui
import win32gui
'''
小工具，查滑鼠座標、頂層視窗內的相對座標`,
'''


print("【座標查詢工具啟動】")
print("請將滑鼠移到目標視窗內，按 Ctrl+C 可以停止\n。")
print("\n")

try:
    while True:
        # 動態抓取當前最前端的視窗
        hwnd = win32gui.GetForegroundWindow()
        win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(hwnd)
        
        # 取得滑鼠座標
        mouse_x, mouse_y = pyautogui.position()
        
        # 計算相對座標
        rel_x = mouse_x - win_left
        rel_y = mouse_y - win_top

        print(f"\033[2A絕對座標 -> X: {mouse_x:4d}, Y: {mouse_y:4d}      \n相對座標 -> X: {rel_x:4d}, Y: {rel_y:4d}      ")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n工具已關閉。")