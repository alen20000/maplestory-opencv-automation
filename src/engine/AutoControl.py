import time
import logging
from config.config_loader import config
from src.utils.boxes import BBox
'''
行為邏輯，橋接GameBot 與 發布命令給 KeyBoardController
'''
class AutoControl:
    def __init__(self, game_bot_instance):

        #parameters
        self.bot =game_bot_instance
        self.player_attack_range = config.get("auto_control.attack_range")


    def decide_operation(self):
        '''
        負責座標計算，下達對應命令
        '''

        if self.bot.player_center_loc is None:
            return

        mobs_result = getattr(self.bot, 'current_mobs_result', None)

        if not mobs_result:
            return

        px, py = self.bot.player_center_loc

        best_target = None
        min_distance = float('inf')

        for mob_name, mob_detail in mobs_result:
            for detailed in mob_detail:
                #player loc is global location
                mx = detailed["top_left"][0] + self.bot.roi_BBOX.x1
                distance = abs(px - mx)
                if distance < min_distance:
                    min_distance = distance
                    best_target = {"name": mob_name, "distance": distance}

        if best_target and best_target['distance'] <= self.player_attack_range:
            print(f"目標 [{best_target['name']}] 在攻擊範圍內 (距離: {best_target['distance']})")
            return "ATTACK"
        
        return "APPROACH"





def random_move():
    '''
    預設，假使沒匹配到角色，隨機移動  
    '''

    pass

def attack_action():
    '''
    預設，接收相對座標小於[攻擊範圍]， 觸發攻擊行為
    '''
    pass