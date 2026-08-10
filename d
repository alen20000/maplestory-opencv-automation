[1mdiff --git a/config/config_data.yaml b/config/config_data.yaml[m
[1mindex 3ad171e..be3824e 100644[m
[1m--- a/config/config_data.yaml[m
[1m+++ b/config/config_data.yaml[m
[36m@@ -3,11 +3,12 @@[m [mgaming:[m
   template_matching_mode: 1[m
 [m
 # 選擇地圖[m
[31m-quickly_choice_map: Hunting_Ground_I[m
[32m+[m[32mquickly_choice_map: Victoria_Road[m
 [m
 # 設定的地圖路徑[m
 map:[m
   test_map: "img/monsters" [m
   Hunting_Ground_I: img/map/Hunting_Ground_I[m
   Pig_Beach: img/map/Pig_Beach[m
[32m+[m[32m  Victoria_Road: img/map/Victoria_Road[m
 [m
[1mdiff --git a/config/config_default.yaml b/config/config_default.yaml[m
[1mindex 75c377c..2d33ee3 100644[m
[1m--- a/config/config_default.yaml[m
[1m+++ b/config/config_default.yaml[m
[36m@@ -17,7 +17,7 @@[m [mplayer_setting:[m
       value: 20[m
   auto_control_config:[m
     #人物的攻擊範圍(像素)[m
[31m-    attack_range: 50[m
[32m+[m[32m    attack_range: 100[m
 image_processing:[m
   #TM_SQDIFF_NORMED（平方差正規化匹配）m/4[m
   max_threshold : 0.1[m
[36m@@ -26,9 +26,9 @@[m [mimage_processing:[m
 [m
 game_bot:[m
   #roi範圍的位移量 ，設定好能減少運算[m
[31m-  roi_x_offset_l_width: 300[m
[31m-  roi_x_offset_r_width: 300[m
[31m-  roi_y_offset_t_high: 100[m
[32m+[m[32m  roi_x_offset_l_width: 500[m
[32m+[m[32m  roi_x_offset_r_width: 500[m
[32m+[m[32m  roi_y_offset_t_high: 150[m
   roi_y_offset_b_high : 50[m
 [m
 health_detector:[m
[1mdiff --git a/src/engine/AutoControl.py b/src/engine/AutoControl.py[m
[1mindex 54cafb5..6f7fb4f 100644[m
[1m--- a/src/engine/AutoControl.py[m
[1m+++ b/src/engine/AutoControl.py[m
[36m@@ -22,7 +22,7 @@[m [mclass AutoControl:[m
         self.search_switch_time = time.time()[m
         self.SEARCH_SWITCH_INTERVAL = 3.0 # <-- 搜尋間隔[m
         self.search_switch_jitter = random.uniform(-1.5, 2.0)  # <-- 搜尋間隔誤差，模擬隨機性[m
[31m-[m
[32m+[m[32m        self.searching_mob = False[m
     def _load_health_config(self):[m
 [m
         '''[m
[36m@@ -59,8 +59,11 @@[m [mclass AutoControl:[m
         if state.player_center_loc is None: # <-- 決策點"檢查玩家座標時"[m
             return None, None[m
         if state.roi_BBOX is None: # <- 決策點"檢查沒有ROI時"[m
[31m-[m
[31m-            return self._search_sweep()[m
[32m+[m[32m            if self.searching_mob:[m
[32m+[m[32m                x, y = self._search_sweep()[m
[32m+[m[32m            else:[m[41m [m
[32m+[m[32m                x, y = None, None[m
[32m+[m[32m            return x, y[m
 [m
         if not state.mobs: # <- 決策點"檢查怪物時"[m
 [m
