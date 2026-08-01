import cv2
import numpy as np
import time
import threading
import keyboard
import win32gui
from PIL import ImageGrab
import time

class WindowCapureTool:
    def __init__(self):

        self.running = True
        self.output_folder = "processed_screenshots"

    def run(self):
        # 綁定熱鍵
        keyboard.add_hotkey('f2', self.grab_screenshot)
        keyboard.add_hotkey('f3', self.stop)


        print("操作：在遊戲內按截圖鍵後，切回或在這邊按下 F2 讀取最新圖片，F3 退出\n")
        
        # 在背景執行緒持續更新座標
        threading.Thread(target=self._print_mouse_position, daemon=True).start()

        # 主迴圈等待退出指令
        while self.running:
            time.sleep(0.1)
            
        print("【程式已安全關閉】")
        keyboard.unhook_all() # 取消所有熱鍵綁定
        cv2.destroyAllWindows()

    def grab_screenshot(self):
        '''抓取目前前景視窗的螢幕截圖(包含窗邊)'''

        hwnd = win32gui.GetForegroundWindow()
        wx1, wy1, wx2, wy2 = win32gui.GetWindowRect(hwnd)
        _, _, c_width, c_height = win32gui.GetClientRect(hwnd)
        total_width = wx2 - wx1
        total_height = wy2 - wy1
        border_x = (total_width - c_width) // 2

        real_bbox = (
                wx1 + border_x, 
                wy1,             
                wx2 - border_x, 
                wy1 + c_height + (total_height - c_height - (border_x * 2)) # 自動適配標題列高度
            )


        screenshot = ImageGrab.grab(bbox=real_bbox) 
        frame = np.array(screenshot)
        screenshot = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        #save the screenshot
        cv2.imwrite(f"{self.output_folder}/screenshot_{int(time.time())}.png", screenshot)
        print(f"已抓取螢幕截圖，存檔於 {self.output_folder}/screenshot_{int(time.time())}.png")

        cv2.imshow("TEST", screenshot)
        cv2.waitKey(0)

    def stop(self):
        """安全退出"""
        print("\n>>> 收到 F3 退出訊號... <<<")
        self.running = False

    def _print_mouse_position(self):
        """在背景執行緒持續更新座標顯示"""
        print("--- 滑鼠座標追蹤中 ---", end="\r")
        try:
            while self.running:
                hwnd = win32gui.GetForegroundWindow()
                try:
                    win_rect = win32gui.GetWindowRect(hwnd)
                    win_left, win_top = win_rect[0], win_rect[1]
                    
                    import pyautogui
                    mouse_x, mouse_y = pyautogui.position()
                    
                    rel_x = mouse_x - win_left
                    rel_y = mouse_y - win_top
                    
                    print(f"\r視窗座標 -> Rel X: {rel_x:4d}, Y: {rel_y:4d} | Abs X: {mouse_x:4d}, Y: {mouse_y:4d}    ", end="", flush=True)
                except Exception:
                    print("--- 請將滑鼠移到目標視窗內 ---                             ", end="\r")
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    tool = WindowCapureTool()
    tool.run()