import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.config_loader import config 
import interception
import time
from config.config_loader import config
from src.utils.common import get_window_handle_and_rect_by, bring_to_front_and_center_origin
import win32gui
import cv2
import ctypes
import numpy as np
from PIL import ImageGrab

'''
DPI跑掉太誇張了 搞不定
'''
ctypes.windll.shcore.SetProcessDpiAwareness(2)
window_name =  config.get("game.title")

hwnd, client_rect = get_window_handle_and_rect_by(window_name)
bring_to_front_and_center_origin(hwnd)
print(hwnd, client_rect)

#相對座標
screen_rect = win32gui.GetClientRect(hwnd)

print(f"screen_rect: {screen_rect}")
#絕對座標
abs_x2, abs_y2 = win32gui.ClientToScreen(hwnd, (screen_rect[2], screen_rect[3]))
x1,y1 = win32gui.ClientToScreen(hwnd, (screen_rect[0], screen_rect[1]))
x2,y2 = win32gui.ClientToScreen(hwnd, (screen_rect[2], screen_rect[3]))
abd_lect = (x1,y1,x2,y2)
current_frame = ImageGrab.grab(bbox=abd_lect)
current_frame = np.array(current_frame)
frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

hp_bar = config.get("health_detector.hp_lect")
hp_x1, hp_y1, hp_x2, hp_y2 = hp_bar[0], hp_bar[1], hp_bar[2], hp_bar[3]
print(f"hp_x1:{hp_x1}, hp_y1:{hp_y1}, hp_x2:{hp_x2}, hp_y2:{hp_y2}")
print("當前實際截圖畫面大小 (高, 寬):", frame_bgr.shape[:2])
img_hp = frame_bgr[hp_y1:hp_y2, hp_x1:hp_x2]
cv2.imshow("TEST", img_hp)
cv2.waitKey(0)
cv2.destroyAllWindows()