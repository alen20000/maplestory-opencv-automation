import yaml
import os
import cv2
import numpy as np
from config.config_loader import config 

'''
mob template resource :https://maplestory.wiki/GMS/65/mob/100101

'''

class MobDetector:
    def __init__(self):
        #Config
        self.min_threshold = config.get("image_processing.min_threshold")
        self.mobs_in_map =  config.get("map.test_map")
        #放匹配模板字典
        self.mobs_templates: dict[str, np.ndarray] = {}

    def _load_mob_templates(self):
        '''
        從路徑資料夾讀取匹配怪物模板後存入字典
        key:mob ID ;value:img
        '''
        if not os.path.exists(self.mobs_in_map):
            return

        #遍歷載入怪物模板
        for mobs in os.listdir(self.mobs_in_map):
            if mobs.lower().endswith("png"):
                img_path = os.path.join(self.mobs_in_map, mobs)
                mob_name = os.path.splitext(mobs)[0]
                #先測試灰階，以後要高思或二值化，也在這
                mob_img = cv2.imread(img_path,cv2.IMREAD_GRAYSCALE)
                if mob_img is not None:
                    self.mobs_templates[mob_name] = mob_img

    def run(self):
        self._load_mob_templates()

    def searching_mob(self,crop_frame_gray):
        '''
        接收ROI範圍畫面與範圍座標
        回傳怪物座標
        '''
        #
        #不想寫在初始化，也不能寫在gamebot，會循環加載，只能寫在這
        if not self.mobs_templates:
            self._load_mob_templates()

        
        all_mobs_locs = []
        #輪尋查怪

        for mob_name, img in self.mobs_templates.items():
            
            # 1.原圖樣版
            matches = cv2.matchTemplate(crop_frame_gray, img, cv2.TM_CCOEFF_NORMED)
            loc = np.where(matches >= self.min_threshold)
            # 這裡是做矩陣翻轉，來得到正確的x,y   
            loc_normal = list(zip(loc[1], loc[0]))

            # 樣板左右翻轉， 這原理只是做矩陣變換，不太會消耗很多運算
            flipped_img = cv2.flip(img, 1)
            matches_flipped = cv2.matchTemplate(crop_frame_gray, flipped_img, cv2.TM_CCOEFF_NORMED)
            loc_f = np.where(matches_flipped >= self.min_threshold)
            loc_flipped = list(zip(loc_f[1], loc_f[0]))

            # 把正常方向與翻轉方向找到的座標全部合併在一起
            combined_locs = loc_normal + loc_flipped

            # 如果合併後有任何座標，就塞進回傳清單裡
            if combined_locs:
                all_mobs_locs.append((mob_name, combined_locs))

        return all_mobs_locs





if __name__ == "__main__":
    run = MobDetector()
    run.run()



def test_print_dict(self):

    for name,img in self.mobs_templates.items():
        # print(f"key:{name},value:{img}")

        if img is None:
            print(f"{name,} 的資料是 None空的")
            continue
        else:
            cv2.imshow(name, img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()