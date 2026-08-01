from cmath import rect
import yaml
import os
import cv2
import numpy as np
import win32gui
from PIL import ImageGrab


class GameBot:
    def __init__(self, config_path: str = "config/global.yaml"):

        #讀取設定檔取得視窗標題
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)


        self.game_title = self.config["game"]["title"]
        self.hwnd, self.rect =  self._init_window()
        self.target_monster = None
        self.gray_frame = None
        self.frame_bgr = None

    def _init_window(self) -> tuple[int, tuple]:
        """ 取得視窗句柄與座標 """
        hwnd = win32gui.FindWindow(None, self.game_title)
        if not hwnd:
            raise RuntimeError(f"沒匹配指定的視窗: {self.game_title}")
        print(f"成功讀取遊戲標題: {self.game_title}，視窗句柄: {hwnd}")

        rect = win32gui.GetWindowRect(hwnd)
        print(f"視窗大小: {rect}")
        return hwnd, rect

    def start(self):
        self.show_screen()

    def get_player_location_by_nametag(self):
        """ 透過名字標籤來取得玩家位置 """



    def capture_frame(self):
        """單純負責：抓取視窗、縮放、轉換色彩格式，並回傳處理好的影像"""
        try:
            # 1. 取得最新視窗座標
            self.rect = win32gui.GetWindowRect(self.hwnd)
        except Exception:
            # 如果抓不到座標拋出異常，讓外層去處理關閉
            raise RuntimeError("視窗已關閉或遺失。")

        img = ImageGrab.grab(bbox=self.rect)
        

        width, height = img.size 
        new_width, new_height = width // 1, height // 1
        img_resized = img.resize((new_width, new_height), 1)


        frame = np.array(img_resized)
        self.frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self.gray_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        return self.frame_bgr

    def _template_monster(self):

        self.target_monster = cv2.imread('monsters_img/mushroom_1.png', cv2.IMREAD_GRAYSCALE)
        if self.target_monster is None:
            raise FileNotFoundError("錯誤：找不到模板圖片，請檢查路徑是否正確！")
        
        h,w = self.target_monster.shape[:2]
        return h,w

    def to_match_templates(self,):

    
    def show_screen(self):

        print("開始擷取視窗畫面，按 'q' 鍵可關閉視窗...")
        h,w = self._template_monster()
        while True:
            try:
                # 1. 呼叫剛剛拆出來的抓圖方法取得畫面
                frame_bgr = self.capture_frame()
                
                # ==========================================
                # 💡 之後你可以在這裡加入你的邏輯與影像辨識
                # 例如: 
                # game_logic_process(frame_bgr)
                # ==========================================

                res = cv2.matchTemplate(self.gray_frame, self.target_monster, cv2.TM_CCOEFF_NORMED)
                threshold = 0.7
                loc = np.where(res >= threshold)
                for pt in zip(*loc[::-1]):  
                    cv2.rectangle(frame_bgr, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)
                    
                # 2. 顯示畫面
                cv2.imshow("Game Debug View", frame_bgr)

                # 3. 偵測是否按下 'q' 鍵退出
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            except RuntimeError as e:
                print(e)
                break

        # 釋放資源
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # 建立實例並執行畫面擷取測試
    test = GameBot()
    test.start()