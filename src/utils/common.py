
import cv2
import numpy as np

def get_mask(img, ignore_pixel_color):
    '''
    產生前景遮罩:指定顏色的像素會被忽略
    '''
    mask = np.all(img == ignore_pixel_color, axis=2).astype(np.uint8) * 255
    mask = cv2.bitwise_not(mask)
    return mask

