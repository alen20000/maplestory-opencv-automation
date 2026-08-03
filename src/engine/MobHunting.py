import yaml
import os
import cv2


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
        self.mobs_templates = {}

    def _load_mob_templates(self):
        '''從路徑資料夾讀取匹配怪物模板後存入字典'''
        if not os.path.exists(self.folder_path):
            return
        for mobs in os.listdir(self.folder_path):
            if mobs.lower().endswith("png"):
                img_path = os.path.join(self.folder_path, mobs)
                mob_name = os.path.splitext(mobs)[0]

                mob_img = cv2.imread(img_path)
                if mob_img is not None:
                    self.mobs_templates[mob_name] = mob_img
    def run(self):
        self._load_mob_templates()

    def searching_mob(self,crop_frame,left_top: tuple[int, int],right_bottom: tuple[int, int]):
        '''
        接收ROI範圍畫面與範圍座標
        '''
        #


        matches = cv2.matchTemplate(frame_gray,self.my_character_template_gray,cv2.TM_CCOEFF_NORMED)

        pass


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

if __name__ == "__main__":
    run = MobDetector()
    run.run()