import time
import yaml
import cv2
import numpy as np
import win32gui
import mss
from PIL import ImageGrab
from src.utils.common import get_mask, get_window_handle_and_rect_by,window_infront_dest,bring_to_front_and_center_origin

# --- 這裡放常數與參數設定 ---
MAX_THRESHOLD = 0.07


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
        self.nametag_path = 'img/nametag/new_char.png'


        self.last_loc = None  # 記住上一次找到的位置
        self.frame_count = 0  # 影格計數器
        #parameter
        self.split_width = 40

        #img
        self.img_char_template_gray = None
        self.img_char_template_mask = None
        self.template_h, self.template_w = None, None
        self.frame_bgr = None

    def run(self):

        #預處理
        self.connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        self.preload_img()

        #process
        self.frame_bgr = self.scan_full_screen()
        cv2.imshow("Game Debug View", self.frame_bgr)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def connect_window(self):
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")
    def preload_img(self):
        """預先載入圖片"""

        #loard_char_template
        self.img_char_template_gray = cv2.imread(self.nametag_path,cv2.IMREAD_GRAYSCALE)
        self.img_char_template_mask = cv2.imread(self.nametag_path,cv2.IMREAD_COLOR)
        #從遮罩模板轉遮罩
        self.img_char_template_mask = get_mask(self.img_char_template_mask,(0, 255, 0)) 


        #get hight and width of template
        self.template_h, self.template_w = self.img_char_template_gray.shape[:2]

    def bid_char(self):
        '''角色座標判斷'''
    def BGR2Binary(self,img):
    def scan_full_screen(self):
        '''全螢幕判斷'''
        try:
            screen_rect = win32gui.GetDesktopRect()
            screen_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (screen_rect[0], screen_rect[1]))
            screen_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (screen_rect[2], screen_rect[3]))
            screen_rect = (screen_rect_point_top_left[0], screen_rect_point_top_left[1], screen_rect_point_bottom_right[0], screen_rect_point_bottom_right[1])  

        except Exception:
            pass

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

        '''圖片取灰階並二值化'''

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return binary
        return frame_bgr

    def screen_loop(self):
        '''全螢幕刷新'''
        while True:
            self.frame_bgr = self.scan_full_screen()
            cv2.imshow("Game Debug View", self.frame_bgr)
            if cv2.waitKey(33) & 0xFF == ord('q'):
                break
    
    def _capture_client_rect_frame(self) -> cv2.Mat:
        '''單純負責：抓取遊戲相機視窗、縮放、轉換色彩格式，並回傳處理好的影像'''

        try:
            camera_rect = win32gui.GetClientRect(self.hwnd)

            camera_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (camera_rect[0], camera_rect[1]))
            camera_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (camera_rect[2], camera_rect[3]))
            camera_rect = (camera_rect_point_top_left[0], camera_rect_point_top_left[1], camera_rect_point_bottom_right[0], camera_rect_point_bottom_right[1])  

        except Exception:
            raise RuntimeError("視窗已關閉或遺失。")

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=camera_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

        return frame_bgr

    def select_best_image(self,matches: list) -> dict:
        '''選出分數最好(最小)的那個區塊and 不合格拋棄'''
        #防呆
        if not matches:
            return None
        # 選出分數最好(最小)的那個區塊
        best = min(matches, key=lambda m: m["score"])

        #閥值產茶
        if best["score"] > MAX_THRESHOLD:
            return None
        
        print(f"\r最佳匹配區塊: {best['tag_type']}, 分數={best['score']:.4f}",end="", flush=True)

        return best
    
    def get_player_location(self,frame_bgr):
        
        '''判斷主角座標'''
        frame_gray = cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2GRAY)

        num_splits = max(1, self.template_w//self.split_width)
        w_splits = self.template_w // num_splits

        matches = []

        #切片與匹配
        for i in range(num_splits):
            x_s = i * w_splits
            x_e = (i+1) * w_splits  if i < num_splits-1 else self.template_w 

            split_template = self.img_char_template_gray[:, x_s:x_e]
            split_mask = self.img_char_template_mask[:, x_s:x_e]

            result = cv2.matchTemplate(
                frame_gray,split_template,cv2.TM_SQDIFF_NORMED,mask=split_mask
            )
            #debug
            # cv2.imshow("split_template", split_template)
            # cv2.waitKey(100)

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

        #找最好(分數最低)的
        best = self.select_best_image(matches)

        if best:
        # 把切片拼回來，抓左上點
            nametag_x = best["loc"][0] - best["offset_x"]
            nametag_y = best["loc"][1]

            cv2.rectangle(frame_bgr, (nametag_x, nametag_y),
            (nametag_x + self.template_w, nametag_y + self.template_h), (0, 255, 0), 2)
        else:
            pass
    def display_screen(self):
        '''顯示畫面'''
        while True:
            try:

                frame_bgr = self._capture_client_rect_frame()
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