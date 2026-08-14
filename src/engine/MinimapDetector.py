from config.config_loader import config
import cv2
import logging
'''
人物黃點: 88FFFF 255,255,240

'''
minimap_detect_range = (5,20,187,184)

class MinimapDetector:
    def __init__(self):

        self.minimap_name = None
        self.minimap_template = None
        self.current_frame_bgr =None
        self.map_tl = None
        self.map_br = None
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

    def run(self,frame_bgr):
        self.current_frame_bgr = frame_bgr
        result = self._match_minimap(frame_bgr)
        # self._draw_minimap()
        # self._draw_match_map(result)
        pass


    def _match_minimap(self, frame):
        """
        先用原圖去補獲真實座標，再把偵測範圍縮到固定區域
        """

        # print("--- DEBUG INFO ---")
        # print("frame type:", type(frame), "shape:", getattr(frame, 'shape', None), "dtype:", getattr(frame, 'dtype', None))
        # print("template type:", type(self.minimap_template), "shape:", getattr(self.minimap_template, 'shape', None), "dtype:", getattr(self.minimap_template, 'dtype', None))
        # print("--------------------")


        result =  cv2.matchTemplate(frame,self.minimap_template,cv2.TM_CCOEFF_NORMED) 
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        print(f"置信度:{max_val}；位置:{max_loc}")
        if max_val > 0.8:
            x1,y1 = max_loc[0],max_loc[1]
            x2,y2 = x1+self.minimap_template.shape[1],y1+self.minimap_template.shape[0]
            #取地圖ROI範圍
            self.map_tl = (x1,y1)
            self.map_br = (x2,y2)


        return max_loc

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
