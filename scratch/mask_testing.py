import cv2
from pathlib import  Path
import numpy as np
root_dir = Path(__file__).resolve().parent.parent
img_path = str(root_dir / "img/monsters/Dark_Stump.png")

img_bgr = cv2.imread(img_path,cv2.IMREAD_COLOR)
img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
lower= np.array([35, 43, 46])  # 綠色下限
upper = np.array([77, 255, 255])  # 綠色上限
mask = cv2.inRange(img_hsv, lower, upper)
mask = cv2.bitwise_not(mask)


cv2.imshow("test",mask)




cv2.waitKey(0)
cv2.destroyAllWindows()


