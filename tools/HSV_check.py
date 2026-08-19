import os
from pathlib import Path
import cv2
import numpy as np
'''
功能:查圖片 HSV範圍
'''

#path
current_dir = Path(__file__).parent
template_path = current_dir.parent / "img" / "health_stuff" / "mp_template.png"
# 讀取你的模板
img = cv2.imread(template_path, cv2.IMREAD_COLOR)
# 轉成 HSV
hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 計算整張圖片中 H, S, V 的最大值與最小值
h, s, v = cv2.split(hsv_img)
print(f"H 範圍: {np.min(h)} ~ {np.max(h)}")
print(f"S 範圍: {np.min(s)} ~ {np.max(s)}")
print(f"V 範圍: {np.min(v)} ~ {np.max(v)}")
