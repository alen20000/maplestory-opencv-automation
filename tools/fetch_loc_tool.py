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
import time
'''
可以用滑快來選取座標與範圍

'''

ctypes.windll.shcore.SetProcessDpiAwareness(2)


window_name =  config.get("game.title")

hwnd, client_rect = get_window_handle_and_rect_by(window_name)
time.sleep(1)
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

# 拖拉滑鼠框選要當 template 的區域，選完按 Enter 或 Space 確認，按 c 取消
roi = cv2.selectROI("拖曳框選 HP 條區域，選完按 Enter", frame_bgr, showCrosshair=True)
x, y, w, h = roi
print(f"座標: x1={x}, y1={y}, x2={x+w}, y2={y+h}")

cropped = frame_bgr[y:y+h, x:x+w]
cv2.imwrite("hp_template.png", cropped)
print("已存檔 hp_template.png")

cv2.imshow("TEST", frame_bgr)
cv2.waitKey(0)
cv2.destroyAllWindows()