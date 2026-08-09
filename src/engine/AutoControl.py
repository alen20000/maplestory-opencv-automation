import time
import logging
from config.config_loader import config
from src.utils.boxes import BBox
from typing import Optional

'''
行為邏輯，橋接GameBot 與 發布命令給 KeyBoardController
'''
class AutoControl:
    def __init__(self, game_bot_instance):

        #parameters
        self.bot =game_bot_instance
        self.player_attack_range = config.get("auto_control.attack_range")


    def decide_operation(self) -> tuple[Optional[str], Optional[dict]]:
        '''
        負責:角色邏輯判斷
        回傳:行為、目標
        '''

        '''角色健康狀態'''
        
        level , heal_key = self._health_status_check()
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}

        '''角色攻擊/閒置/移動行為'''
        if self.bot.player_center_loc is None:
            return None, None

        mobs_result = getattr(self.bot, 'current_mobs_result', None)

        if not mobs_result:
            return None, None

        px, py = self.bot.player_center_loc

        if self.bot.roi_BBOX is None:
            return None, None

        best_target = None
        min_distance = float('inf')

        for mob_name, mob_detail in mobs_result:
            for detailed in mob_detail:
                #player loc is global location
                mx = detailed["top_left"][0] + self.bot.roi_BBOX.x1

                raw_distance = mx - px # 怪物 mx - 角色 px 

                distance = abs(px - mx)

                if distance < min_distance:
                    min_distance = distance

                    if raw_distance > 0:
                        direction = "RIGHT"  # 怪物在右邊
                    else:
                        direction = "LEFT"   # 怪物在左邊

                    best_target = {"name": mob_name, "distance": distance, "direction": direction}

        if best_target and best_target['distance'] <= self.player_attack_range:
            # print(f"目標 [{best_target['name']}] 在攻擊範圍內 距離: {best_target['distance']} 方向: {best_target['direction']}")
            return "ATTACK" , best_target
        
        return "APPROACH" , best_target

    def _health_status_check(self): 

        '''
        血量情況判斷與行動分流
        回傳: 血量分級、對應按鍵
        '''
        hp = self.bot.player_hp
        #防呆
        if hp is None:
            return None, None

        #按鍵預設，與GameBot同步
        health_setting = self.bot.health_setting

        if not health_setting:
            return None, None


        #結構: {"light":    {"key": "delete", "value": 80},..,}
        sorted_levels = sorted(
            health_setting.items(),
            key=lambda item: item[1]["value"]
        )

        #主要判斷
        for level, setting in sorted_levels:
            if hp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                return level, key
            
        return None, None

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