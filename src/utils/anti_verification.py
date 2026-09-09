import cv2
import numpy as np
import time
'''
目標: 解決遊戲檢測

方向: 光流法 取得初始白色目標 -> 卡爾曼綠波做動態座標修正

'''
# 參數設定

feature_params = dict(
    maxCorners=100,
    qualityLevel=0.3,
    minDistance=7,
    blockSize=7
)

lk_params = dict(
    winSize=(15, 15),
    maxLevel=1,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
)

# 白色的 HSV 範圍
lower_white = np.array([0, 0, 200], dtype=np.uint8)
upper_white = np.array([180, 30, 255], dtype=np.uint8)

# 初始化卡爾曼濾波器
kf = cv2.KalmanFilter(4, 2)
kf.measurementMatrix = np.array([[1,0,0,0],[0,1,0,0]], np.float32)
kf.transitionMatrix = np.array([[1,0,1,0],[0,1,0,1],[0,0,1,0],[0,0,0,1]], np.float32)



# 1. 讀取測試影片& 初始化
video_path = "assets/videos/test_lie_detector.mp4"
cap = cv2.VideoCapture(video_path)
is_tracking = False
start_time = time.time()
prev_gray = None

if not cap.isOpened():
    print(f"無法開啟影片：{video_path}，請檢查檔案路徑。")
    exit()




# 2. 轉灰階
ret, frame = cap.read()
if not ret:
    print("無法讀取影片的第一幀畫面。")
    exit()



print(" 'q' 鍵可關閉視窗。")

# 開啟影片迴圈
while cap.isOpened():
    ret, frame = cap.read()
    # 切割取ROI
    h, w, _ = frame.shape
    ymin, ymax = int(h * 0.22), int(h * 0.70)
    xmin, xmax = int(w * 0.05), int(w * 0.95)
    roi_frame = frame[ymin:ymax, xmin:xmax]

    if not ret:
        print("影片播放完畢。")
        break
        
    curr_gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)

    # 計算時間
    elapsed_time = time.time() - start_time

    if elapsed_time < 3:
        '''偵測前幾秒先用流光抓取白色目標'''


        # 使用 HSV 閥值找到白色區域 mask
        hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_white, upper_white)
        # 在 mask 範圍內尋找特徵點
        curr_pts = cv2.goodFeaturesToTrack(curr_gray, mask=mask, **feature_params)

            
        if curr_pts is not None:
            print("偵測前幾秒先用流光抓取白色目標", len(curr_pts))
            prev_pts = curr_pts
            is_tracking = True
        # 【加入畫圖邏輯】如果在初始化階段有抓到點，直接把點畫在畫面上
        if curr_pts is not None:
            for pt in curr_pts:
                a, b = map(int, pt.ravel())
                # 記得加上 xmin 與 ymin，讓點對準全螢幕的 frame
                cv2.circle(frame, (a + xmin, b + ymin), 4, (0, 0, 255), -1)

    elif is_tracking and prev_gray is not None and prev_pts is not None:
        print("轉入動態預測")

        prev_pts = np.array(prev_pts, dtype=np.float32) # 統一轉為 32位浮點數陣列

        # 目標開始融合，依靠光流 + 卡爾曼預測
        curr_pts, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, prev_pts, None, **lk_params)

        if curr_pts is not None and len(curr_pts[status==1]) > 0:

            # 取得成功追蹤的點
            good_new = curr_pts[status==1]

            # 計算中心點，並強制轉為 OpenCV 卡爾曼波器 要求的 (2, 1) 直行矩陣 (float32)
            measured_mean = np.mean(good_new, axis=0)
            measured_center = np.array([[np.float32(measured_mean[0])], [np.float32(measured_mean[1])]], dtype=np.float32)
            
            # 丟給卡爾曼濾波器進行修正與預測
            prediction = kf.predict()
            estimated = kf.correct(measured_center)
            
            #  把 (2, 1) 矩陣攤平成一維陣列
            est_flat = estimated.flatten()
            target_x, target_y = int(est_flat[0]), int(est_flat[1])
            
            # 把矩陣攤平，把數字拿出來
            est_flat = estimated.flatten()
            target_x, target_y = int(est_flat[0]), int(est_flat[1])
            print (f"卡爾曼預測座標: ({target_x}, {target_y})")

            # --- 階段 3: 滑鼠移動 ---
            # 為了避免頻繁發送指令，可以設定一個最小移動距離門檻
            # pyautogui.moveTo(target_x, target_y, duration=0.01) 
            
            # 視覺化除錯用
            cv2.circle(roi_frame, (target_x, target_y), 10, (255, 0, 0), -1) # 藍色點是卡爾曼預測點
            prev_pts = good_new.reshape(-1, 1, 2)


    else:
        print("目標完全融合，光流跟丟，依靠卡爾曼慣性預測...")
        # 如果光流完全失效，讓卡爾曼濾波器單獨跑幾幀，看能不能「盲跟」到重新出現
        prediction = kf.predict()
        target_x, target_y = int(prediction[0]), int(prediction[1])
        # 可以選擇是否繼續移動滑鼠 pyautogui.moveTo(...)


    # 顯示即時追蹤畫面
    cv2.imshow("Lie Detector Tracking Test", roi_frame)

    # 更新上一幀
    prev_gray = curr_gray.copy()

    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()