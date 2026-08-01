import cv2
import numpy as np

def nothing(x):
    pass

# 讀取圖片或打開攝影機
img = cv2.imread("sample.png")
img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# 建立一個視窗與滑桿 (Trackbars)
cv2.namedWindow("Color Picker")
cv2.createTrackbar("Lower H", "Color Picker", 0, 179, nothing)
cv2.createTrackbar("Lower S", "Color Picker", 0, 255, nothing)
cv2.createTrackbar("Lower V", "Color Picker", 0, 255, nothing)
cv2.createTrackbar("Upper H", "Color Picker", 179, 179, nothing)
cv2.createTrackbar("Upper S", "Color Picker", 255, 255, nothing)
cv2.createTrackbar("Upper V", "Color Picker", 255, 255, nothing)

while True:
    # 取得當前滑桿的數值
    lh = cv2.getTrackbarPos("Lower H", "Color Picker")
    ls = cv2.getTrackbarPos("Lower S", "Color Picker")
    lv = cv2.getTrackbarPos("Lower V", "Color Picker")
    uh = cv2.getTrackbarPos("Upper H", "Color Picker")
    us = cv2.getTrackbarPos("Upper S", "Color Picker")
    uv = cv2.getTrackbarPos("Upper V", "Color Picker")

    lower_bound = np.array([lh, ls, lv])
    upper_bound = np.array([uh, us, uv])

    # 進行 inRange 過濾
    mask = cv2.inRange(img_hsv, lower_bound, upper_bound)

    # 顯示過濾後的畫面
    cv2.imshow("Color Picker", mask)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()