## For 楓之谷:經典版
---
## 小工具
| 檔案名稱 | 核心用途 | 目前狀態 | 備註 |
| :--- | :--- | :---: | :--- |
| `auto_pick_up.bat` | 自動撿拾腳本 | V 正常 | 另外寫的自動拾取腳本 |
| `get_nametag.py` | 擷取名稱與座標 | V 正常 | 半自動提取角色名牌，用於角色定位 |
| `CaptureScreen.py` | 顯示座標與截圖 | V 正常 | 測算像素用 |

### Img Logging

<img src="./assets/log_img.gif" width="600">

<img src="./assets/log_img_2.gif" width="600">

目前邊界判定有問題，到地圖邊ROI範圍畫不出來，所以會罰站；目前加上自動撿拾腳本，能實現一個基礎的自動打怪循環

---

## Dev Notes & TODO
>[NOTE] 尋怪機制優化:研究了切片、MASK，但會加大運算量，以及NMS沒寫好的話，locs數量會非常多，若要劃出BBox更會造成運算量太大而CTD

>[TODO]把撿拾功能寫入專案

>[NOTE]解決地圖邊界判定問題；用視窗擷取視窗中心回正；或是測算小地圖座標在還原，要再思考

>[NOTE]尋怪邏輯:要再想想怎麼架構與行為邏輯

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
  * ** NMS（Non-Maximum Suppression）**
    * 利用NMS清除重複匹配，減輕`draw_dectection_box`繪圖運算量，打怪功能前的重要步驟
* **硬體操控**
    * 選用 `interception`，硬體層下達底層指令
    * 選用`keyboard`，實現綁定熟鍵

##