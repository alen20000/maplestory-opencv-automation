from config.config_loader import config
import cv2
import logging
'''
人物黃點: 88FFFF 255,255,240

'''
minima_detect_range = (9,38,187,184)

class MinimapDetector:
    def __init__(self):

        self.minimap_name = None
        self.minimape = None

    def _load_minimap_config(self):
            
        try:
            Map_Name = config.get("quickly_choice_map")
            self.minimap_name = config["minimap"]["name"]
            self.minimape = config.get(f"mini_map.{Map_Name}")
        except Exception as e:
            logging.error(f"載入地圖失敗{e}")

    def analysis_minimap(self, full_frame):

        pass


    def get_minimap(self, full_frame):
        """
        先用原圖去補獲真實座標，再把偵測範圍縮到固定區域
        """
        result = cv2.TemplateMatchModes(self.minimape) 