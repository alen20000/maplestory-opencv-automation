import cv2
import numpy as np

def extract_id_and_badge():
    img_path = 'map.png'
    img = cv2.imread(img_path)

    y1, y2 = 200, 600
    x1, x2 = 500, 940

    hsv = cv2.imread("img")


    crop_area = img[y1:y2, x1:x2]
    

    gray = cv2.cvtColor(crop_area, cv2.COLOR_BGR2GRAY)
    

    _, thresh = cv2.threshold(gray, 150, 200, cv2.THRESH_BINARY)
    

    b_channel, g_channel, r_channel = cv2.split(crop_area)
    alpha_channel = thresh # 以二值化結果作為透明遮罩
    
    cv2.imshow("Map", thresh)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    extract_id_and_badge()