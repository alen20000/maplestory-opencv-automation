from config.config_loader import config
import cv2
import logging
import numpy as np
'''
人物黃點: RGB 255,255,136  HSV 是： [ 30 119 255]
人物黃點: RGB 255,255,0  HSV 是： [ 30 255 255]

learning: 想法錯了 應該不用全圖匹配後取roi範圍偵測 ； 應該直接鎖死小地圖的top left  好像每張小地圖的 topl left point 都是一個位置
設 小地圖定位點 螢幕座標為 x:15 y:110 窗口座標為 15-9 , 110-38 = 6, 72
然後 模板切 x y  範圍就是 15+x  , 110 + y
'''
minimap_detect_range = (0,20,187,184)

class MinimapDetector:
    def __init__(self):

        self.minimap_name = None
        self.minimap_template = None
        self.current_frame_bgr =None
        self.template_h,self.template_w = None,None

        self.minimap_tl = (6,72)
        self.minimap_br = None
        self.crop_frame_bgr = None

        #load config
        self._load_minimap_config()

    def _load_minimap_config(self):
            
        try:
            #load map img
            map_name = config.get("quickly_choice_map")
            map = config.get(f"mini_map.{map_name}")

            self.minimap_template = cv2.imread(map,cv2.IMREAD_COLOR)
            
        except Exception as e:
            logging.error(f"載入地圖失敗{e}")

    def _get_minimap_br(self):
        '''
        得到小地圖範圍的右下座標
        '''
        self.template_h, self.template_w = self.minimap_template.shape[:2]
        x2 = self.minimap_tl[0] + self.template_w
        y2 = self.minimap_tl[1] + self.template_h
        self.minimap_br = (x2,y2)

    def _crop_minimap(self):
        '''
        聚焦偵測範圍
        '''
        self.crop_frame_bgr = self.current_frame_bgr[self.minimap_tl[0]:self.minimap_br[0],self.minimap_tl[1]:self.minimap_br[1]]

    def run(self,frame_bgr):
        self.current_frame_bgr = frame_bgr

        if self.template_h is None and self.template_w is None:
            self._get_minimap_br()
            self._crop_minimap()

        cv2.rectangle(self.current_frame_bgr,(self.minimap_tl),(self.minimap_br),(100,100,100),3)



    def _detect_player_loc(self,frame_bgr):
        '''
        在迷你地圖偵測範圍內找人物座標，
        '''
        #防呆
        if self.minimap_br is None:
            return None

        frame_hsv = cv2.cvtColor(frame_bgr,cv2.COLOR_BGR2HSV)
        lower_player_color = np.array([20, 100, 180])
        upper_player_color = np.array([40, 255, 255])

        mask = cv2.inRange(frame_hsv,lower_player_color,upper_player_color)
        #抓住符合顏色。 這邊還有 cv2.findContours搭配cv2.RETR_EXTERNAL與cv2.CHAIN_APPROX_SIMPLE 抓輪廓的寫法，可以嘗試(可選)
        pts = cv2.findNonZero(mask)

        if  pts is not None and len(pts) > 2:

            #第一維是 點(矩陣列)，第二維是(x,y)
            c_x = int(np.mean(pts[:,0]))
            c_y = int(np.mean(pts[:,1]))

            #這邊應該是換成遊戲內的座標，他是從roi區域座標升上來的，而不是螢幕絕對座標，嵌套兩個座標系，要還原絕對座標還要在加遊戲視窗的top_left座標

            game_player_x = c_x + self.map_tl[0]
            game_player_y = c_y + self.map_tl[1]
            return (game_player_x,game_player_y)


    def _draw_minimap(self):
        '''
        測試用，顯示偵測範圍
        '''
        x1,y1,x2,y2 = minimap_detect_range
        cv2.rectangle(self.current_frame_bgr,(x1,y1),(x2,y2),(100,100,100),3)
        cv2.imshow("TEST", self.current_frame_bgr)
        cv2.waitKey(0)

    def _draw_match_map(self,loc):
        '''
        測試用
        '''
        x1,y1 = loc[0],loc[1]
        x2,y2 = x1+self.minimap_template.shape[1],y1+self.minimap_template.shape[0]
        cv2.rectangle(self.current_frame_bgr,(x1,y1),(x2,y2),(0,0,255),3)
