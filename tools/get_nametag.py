import time
import yaml
import cv2
import numpy as np
import win32gui
import win32con

from PIL import ImageGrab
from src.utils.common import get_mask, get_window_handle_and_rect_by, bring_to_front_and_center_origin
from config.config_loader import config

''''
人物名牌捕捉器:
程序會捕捉畫面，進到畫面後，找一個能夠清楚顯示明白的場景，按下拍照鍵"Z"即可製作名牌

'''

class GetRoleImg():
    def __init__(self):
        #config
        self.game_title = config.get("game.title")
        self.template_nametag_path = config.get("folder_path.template_nametag_path")
        self.hwnd,self.client_rect =None, None
        self.MyRole_img_path = config.get("folder_path.my_character_template_path")
        
        #img
        self.img_char_template_gray = None
        self.img_char_template_mask = None
        self.template_h, self.template_w = None, None
        self.split_width = 40

        #char location 
        self.char_left_top = None
        self.char_right_bottom =None

        #paramter
        self.max_threshold = config.get("image_processing.max_threshold")

    def run(self):
        self.connect_window()
        bring_to_front_and_center_origin(self.hwnd)
        self.preload_img()
        self.get_new_char_img()

    def connect_window(self):
        self.hwnd, self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            print(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            print(f"未匹配到指定窗口{self.game_title }")

    def preload_img(self):
        """預先載入圖片"""  
        #loard_char_template

        self.img_char_template_gray = cv2.imread(self.template_nametag_path,cv2.IMREAD_GRAYSCALE)
        self.img_char_template_mask = cv2.imread(self.template_nametag_path,cv2.IMREAD_COLOR)

        if self.img_char_template_gray is None:
            raise FileNotFoundError(f"找不到模板圖片，請確認路徑是否正確: {self.template_nametag_path}")
        #從遮罩模板轉遮罩
        self.img_char_template_mask = get_mask(self.img_char_template_mask,(0, 255, 0)) 
        #get hight and width of template
        self.template_h, self.template_w = self.img_char_template_gray.shape[:2]

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

    def get_player_location(self,frame_bgr):
        '''判斷人物角色位置'''
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
            # debug
            # cv2.imshow("split_template", split_template)
            # cv2.waitKey(100)
            
            min_val, _, min_loc, _ = cv2.minMaxLoc(result)  
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

        #找最優(分數最低)項
        best = self._select_best_image(matches)
        if best:
        # 把切片拼回，抓左上點
            nametag_x = best["loc"][0] - best["offset_x"]
            nametag_y = best["loc"][1]

            self.char_left_top = (nametag_x, nametag_y)
            self.char_right_bottom = (nametag_x + self.template_w, nametag_y + self.template_h)

            cv2.rectangle(frame_bgr, (nametag_x, nametag_y),
            (nametag_x + self.template_w, nametag_y + self.template_h), (0, 255, 0), 2)
        else:
            pass

    def _select_best_image(self,matches: list) -> dict:
        '''選出分數最好(最小)的那個區塊and 不合格拋棄'''
        #防呆
        if not matches:
            return None
        # 選出分數最好(最小)的那個區塊
        best = min(matches, key=lambda m: m["score"])

        #閥值偵測
        if best["score"] > self.max_threshold:
            return None
        
        print(f"\r最佳匹配區塊: {best['tag_type']}, 分數={best['score']:.4f}",end="", flush=True)

        return best
    
    def get_new_char_img(self):
        '''顯示畫面、手動抓圖'''
        while True:
            try:
                frame_bgr = self._capture_client_rect_frame()
                self.get_player_location(frame_bgr)
                cv2.imshow("Game Debug View", frame_bgr)
                #找到人物，觸發抓取在跳出

                # 監聽按鍵"z"，控制拍照
                key = cv2.waitKey(1) & 0xFF
                if key == ord('z'):
                    self.save_match_char_img(frame_bgr)
                    break

                # 檢查是不是按了 'q'
                elif key == ord('q'):
                    break
            except RuntimeError as e:
                print(e)
                break

        cv2.destroyAllWindows()

    def save_match_char_img(self,frame_bgr):
        '''儲存人物名白 '''

        x1,y1 = self.char_left_top
        x2,y2 = self.char_right_bottom
        crop_img = frame_bgr[y1:y2,x1:x2]

        result =cv2.imwrite(self.MyRole_img_path,crop_img)
        if result:
            print(f"\n角色標籤已儲存至:{self.MyRole_img_path}")
        else:
            print("角色標籤儲存失敗")

if __name__ == "__main__":
    run =GetRoleImg()
    time.sleep(2)
    run.run()