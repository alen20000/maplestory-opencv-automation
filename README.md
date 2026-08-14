## For 楓之谷:經典版
---
## 小工具
| 檔案名稱 | 核心用途 | 目前狀態 | 備註 |
| :--- | :--- | :---: | :--- |
| `auto_pick_up.bat` | 自動撿拾腳本 | V 正常 | 另外寫的自動拾取腳本 |
| `Run_GetNametag.bat` | 擷取人物名牌 | V 正常 | 要先用這個抓自己人物名牌，才可以更準的定位。該起後找到乾淨的背景按下"Z"鍵，提取人物名牌。 |
| `CaptureScreen.py` | 顯示座標與截圖 | V 正常 | 測算像素用 |




### Img Logging
<p align="center">
  <img src="./assets/log_img.gif" width="600">
</p>
<p align="center">
  <img src="./assets/log_img_2.gif" width="600">
</p>



---

## Dev Notes 
>[LEARNING] 圖像匹配:為了提高精度，有測試切片、遮罩還有很多方法，但會貌似都很容易加大運算量，精度、效能也沒明顯提升，最後用線程池去做反而更簡單；測試時沒有添加過濾算法，locs數量會異常多，而劃出BBox可能因運算量太大而CTD

>[WIP]導入撿拾功能，但還沒優化

>[DONE]解決地圖邊界判定問題:ROI未偵測到人物後，會開始計數，達到設定閥值後，觸發隨機走路，讓人物偵測捕獲；若Minimap tracking有完成，這部分應該要拿掉重寫

>[TODO]尋怪邏輯:嘗試以minimap定位人物座標，搭配小地圖上色去做出更細節動作，來替代目前的行為邏輯

>[ISSUE] 健康監測:畫面不匹配，導致抓不到像素，原本的防呆功能好像沒有用處，尤其是畫面切換時，會一直觸發喝水行為

---

## Tech Stack

* **視窗抓取 (Win32 API + Pillow)**：
  * 使用 `win32gui` 取得遊戲視窗句柄 (`hwnd`) 與視窗邊界 (`GetClientRect` / `ClientToScreen`)。
  * 結合 `ImageGrab` (mss/Pillow) 進行高效能的視窗截圖，並轉為 OpenCV 的 BGR 陣列格式。
* **樣板匹配 (Template Matching)**：
  * **灰階與二值化預處理**：將畫面與模板轉為灰階，利用 `cv2.threshold` (OTSU 演算法) 消除雜訊、突顯輪廓。
  * **切片匹配 (Splitted Template Matching)**：
    * 將模板圖片進行寬度切片（`split_width`），分別與遊戲畫面進行比對，。
    * 支援使用遮罩（Mask）過濾背景干擾。
  * **歸一化相關係數 / 平方差匹配 (`cv2.matchTemplate`)**：
    * 選用 `cv2.minMaxLoc` 尋找最佳匹配點（最高相似度或最小差異值），並設定閾值（Threshold）過濾錯誤結果。
  * **NMS（Non-Maximum Suppression**
    * 利用NMS清除重複匹配，減輕`draw_dectection_box`繪圖運算量，打怪功能前的重要步驟
* **硬體操控**
    * 選用 `interception`，硬體層下達底層指令
    * 選用`keyboard`，實現綁定熟鍵
* **線程池**
    * 使用`concurrent.futures`內的`ThreadPoolExecutor`來分擔怪物模板匹配的工作
##

### Current Features (WIP)

* 自動尋怪
  * 螢幕視窗為中心的尋怪
* 自動打怪
* 自動撿東西
  * 簡易版，而且還要外掛使用...
* 自動喝水
  * 只有HP

### Setting

* 藥水設定
  * 路徑`./config/config_default`
<p align="center">
  <img src="./assets/setting-1.png" width="300">
</p>

* 地圖設定
  * 路徑`./config/config_data`
  * `quickly_choice_map`的值，設下列`map`的`value`
  * `map`下方的鍵值可以製作對應地圖的怪物配對模板

<p align="center">
  <img src="./assets/setting-2.png" width="300">
</p>