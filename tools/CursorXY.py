"""
矩形座標選取工具
================
用途：依序點擊 4 個角落，自動算出矩形區域座標（給 mss 的 region 用）。

安裝：
    pip install pynput

使用方式：
1. 執行這支程式
2. 依照終端機提示，依序點擊：
   第1下 → 左上角
   第2下 → 右上角
   第3下 → 左下角
   第4下 → 右下角
3. 點完4下後，自動印出可以直接複製貼上的 region dict

注意：
- 用「點擊」來記錄位置，所以滑鼠移到定點後，隨便點一下左鍵即可
  （不用擔心點擊會誤觸原本畫面上的按鈕，因為這只是拿來取座標，
   你可以先點在空白處或不影響畫面的地方，重點是滑鼠移到正確位置再點）
- 若不小心點錯，直接按 Ctrl+C 中斷，重新執行一次即可
"""

from pynput import mouse

# 依序要記錄的4個角落名稱
LABELS = ["左上角", "右上角", "左下角", "右下角"]

clicks = []


def on_click(x, y, button, pressed):
    # 只在「按下」的瞬間記錄一次，放開時不記錄，避免重複
    if not pressed:
        return

    label = LABELS[len(clicks)]
    clicks.append((x, y))
    print(f"[已記錄] {label}: x={x}, y={y}")

    if len(clicks) < len(LABELS):
        next_label = LABELS[len(clicks)]
        print(f"請點擊「{next_label}」的位置...")
    else:
        # 4個點都收集完了，計算矩形
        calculate_region()
        return False  # 回傳 False 會停止監聽


def calculate_region():
    top_left, top_right, bottom_left, bottom_right = clicks

    # 用左上和右下取寬高（理論上跟右上/左下算出來會一致，這裡取最保險的組合）
    left = top_left[0]
    top = top_left[1]
    right = bottom_right[0]
    bottom = bottom_right[1]

    width = right - left
    height = bottom - top

    print("\n========== 計算結果 ==========")
    print(f"左上角: {top_left}")
    print(f"右上角: {top_right}")
    print(f"左下角: {bottom_left}")
    print(f"右下角: {bottom_right}")
    print("--------------------------------")
    print("可直接複製貼上使用：\n")
    print("monitor_region = {")
    print(f'    "top": {top},')
    print(f'    "left": {left},')
    print(f'    "width": {width},')
    print(f'    "height": {height},')
    print("}")
    print("================================")


def main():
    print("矩形座標選取工具")
    print("請依序點擊 4 個角落來記錄矩形範圍\n")
    print(f"請點擊「{LABELS[0]}」的位置...")

    with mouse.Listener(on_click=on_click) as listener:
        listener.join()


if __name__ == "__main__":
    main()