import cv2
import numpy as np
import time
import threading
import keyboard
import win32gui
import pyautogui
from PIL import ImageGrab
import ctypes

# 一定要在所有 win32gui / ImageGrab / pyautogui 呼叫之前執行
ctypes.windll.shcore.SetProcessDpiAwareness(2)


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
        keyboard.unhook_all()  # 取消所有熱鍵綁定
        cv2.destroyAllWindows()

    def _get_client_screen_bbox(self, hwnd):
        """
        統一的 client 區域座標計算：
        回傳這個視窗 client 區域在「螢幕」上的絕對座標 (x1, y1, x2, y2)。
        這跟主程式 hp_lect 用的座標系統完全一致。
        """
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        x1, y1 = win32gui.ClientToScreen(hwnd, (left, top))
        x2, y2 = win32gui.ClientToScreen(hwnd, (right, bottom))
        return x1, y1, x2, y2

    def grab_screenshot(self):
        '''抓取目前前景視窗的 client 區域截圖（不含標題列與邊框）'''

        hwnd = win32gui.GetForegroundWindow()
        real_bbox = self._get_client_screen_bbox(hwnd)

        screenshot = ImageGrab.grab(bbox=real_bbox)
        frame = np.array(screenshot)
        screenshot = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # save the screenshot
        filename = f"{self.output_folder}/screenshot_{int(time.time())}.png"
        cv2.imwrite(filename, screenshot)
        print(f"已抓取螢幕截圖，存檔於 {filename}")
        print(f"截圖畫面大小 (高, 寬): {screenshot.shape[:2]}  ← 這就是合法的 client 相對座標範圍")

        cv2.imshow("TEST", screenshot)
        cv2.waitKey(0)

    def stop(self):
        """安全退出"""
        print("\n>>> 收到 F3 退出訊號... <<<")
        self.running = False

    def _print_mouse_position(self):
        """在背景執行緒持續更新座標顯示（改用 client 相對座標，跟主程式座標系統一致）"""
        print("--- 滑鼠座標追蹤中 ---", end="\r")
        try:
            while self.running:
                hwnd = win32gui.GetForegroundWindow()
                try:
                    cx1, cy1, cx2, cy2 = self._get_client_screen_bbox(hwnd)

                    mouse_x, mouse_y = pyautogui.position()

                    rel_x = mouse_x - cx1
                    rel_y = mouse_y - cy1

                    # 判斷滑鼠是否在 client 範圍內，超出範圍就提示，避免量到無效座標
                    in_range = (0 <= rel_x <= (cx2 - cx1)) and (0 <= rel_y <= (cy2 - cy1))
                    tag = "OK" if in_range else "超出client範圍"

                    print(
                        f"\rClient相對 -> X: {rel_x:4d}, Y: {rel_y:4d} "
                        f"| 螢幕絕對 X: {mouse_x:4d}, Y: {mouse_y:4d} [{tag}]    ",
                        end="", flush=True
                    )
                except Exception:
                    print("--- 請將滑鼠移到目標視窗內 ---                             ", end="\r")

                time.sleep(0.1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    tool = WindowCapureTool()
    tool.run()