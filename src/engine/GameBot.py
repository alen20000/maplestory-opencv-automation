import time
import yaml
import cv2
import numpy as np
import win32gui
import mss
from PIL import ImageGrab
from src.utils.common import get_mask, get_window_handle_and_rect_by

class GameBot:
    def __init__(self):
        #config
        with open('config/global.yaml', "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        #init
        self.game_title = self.config["game"]["title"]
        self.hwnd = None
        self.client_rect = None
        self.template = None
        self.gray_frame = None
        self.frame_bgr = None
        self.nametag_path = 'img/nametag/example.png'

        self.last_loc = None  # 記住上一次找到的位置
        self.frame_count = 0  # 影格計數器

    def run(self):
        print(self.game_title)
        self.connect_window()
        self.display_screen()

    def connect_window(self):
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")

    def capture_client_rect_frame(self) -> cv2.Mat:
        '''單純負責：抓取遊戲相機視窗、縮放、轉換色彩格式，並回傳處理好的影像'''

        try:
            camera_rect = win32gui.GetClientRect(self.hwnd)

            camera_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (camera_rect[0], camera_rect[1]))
            camera_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (camera_rect[2], camera_rect[3]))
            camera_rect = (camera_rect_point_top_left[0], camera_rect_point_top_left[1], camera_rect_point_bottom_right[0], camera_rect_point_bottom_right[1])  

        except Exception:
            raise RuntimeError("視窗已關閉或遺失。")


        current_frame = ImageGrab.grab(bbox=camera_rect)
        
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR
        return frame_bgr


    def get_player_location(self,frame_bgr):

        frame_gray = cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2GRAY)
        img_char_template_gray = cv2.imread(self.nametag_path,cv2.IMREAD_GRAYSCALE)
        img_char_template_mask = cv2.imread(self.nametag_path,cv2.IMREAD_COLOR)

        #hight and width of template
        h, w = img_char_template_gray.shape[:2]
        SPITE_WIDTH = 40

        # max給少於一時補1
        num_splits = max(1, w//SPITE_WIDTH)
        w_splits = w // num_splits
        # 這是印在迴圈外面的開場白（正常換行即可）
        # print(f"將模板圖片分割為 {num_splits} 個區塊，每個區塊寬度為 {SPITE_WIDTH} 像素。")
        #遮罩
        mask =get_mask(img_char_template_mask,(0, 255, 0))

        matches = []
        for i in range(num_splits):
            x_s = i * w_splits
            x_e = (i+1) * w_splits  if i < num_splits-1 else w 

            split_template = img_char_template_gray[:, x_s:x_e]
            split_mask = mask[:, x_s:x_e]

            result = cv2.matchTemplate(
                frame_gray,split_template,cv2.TM_SQDIFF_NORMED,mask=split_mask
            )

            # min_loc 是這一份切片「自己」在地圖上找到的最佳匹配左上角座標
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)  
            loc = min_loc
            score = min_val

            matches.append({
                "tag_type": f"{i+1}/{num_splits}",
                "loc": loc,
                "score": score,
                "w": split_template.shape[1],
                "h": split_template.shape[0],
                "offset_x": x_s,
            })

            # print(f"  區塊 {i+1}/{num_splits}: 找到位置={loc}, "
            #     f"分數(越小越準)={score:.4f}")

        # 選出分數最好(最小)的那個區塊
        best = min(matches, key=lambda m: m["score"])
        # print(f"\n最佳匹配區塊: {best['tag_type']}, 分數={best['score']:.4f}")

        # 把「這個區塊找到的位置」換算回「整個名牌」的位置
        # 因為找到的是這個切片的左上角，要扣掉這個切片的 offset_x 才能回推整個名牌的左上角
        nametag_x = best["loc"][0] - best["offset_x"]
        nametag_y = best["loc"][1]

        self.last_loc = (nametag_x, nametag_y, w, h)

        cv2.rectangle(frame_bgr, (nametag_x, nametag_y),
        (nametag_x + w, nametag_y + h), (0, 255, 0), 2)
        


    def display_screen(self):

        print("開始擷取視窗畫面，按 'q' 鍵關閉")

        while True:
            try:

                self.frame_count += 1 
                if self.frame_count % 5 == 0 or self.last_loc is None:
                    frame_bgr = self.capture_client_rect_frame()
                else:
                    if self.last_loc:
                        nametag_x, nametag_y, w, h = self.last_loc
                        cv2.rectangle(frame_bgr, (nametag_x, nametag_y),
                        (nametag_x + w, nametag_y + h), (0, 255, 0), 2)                         



                self.get_player_location(frame_bgr)

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
    pass