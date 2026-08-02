For 楓之谷:經典版
---

## 進度

1. **遊戲視窗自動對齊**：透過 Win32 API 抓取指定遊戲視窗，自動將其置頂並取得座標範圍。
2. **角色動態名牌擷取 (`GetCharImg.py`)**：
   * 透過基準圖（example）配合遮罩搜尋角色。
   * 畫面即時預覽，按下 **`z`** 鍵可直接截取當前角色名牌並存檔，按下 **`q`** 鍵退出。
3. **即時畫面追蹤與定位 (`GameBot.py`)**：
   * 全螢幕迴圈掃描遊戲畫面。
   * 即時計算角色中心點座標，並繪製 ROI（興趣區塊）與偵測框。
   * 內建錯誤日誌記錄（`logs/game_debug.log`）。

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