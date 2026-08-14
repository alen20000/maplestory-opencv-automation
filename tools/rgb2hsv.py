import cv2
import numpy as np

# 注意：OpenCV 陣列順序是 BGR， RGB 要倒過來填入 [Blue, Green, Red]
# RGB(255, 255, 240) -> BGR(240, 255, 255)
target_bgr = np.array([[[136, 255, 255]]], dtype=np.uint8)
target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)

print("轉換出來的 HSV 是：", target_hsv[0][0])