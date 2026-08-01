import cv2
import numpy as np

img_camera = cv2.imread("map.png", cv2.IMREAD_GRAYSCALE)
img_nametag = cv2.imread("sample.png", cv2.IMREAD_GRAYSCALE)

img_camera = cv2.GaussianBlur(img_camera, (3, 3), 0)
img_nametag = cv2.GaussianBlur(img_nametag, (3, 3), 0)

lower_white, upper_white = (0, 175)
img_roi = cv2.inRange(img_camera , lower_white, upper_white)
img_nametag_mask = cv2.inRange(img_nametag, lower_white, upper_white)

# 1. 執行樣板匹配
# 使用 cv2.TM_SQDIFF_NORMED 演算法，並帶入剛剛做好的 nametag 遮罩
result = cv2.matchTemplate(img_roi, img_nametag_mask, cv2.TM_SQDIFF_NORMED, mask=img_nametag_mask)

# 2. 解析匹配結果
# cv2.minMaxLoc 可以幫我們找出整張圖裡面「差異最小（最吻合）」的位置
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

# 因為我們用的是 SQDIFF，所以「min_val」就是最低誤差（分數越低越好）
# min_loc 就是找到的最佳位置 (x, y)
match_x, match_y = min_loc

print(f"找到目標！最佳匹配位置座標: ({match_x}, {match_y})，誤差分數: {min_val:.4f}")

# 3. 畫出框框把找到的標籤標示出來
# 取得 nametag 的寬高
h, w = img_nametag.shape

# 把原本讀進來的 map.png 轉回彩色，這樣畫出來的框框才會是綠色的
img_debug = cv2.cvtColor(img_camera, cv2.COLOR_GRAY2BGR)

# 在找到的位置畫一個矩陣框 (BGR: 0, 255, 0 代表綠色)
cv2.rectangle(img_debug, (match_x, match_y), (match_x + w, match_y + h), (0, 255, 0), 2)

# 4. 顯示結果
cv2.imshow('Match Result', img_debug)
cv2.waitKey(0)
cv2.destroyAllWindows()