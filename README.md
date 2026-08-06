For 楓之谷:經典版
---
## 小工具
1. `open auto_pick_up in Admit.bat`: 遊戲內自動撿拾工具，`F2`啟動/關係，`F3`退出。
2. `get_nametag.py`:擷取角色名稱圖片。
3. `CaptureScreen.py`:顯示座標系與截圖功能，方便測算像素。

### Image Logging

<img src="./assects/log_img.gif" width="604">

### 可以多怪匹配了，但顏色分辨不出來，因為使用灰階圖，下次嘗試用HSV試試效果；左右img翻轉部分代碼要整理；繪圖函式解偶拉出來，不要跟資料處理或匹配處理的模塊混在一起

---

## Tech Stack 

* **視窗抓取 (Win32 API + Pillow)**：
  * 使用 `win32gui` 取得遊戲視窗句柄 (`hwnd`) 與視窗邊界 (`GetClientRect` / `ClientToScreen`)。
  * 結合 `ImageGrab` (mss/Pillow) 進行高效能的視窗截圖，並轉為 OpenCV 的 BGR 陣列格式。
* **樣板匹配 (Template Matching)**：
  * **灰階與二值化預處理**：將畫面與模板轉為灰階，利用 `cv2.threshold` (OTSU 演算法) 消除雜訊、突顯輪廓。
  * **切片匹配 (Splitted Template Matching)**：
    * 將模板圖片進行寬度切片（`split_width`），分別與遊戲畫面進行比對。
    * 支援使用遮罩（Mask）過濾背景干擾。
  * **歸一化相關係數 / 平方差匹配 (`cv2.matchTemplate`)**：
    * 利用 `cv2.minMaxLoc` 尋找最佳匹配點（最高相似度或最小差異值），並設定閾值（Threshold）過濾錯誤結果。
* **硬體操控**
    * 使用 `interception`，對機械層下操作指令
    * 使用`keyboard`，實現綁定熟鍵