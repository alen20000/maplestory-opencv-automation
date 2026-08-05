import yaml
import os
import cv2
import numpy as np
from src.utils.common import cent_coord,get_roi_box,draw_dectection_box
# --- 參數先放這以後記得移走 ---
MAX_THRESHOLD = 0.07
MIN_THRESHOLD = 0.6

'''
mob template resource :https://maplestory.wiki/GMS/65/mob/100101

'''
class MobDetector:
    def __init__(self):
        #config
        with open('config/config_data.yaml', "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.folder_path = self.config["map"]["test_map"]
        #放匹配模板字典
        self.mobs_templates: dict[str, np.ndarray] = {}



    def _load_mob_templates(self):
        '''
        從路徑資料夾讀取匹配怪物模板後存入字典
        key:mob ID ;value:img
        '''
        if not os.path.exists(self.folder_path):
            return

        #遍歷載入怪物模板
        for mobs in os.listdir(self.folder_path):
            if mobs.lower().endswith("png"):
                img_path = os.path.join(self.folder_path, mobs)
                mob_name = os.path.splitext(mobs)[0]
                #先測試灰階，以後要高思或二值化，也在這
                mob_img = cv2.imread(img_path,cv2.IMREAD_GRAYSCALE)
                if mob_img is not None:
                    self.mobs_templates[mob_name] = mob_img

    def run(self):
        self._load_mob_templates()

    def searching_mob(self,crop_frame_gray,ROI_left_top: tuple[int, int]):
        '''
        接收ROI範圍畫面與範圍座標
        '''
        #
        #不想寫在初始化，也不能寫在gamebot，會循環加載，只能寫在這
        if not self.mobs_templates:
            self._load_mob_templates()

        #輪尋查怪
        for _,img in self.mobs_templates.items():
            matches = cv2.matchTemplate(crop_frame_gray,img,cv2.TM_CCOEFF_NORMED)

            #np.where的回傳是許多個tuple[y,x]，要注意必須轉回來(x,y)
            loc = np.where(matches >= MIN_THRESHOLD)
            loc = list(zip(loc[1], loc[0]))

            if loc:

                for pt in loc:
                    x, y = pt

                    global_mob_loc = (x + ROI_left_top[0], y + ROI_left_top[1])

                    center_pt = cent_coord(global_mob_loc,img)

                    c_w,c_h = center_pt
                    mb_left_top,mb_right_bottom = get_roi_box(c_w,c_h,img)

                    return mb_left_top,mb_right_bottom
        # 所有模板都不匹配，才傳這個None
        return None





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