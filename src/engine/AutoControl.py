import time
import logging
from config.config_loader import config
from src.utils.boxes import BBox
from typing import Optional
from src.engine.game_state import GameState
import time
import random
from pathlib import Path
import yaml
'''
改為，接收封包(GameState)，以封包數據進行邏輯運算與決策，
輸出對應行為指令與目標資訊給控制模組
'''
class AutoControl:
    def __init__(self):
        # Data Containers & States
        self.health_setting = {}
        self.search_direction = "RIGHT"
        self.search_switch_time = time.time()
        self.recored_data = []
        self.platforms = []
        self.current_platform = None #<-- 當前所在平台
        self.mini_player_loc = None #<-- 當前人物位置(小地圖)
        # Loadding Config
        self._load_health_config()
        self._load_map_data()
        # Parameters
        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range")

        # Search Config & Constants
        self.SEARCH_SWITCH_INTERVAL = 3.0 # <-- 搜尋間隔
        self.search_switch_jitter = random.uniform(-1.5, 2.0)  # <-- 搜尋間隔誤差，模擬隨機性


        #Toggle/
        self.enable_searching_mob = config.get("auto_control_config.search_interval", False) # <-- 搜尋怪物功能

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
    def _load_map_data(self):
        try:
            map_name = config.get("quickly_choice_map")
            self.mini_map = Path(config.get(f"mini_map.{map_name}"))
            folder_path = self.mini_map.parent
            yaml_path = folder_path / f"{map_name}.yaml"
            if yaml_path.exists():
                with open(yaml_path, "r") as f:
                    self.recored_data = yaml.safe_load(f)
                # 找出平台
                self.platforms = self._find_platform()

        except Exception as e:
            logging.error(f"載入地圖失敗{e}")


    def select_operation(self,state: GameState) -> tuple[Optional[str], Optional[dict]]:
        '''
        Args:
            state (GameState): 包含當前角色位置、血量、ROI 範圍及怪物清單的資料容器。
        '''

        # 角色健康狀態

        # level , heal_key = self._health_status_check(state.player_hp)
        # if level is not None:
        #     return f"HEAL_{level.upper()}", {"key": heal_key}

        # 平台判斷
        if state.mini_player_loc:
            try:
                self.mini_player_loc = state.mini_player_loc
                self.current_platform = self.check_current_platform()
            except:
                pass
            
        if self.current_platform:
            result = self._fk_that_mob(state)
            print(f"result: {result}")
            return result
        
        return None,None
    


    def _find_platform(self):
        """
        找出平台
        用滑動窗口直接從list內抓出平台，加上偏移量，製作出平台範圍
        """

        platforms = []
        i= 0
        while i < len(self.recored_data)-1:
            current = self.recored_data[i]
            next_item = self.recored_data[i + 1]

            if current["action"] =='walk' and next_item["action"] == 'walk':

                offset = 5
                top = current["loc"][1] - offset
                bottom = current["loc"][1] + offset

                left = min(current["loc"][0], next_item["loc"][0])
                right = max(current["loc"][0], next_item["loc"][0])

                platforms.append({"t_l":(top,left),"b_r":(bottom,right)})
                i += 2
            else:
                i += 1 

        return platforms

    def check_current_platform(self):
        """
        根據玩家目前的座標，判斷人在哪一個平台內

        """
        if not self.mini_player_loc or not self.platforms:
            return None

        px, py = self.mini_player_loc 

        for index, plat in enumerate(self.platforms):
            top, left = plat["t_l"]     
            bottom, right = plat["b_r"] 

            if left <= px <= right and top <= py <= bottom:
                # 加一個1，不然0的化再判斷可能為None
                index += 1
                return index  

        return None



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

    def _fk_that_mob(self,state):
        
        if not state.player_center_loc:
            return None, None
        px, _ = state.player_center_loc

        # 計算距離/方向/目標/回傳 states module 結果
        best_target = None
        min_distance = float('inf')
        print(state.mobs)
        #從無限遠開始判斷
        for mob , mob_detail in state.mobs or []:
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

        return None, None