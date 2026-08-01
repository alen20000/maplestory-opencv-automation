import cv2
import numpy as np
import win32gui
import win32ui
import win32con

class MonsterDetector:
    def __init__(self, window_title="MapleStory"):
        self.window_title = window_title
        self.hwnd = None
        self._find_window()

    def _find_window(self):
        """尋找遊戲視窗的 Handle"""
        self.hwnd = win32gui.FindWindow(None, self.window_title)
        if not self.hwnd:
            print(f"[警告] 找不到視窗: {self.window_title}，將使用全螢幕替代或等待...")

    def capture_window(self):
        """針對特定視窗抓圖，解決遮擋與全螢幕效能問題"""
        if not self.hwnd:
            return None

        # 取得視窗大小
        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
        width = right - left
        height = bottom - top

        # 透過 Windows API 建立裝置內容 (DC) 進行高效截圖
        hwnd_dc = win32gui.GetWindowDC(self.hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # 複製視窗畫面到點陣圖
        # 0 = SRCCOPY
        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        # 轉換成 OpenCV 可以讀取的 numpy 陣列
        signed_ints_array = save_bitmap.GetBitmapBits(True)
        img = np.frombuffer(signed_ints_array, dtype='uint8')
        img.shape = (height, width, 4) # BGRA

        # 清理資源
        win32gui.ReleaseDC(self.hwnd, hwnd_dc)
        win32ui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()

        # 轉成 BGR 格式
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def run(self):
        """主執行迴圈"""
        print("開始執行怪物辨識，按下 'q' 鍵離開...")
        while True:
            frame = self.capture_window()
            if frame is None:
                break

            # 簡單的顏色過濾示範 (例如抓取特定怪物的顏色)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_red = np.array([0, 150, 150])
            upper_red = np.array([10, 255, 255])
            mask = cv2.inRange(hsv, lower_red, upper_red)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) > 500:
                    x, y, w, h = cv2.boundingRect(cnt)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.imshow("Window Monster Detector", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()

if __name__ == "__main__":
    # 使用時只要帶入遊戲視窗的標題名稱即可
    detector = MonsterDetector(window_title="你的遊戲視窗名稱")
    detector.run()