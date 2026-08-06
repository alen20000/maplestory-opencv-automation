import cv2
import numpy as np
import win32gui
import win32con
from src.utils.boxes import BBox
from pathlib  import Path

import yaml
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




def bring_to_front_and_center_origin(hwnd:int):
    '''
    整理窗口位置
    將視窗帶到最前、初始化位置
    '''
    try:
        # 如果視窗被最小化了，先將它恢復正常大小
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # 將視窗帶到最前台
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"置頂視窗失敗: {e}")

    win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)


def cent_coord(global_loc:tuple[int,int],template_size:tuple[int,int]) -> tuple[int,int]: 
    '''
    計算location中心點
    輸入: 目標全局座標(左上基準點)x,y , 模板圖片長寬[x,y]
    這裡輸入是 (x,y) ；輸出是 (x,y)
    '''
    center_w = int(global_loc[0]+(template_size[0]//2))
    center_h = int(global_loc[1]+(template_size[1]//2))
    return center_w,center_h


def get_bbox_from_center(cen_loc:tuple[int,int],template_size:tuple[int,int]) -> tuple[tuple[int,int],tuple[int,int]]:
    '''
    計算bbox區塊
    輸入:中心座標的 [x,y], 模板圖片長寬[x,y];    cen_loc[0] = x cen_loc[1] = y ; template_size[0] = x template_size[1] = y
    輸出:bbox座標 turple[(x1,y1),(x2,y2)]

    '''
    #Unpack
    cx, cy = cen_loc
    t_w, t_h = template_size
    #計算bbox
    x1 = cx - t_w // 2
    y1 = cy - t_h // 2
    x2 = cx + t_w // 2
    y2 = cy + t_h // 2

    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)

def convert_img2xy(img:np.ndarray)->tuple[int,int] : 
    #把img的array陣列 (y,x) 轉成 (x,y)
    y,x = img.shape[:2]
    return (x,y)


def draw_dectection_box(frame,left_top,right_bottom,label="Target",color=(0,255,0),thickness=2,
                        top_padding=0, bottom_padding=0, left_padding=0, right_padding=0):
    '''繪製ROI區塊，參數:frame,左上角座標,右下角座標,標籤名稱,顏色,線條粗細,擴大值'''

    #Box變動算法
    left_top = (left_top[0] - left_padding, left_top[1] - top_padding)
    right_bottom = (right_bottom[0] + right_padding, right_bottom[1] + bottom_padding)

    cv2.rectangle(frame, left_top, right_bottom, color, thickness)

    cv2.putText(
        frame, 
        label, 
        (left_top[0], left_top[1] - 10), # 文字位置在框框左上方稍微偏上一點
        cv2.FONT_HERSHEY_SIMPLEX, 
        0.5, 
        color, 
        2
    )
    return frame


def BGR2Binary(img: np.ndarray) -> np.ndarray:
    '''BGR 色彩影像轉換為灰階，再以灰階做二值化'''

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return binary
