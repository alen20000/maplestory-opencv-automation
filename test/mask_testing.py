import cv2
from pathlib import  Path
import numpy as np
root_dir = Path(__file__).resolve().parent.parent
test_img = str(root_dir / "img/monsters/Dark_Stump.png")

img = cv2.imread(test_img,cv2.COLOR_BGR2GRAY)
# mask = cv2.imread("mask.png")
cv2.imshow("test",img)

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lower_green = np.array([35, 43, 46])  # 綠色下限
upper_green = np.array([77, 255, 255])  # 綠色上限
green_mask = cv2.inRange(hsv, lower_green, upper_green)

cv2.imshow("test",green_mask)




cv2.waitKey(0)
cv2.destroyAllWindows()


