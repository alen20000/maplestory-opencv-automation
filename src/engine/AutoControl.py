import time
import logging
from config.config_loader import config
from src.utils.boxes import BBox
from typing import Optional
from src.engine.game_state import GameState
import time
import random
'''
改為，接收封包(GameState)，以封包數據進行邏輯運算與決策，
輸出對應行為指令與目標資訊給控制模組
'''
class AutoControl:
    def __init__(self):

        #parameters

        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range")
        self.health_setting = {}
        self._load_health_config()
        self.search_direction = "RIGHT"
        self.search_switch_time = time.time()
        self.SEARCH_SWITCH_INTERVAL = 3.0 # <-- 搜尋間隔
        self.search_switch_jitter = random.uniform(-1.5, 2.0)  # <-- 搜尋間隔誤差，模擬隨機性

    def _load_health_config(self):

        '''
        喝水設定載入
        '''

        raw = config.get("player_setting.health_setting") or {}

        for level, setting in raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":
                key = None

            self.health_setting[level] = {
                "value" : value,
                "key" : key,
            }


    def decide_operation(self,state: GameState) -> tuple[Optional[str], Optional[dict]]:
        '''
        Args:
            state (GameState): 包含當前角色位置、血量、ROI 範圍及怪物清單的資料容器。
        '''

        # 角色健康狀態

        level , heal_key = self._health_status_check(state.player_hp)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}

        # 檢查點
        if state.player_center_loc is None: # <-- 決策點"檢查玩家座標時"
            return None, None
        if state.roi_BBOX is None: # <- 決策點"檢查沒有ROI時"

            return self._search_sweep()

        if not state.mobs: # <- 決策點"檢查怪物時"

            
            return self._search_sweep()

        px, _ = state.player_center_loc

        if state.roi_BBOX is None:
            return None, None

        # 計算距離/方向/目標/回傳 states module 結果
        best_target = None
        min_distance = float('inf')
        #從無限遠開始判斷
        for mob , mob_detail in state.mobs:
            for detailed in mob_detail:
                #計算怪物的絕對座標，
                mx = detailed["top_left"][0] + state.roi_BBOX.x1

                #絕對值求與玩家間的距離
                distance = abs(px - mx)
                if distance < min_distance:
                    min_distance = distance
                    #左右判斷
                    direction = "RIGHT" if px < mx else "LEFT"
                    best_target = {"name": mob, "distance": distance, "direction": direction}
        #攻擊距離判斷在這行
        if best_target and best_target['distance'] <= self.player_attack_range:
            print(f"目標 [{best_target['name']}] 在攻擊範圍內 距離: {best_target['distance']} 方向: {best_target['direction']}")
            return "ATTACK" , best_target

        return "APPROACH" , best_target

    def _health_status_check(self,player_hp): 

        '''
        血量情況判斷與行動分流
        回傳: 血量分級、對應按鍵
        '''

        if not (0 <= player_hp <= 100):
            logging.warning(f"血量取值異常: {player_hp} ")
            return None, None

        #防呆
        if player_hp is None:
            return None, None 

        #按鍵預設，與GameBot同步
        health_setting = self.health_setting

        if not health_setting:
            return None, None 


        #結構: {"light":    {"key": "delete", "value": 80},..,}
        sorted_levels = sorted(
            health_setting.items(),
            key=lambda item: item[1]["value"]
        )

        #主要判斷
        for level, setting in sorted_levels:
            if player_hp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                return level, key
            
        return None, None


    def _goto_center(self,state: GameState):

        '''
        搜尋策略:向中心運動
        
        '''
        frame = state.frame
        px, _ = state.player_center_loc
        _, x = frame.shape[:2]
        print(f"隨機移動到{x//2}")

        direction = "RIGHT" if px < x//2 else "LEFT"
        random_move = {
            "name": "RANDOM_MOVE",
            "distance": None,
            "direction": direction
            }

        return "APPROACH" , random_move
    
    def _to_alternating_side_move(self):

        '''
        搜尋策略:與上一方向反向運動
        
        '''

        if self.last_direction == "RIGHT":
            direction = "LEFT"
        elif self.last_direction == "LEFT":
            direction = "RIGHT"
        else:
            return None, None
        alternating_move = {
            "name": "alternating_side",
            "distance": None,
            "direction": direction
            }

        return "APPROACH" , alternating_move

    def _search_sweep(self):
        '''
        定時左右來回移動
        '''
        now = time.time()
        threshold = self.SEARCH_SWITCH_INTERVAL + self.search_switch_jitter

        if now - self.search_switch_time >= threshold:
            self.search_direction = "LEFT" if self.search_direction == "RIGHT" else "RIGHT"
            self.search_switch_time = now
            self.search_switch_jitter = random.uniform(-1.5, 2.0)  # 換方向時重新抽一次


        return "APPROACH", {
        "name": "SEARCH_SWEEP",
        "distance": None,
        "direction": self.search_direction
        }