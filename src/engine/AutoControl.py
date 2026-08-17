import time
import logging
from config.config_loader import config
from typing import Optional
from src.engine.game_state import GameState
import time
import random
from pathlib import Path
import yaml
import math
'''
改為，接收封包(GameState)，以封包數據進行邏輯運算與決策，
輸出對應行為指令與目標資訊給控制模組
'''
class AutoControl:
    def __init__(self):

        # Search Config & Constants
        self.buffer = config.get("auto_control_config.buffer", 0) # <-- 邊界距離緩衝(平台的邊界距離+緩衝距離)
        self.platform_offset = config.get("auto_control_config.platform_offset", 5)
        # Data Containers & States
        self.health_setting = {}
        self.search_direction = random.choice(["LEFT", "RIGHT"])
        self.search_switch_time = time.time()
        self.recored_data = []
        self.platforms = [] #<-- 所有平台
        self.vertical_passage = [] #<-- 所有垂直通道
        self.current_platform = None #<-- 當前所在平台
        self.mini_player_loc = None #<-- 當前人物位置(小地圖)
        # Loadding Config
        self._load_health_config()
        self._load_map_data()
        # Parameters
        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range")


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
                self.vertical_passage = self._find_vertical_passage()

        except Exception as e:
            logging.error(f"載入地圖失敗{e}")


    def select_operation(self,state: GameState) -> tuple[Optional[str], Optional[dict]]:
        '''
        Args:
            state (GameState): 包含當前角色位置、血量、ROI 範圍及怪物清單的資料容器。
        '''

        #角色健康狀態
        level , heal_key = self._health_status_check(state.player_hp)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}

        #垂直通道判斷
        if state.mini_player_loc:

            result = self._check_current_vertical_passage()
            
            if result is not None:
                return self._trigger_vertocal_action(result)
        
        # 平台判斷
        if state.mini_player_loc:
            try:
                self.mini_player_loc = state.mini_player_loc
                self.current_platform = self.check_current_platform()
            except:
                pass

        #Debug
        # if self.current_platform is None:
        #     print("人物游離中")
        # else:
        #     print(f"目前在第{self.current_platform}個平台")


        #人物在平台內
        if self.current_platform:
            #有怪則找怪
            if state.mobs:
                result = self._fk_that_mob(state)
                return result
        if self.current_platform and self.enable_searching_mob :
            #巡弋動作
            result = self._enable_player_patrol()
            return result

        #若都沒有則閒置
        return "IDLE", None
    

    def _find_vertical_passage(self):
        '''
        找出垂直通道(繩子、跳下點)
        '''

        target_actions = ["rope_down", "rope_up", "jump_down"]

        filtered_data = [
        item for item in self.recored_data 
        if item.get("action") in target_actions
        ]

        return filtered_data
    
    def _check_current_vertical_passage(self):
        '''
        檢查人物是否在垂直通道
        '''
        if not self.mini_player_loc or not self.vertical_passage:
            return None
        threshold = 3

        matched_point = next(
            (
                point for point in self.vertical_passage
                if math.dist(self.mini_player_loc,point["loc"]) <= threshold),None
            
        )

        return matched_point

    def _trigger_vertocal_action(self,result:dict):
        '''
        觸發垂直通道動作
        '''
        if result is None:
            return None,None
        action_name = result["action"]
        target_loc = result["loc"]
        
        t_x, t_y  = target_loc
        c_x, c_y  =self.mini_player_loc

        #方向判斷
        direction = "RIGHT" if t_x > c_x else ("LEFT" if t_x < c_x else None)

        print(f"觸發垂直通道動作:{action_name},方向:{direction}")
        #狀態機回傳值
        if action_name == "rope_down":
            return self._pack_action("ROPE_DOWN", direction=direction)
        elif action_name == "rope_up":
            return self._pack_action("ROPE_UP", direction=direction)
        elif action_name == "jump_down":
            return self._pack_action("JUMP_DOWN", direction=direction)

        if c_y >= t_y:
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

                top = current["loc"][1] - self.platform_offset
                bottom = current["loc"][1] + self.platform_offset

                left = min(current["loc"][0], next_item["loc"][0])
                right = max(current["loc"][0], next_item["loc"][0])

                platforms.append({"t_l":(left,top),"b_r":(right,bottom)})
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
            left, top = plat["t_l"]     
            right, bottom = plat["b_r"] 

            if left <= px <= right and top <= py <= bottom:
                # 加一個1，不然0的話再判斷可能為None
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
        '''
        功能:在尋怪範圍內攻擊怪物
        '''
        if not state.player_center_loc:
            return None, None
        px, _ = state.player_center_loc

        # 計算距離/方向/目標/回傳 states module 結果
        best_target = None
        min_distance = float('inf')

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

        return "IDLE", None


    def _enable_player_patrol(self):
        '''
        巡邏邏輯
        '''

        px, py = self.mini_player_loc

        #要 -1 因為求平台時多加了
        plat_index = self.current_platform - 1
        current_plat = self.platforms[plat_index]
        
        left_bound = current_plat["t_l"][0]   # 平台的左極限 X
        right_bound = current_plat["b_r"][0]  # 平台的右極限 X
        #Debug
        # print(f"平台平台:{plat_index}平台。左邊界: {left_bound}, 右邊界: {right_bound}")
        # print(f"開始巡邏，位置:{self.mini_player_loc}")
        # print(self.buffer)

        if px <= left_bound + self.buffer:
            self.search_direction = "RIGHT"   # 強制向右
            # print(f"即將轉向: {self.search_direction}")
            return self._pack_action("MOVE", direction="RIGHT")

        elif px >= right_bound - self.buffer:
            self.search_direction = "LEFT"    # 強制向左
            # print(f"即將轉向: {self.search_direction}")
            return self._pack_action("MOVE", direction="LEFT")
        else:
            return self._pack_action("MOVE", direction=self.search_direction)


    def _pack_action(self, action_type, **kwargs):
        """
        將行為打包成字典
        """
        return action_type, kwargs if kwargs else None

