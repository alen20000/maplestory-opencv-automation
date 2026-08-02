
import cv2
import numpy as np
import win32gui
def get_mask(img, ignore_pixel_color):
    '''
    產生前景遮罩:指定顏色的像素會被忽略
    '''
    mask = np.all(img == ignore_pixel_color, axis=2).astype(np.uint8) * 255
    mask = cv2.bitwise_not(mask)

    return mask


def get_window_handle_and_rect_by(title_name:str)-> tuple[int, tuple[int, int, int, int]]:
    """取得視窗句柄與視窗在螢幕之絕對座標 """

    hwnd = win32gui.FindWindow(None,title_name)
    if not hwnd:
        return None

    # 取得視窗的絕對座標：回傳 (left, top, right, bottom)
    window_rect = win32gui.GetWindowRect(hwnd)

    return hwnd, window_rect


def padding_rect(rect,padding_value) -> tuple[tuple[int,int,int,int],int]:
    '''擴大''' 
    pass
