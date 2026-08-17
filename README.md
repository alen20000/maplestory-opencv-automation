## For 楓之谷:經典版
---
## 小工具
| 檔案名稱 | 核心用途 | 目前狀態 | 備註 |
| :--- | :--- | :---: | :--- |
| `auto_pick_up.bat` | 自動撿拾腳本 | V 正常 | 另外寫的自動拾取腳本，買不起寵物時用的 |
| `Run_GetNametag.bat` | 擷取人物名牌 | V 正常 | 要先用這個抓自己人物名牌，才可以更準的定位。該起後找到乾淨的背景按下"Z"鍵，提取人物名牌。 |
| `CaptureScreen.py` | 顯示座標與截圖 | V 正常 | 測算像素用 |
|`Operation_Logger.py`|錄製小地圖的行動點|V 正常 |沒有錄製行動點的話，程序沒辦法動，至少錄製一個打怪平台，才可以計算左右範圍，儲存路徑為 `mini_map\[對應地圖]`的目錄下，錄製前要在`config_data.yaml`設定`quickly_choice_map`|




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

>[DONE]解決地圖邊界判定問題:舊版本ROI未偵測到人物後，會開始計數，達到設定閥值後，觸發隨機走路，讓人物偵測捕獲；改以小地圖+座標平台化，做左右邊界判定

>[TODO ->DONE ] 尋怪邏輯:改以minimap獲得的人物座標做計算，效果比原本的隨機找怪邏輯更好，不用浪費大量運算做人物座標抓取了。

>[TODO ->DOING] 更精細的行為:目前能在平台上巡邏與打怪了；爬繩部分目前有點呆。

>[ISSUE] 健康監測:畫面不匹配，導致抓不到像素，原本的防呆功能好像沒有用處，尤其是畫面切換時，會一直觸發喝水行為

>[WIP] 卡死走回: 還沒弄
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
* 平台移動、垂直移動
  * 設立座標時，連續兩個`MOVE`為一個平台，連續兩個`ROPE`為垂直移動通道。 垂直移動還沒寫好，有點呆瓜

* 自動尋怪
  * 角色會以每個平台的左右邊界為極值做來回走動

* 自動打怪
  * 設立怪物偵測範圍，巡邏時出現在偵測範圍內的怪物會計算相對中心座標，取最近者發動攻擊

* 自動撿東西
  * 移動時會自動觸發撿拾

* 自動喝水
  * 只有HP (我的角色還喝不起藍水)

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

* Minimap 移動點設定
   * 路徑`
   ./img/mini_map/[對應的地圖]/[對應的地圖].ymal`
   * 要新增地圖模板到 `maplestory.wiki` 個網站抓
   * 目前只有兩種移動點類型，`MOVE` 與 `ROPE`，畫出水平平台與垂直移動的通道

<p align="center">
  <img src="./assets/setting-3.png" width="300">
  <br>
  <em>移動點設定範例</em>
</p>

