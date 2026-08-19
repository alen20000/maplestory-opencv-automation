import time
import logging
from config.config_loader import config
from typing import Optional
from src.engine.game_state import GameState
import time
import random
from pathlib import Path
import yaml
import time
'''
改為，接收封包(GameState)，以封包數據進行邏輯運算與決策，
輸出對應行為指令與目標資訊給控制模組
'''
class AutoControl:
    def __init__(self):

        # Search Config & Constants
        self.buffer = config.get("auto_control_config.buffer", 0) # <-- 邊界距離緩衝(平台的邊界距離+緩衝距離)
        self.platform_offset = config.get("auto_control_config.platform_offset",5)
        self.verti_move_threshold = config.get("auto_control_config.verti_move_threshold",10)
        # Data Containers
        self.health_setting = {}
        self.mp_setting = {}
        self.search_direction = random.choice(["LEFT", "RIGHT"])

        self.recored_data = []#<-- 所有行為點的容器
        self.platforms = [] #<-- 所有平台
        self.vertical_passage = [] #<-- 所有垂直通道
        self.current_platform = None #<-- 當前人物所在的平台
        self.current_vertical_passage = None #<-- 當前人物所在的垂直通道
        self.mini_player_loc = None #<-- 當前人物位置(小地圖)
        self.current_verti_target = None #<-- 當前垂直通道目標方向

        #Timer
        self.patrol_start_time = None #巡邏開始時間

        #States
        self.is_climbing_state = False #在爬樓梯狀態
        self.is_finding_rope_state =False #找繩子狀態
        self.is_combat_state = True #戰鬥狀態
        # Loadding Config
        self._load_health_config()
        self._load_map_data()
        # Parameters
        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range")


        #Toggle/
        self.enable_searching_mob = config.get("auto_control_config.search_interval", False) # <-- 搜尋怪物功能
    #=================
    # 載入設定
    #=================
    def _load_health_config(self):

        '''
        喝水設定載入
        '''

        hp_raw = config.get("player_setting.health_setting") or {}

        for level, setting in hp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":
                key = None

            self.health_setting[level] = {
                "value" : value,
                "key" : key,
            }
        mp_raw = config.get("player_setting.mp_setting") or {}

        for level, setting in mp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":
                key = None

            self.mp_setting[level] = {
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

                logging.warning(f"{map_name}地圖載入完成，平台數量:{len(self.platforms)},垂直通道數量:{len(self.vertical_passage)}")

        except Exception as e:
            logging.error(f"載入地圖失敗{e}")

    #=================
    # 主要邏輯
    #=================
    def select_operation(self,state: GameState) -> tuple[Optional[str], Optional[dict]]:
        '''
        Args:
            state (GameState): 包含當前角色位置、血量、ROI 範圍及怪物清單的資料容器。
        '''

        #角色座標更新
        if state.mini_player_loc:
            self.mini_player_loc = state.mini_player_loc

        #時間標籤
        current_time =time.time()

        # 模塊:健康狀態(喝水)
        level , heal_key = self._health_status_check(state.player_hp)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}
        level , mp_key = self._mp_status_check(state.player_mp)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": mp_key}
        
        # 模塊:打怪物
        if self.mini_player_loc and self.enable_searching_mob:
            if platform:= self._handle_platform_logic(state):
                return platform

        # 模塊:左右邊界巡邏
        if self.current_platform and self.enable_searching_mob :
            # 初始化"巡邏狀態"
            if self.patrol_start_time is None:
                self.patrol_start_time = current_time
                self.patrol_state = True

            # 找不到怪"X"秒 就關閉巡邏狀態
            if   current_time - self.patrol_start_time > self.verti_move_threshold:
                print("平台巡邏超時，切換至尋找上下通道")

                self.patrol_start_time = None
            else:
                # 平台檢查
                self.current_platform = self._check_current_platform()
                #正常巡邏
                result = self._enable_player_patrol()
                return result
        
        # 模塊:找下移動模塊
        if self.mini_player_loc:
            try:

                # 判斷:人物是否在垂直通道內
                self.current_vertical_passage = self._check_vertical_passage()

                # 觸發:人物在垂直通道範圍 且 時間允許
                if self.current_vertical_passage is not None:

                    self.pervious_time = current_time

                    # 禁止戰鬥
                    self.is_combat_state = False

                    # 開始垂直移動
                    result = self._verti_movement()
                    if result is not None:
                        return result
                else:
                    # 重置狀態屬性

                    self.is_climbing_state = False
                    self.is_finding_rope_state = False
            except Exception as e:
                logging.error(f"垂直通道判斷失敗{e}")

        # 重置爬行方向的狀態
        self.current_verti_target = None
        # 如果人物脫離垂直通道，則允許戰鬥
        if self.current_vertical_passage is None:
            self.is_combat_state = True


        return None,None

    def _handle_platform_logic(self, state: GameState) -> tuple[Optional[str], Optional[dict]]:
        """
        處理平台內判斷、打怪、巡弋邏輯
        """
            #觸發:有人物座標時
        if self.mini_player_loc:
            try:
                # 平台判斷
                self.current_platform = self._check_current_platform()
            except Exception as e:
                logging.error(f"平台判斷失敗{e}")

        #觸發:人物在平台內時
        if self.current_platform:
            #有怪則找怪
            if state.mobs:
                
                # 觸發:有怪物就重置巡邏計時與狀態
                self.patrol_start_time = None
                self.patrol_state = True

                result = self._fk_that_mob(state)
                return result
            

        
    #=================
    # 邏輯塊: 垂直通道
    #=================
    def _find_vertical_passage(self):
        '''
        找出垂直通道(繩子)，並製作出垂直通道範圍

        若 x 為 0 ；  -3 ~3 之間 ，基礎素質能跳爬
        '''
        passage = []
        i = 0
        while i < len(self.recored_data)-1:
            current = self.recored_data[i]
            next_item = self.recored_data[i + 1]

            #垂直通道的offset，先寫死在這，有需要再抽離
            offset = 3
            if current["action"] == "rope" and next_item["action"] == "rope":

                top = min(current["loc"][1],next_item["loc"][1])
                bottom = max(next_item["loc"][1],current["loc"][1])

                left = min(current["loc"][0], next_item["loc"][0]) - offset
                right = max(current["loc"][0], next_item["loc"][0]) + offset

                passage.append({"t_l":(left,top),"b_r":(right,bottom)})
                i += 2
            else:
                i += 1

        return passage
    
    def _check_vertical_passage(self):
        '''
        判斷玩家在哪個垂直通道內

        returns: 垂直通道的index|None
        '''
        if not self.mini_player_loc or not self.vertical_passage:
            return None

        px, py = self.mini_player_loc 

        for index, vert in enumerate(self.vertical_passage):
            left, top = vert["t_l"]     
            right, bottom = vert["b_r"] 

            if left <= px <= right and top <= py <= bottom:
                # 加一個1，不然0的話再判斷可能為None
                index += 1

                return index  

        return None


    def _verti_movement(self):
        """
        垂直移動判斷
        """
        #通道有+1，要減掉才是正確的index
        verti_index = self.current_vertical_passage -1
        current_verti_passage = self.vertical_passage[verti_index]

        px, py = self.mini_player_loc

        top = current_verti_passage["t_l"][1]
        bottom = current_verti_passage["b_r"][1]
        mid_y = (top + bottom) // 2
        central_axis = current_verti_passage["t_l"][0] + (current_verti_passage["b_r"][0] - current_verti_passage["t_l"][0]) // 2

        # 固定上下的方向
        if self.current_verti_target is None:
            self.current_verti_target = "UP" if py > mid_y else "DOWN"

            #debug
            # print(f"進入通道，鎖定目標方向:{self.current_verti_target}")

        #=================
        #   假設 繩子 X為0  原地上跳 X也要為0 才能抓住；
        #   x = -1 與 1 左跳,右跳都抓不到繩子，要移動到x=0 用直接跳 或是 移動到 x= -2,2 則左跳右跳可以抓到繩子 
        #=================
        
        #判斷:方向為"UP" 且 人物處於通道底部
        if self.current_verti_target == "UP" and py == bottom :
            self.is_finding_rope_state = True

            if px < central_axis :
                return self._pack_action("ROPE", direction="RIGHT_UP")
            elif px > central_axis :

                return self._pack_action("ROPE", direction="LEFT_UP")
            elif px == central_axis:
                print(f"原地上跳:人物X軸 {px}；繩子X軸 {central_axis}")
                return self._pack_action("ROPE", direction="UP")
            
        #判斷:方向為"UP" 且 處於y軸範圍 
        elif self.current_verti_target == "UP" and top <= py < bottom:
            print("CLIMB_UP")
            #狀態改變
            self.is_finding_rope_state =False
            self.is_climbing_state = True
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        elif self.current_verti_target == "UP" and py <= top:
            print("到達頂部，重置狀態")
            #到達頂部，重置狀態
            self.is_climbing_state = False
            return self._pack_action("IDLE", None)
        
        #判斷:方向為"DOWN"
        if self.current_verti_target == "DOWN" and py == top:
            #狀態改變
            self.is_finding_rope_state = True

            if px < central_axis and py == top:
                print("往右下跑")
                return self._pack_action("ROPE", direction="RIGHT_DOWN")
            elif px > central_axis and py == top:
                print("往左下跑")
                return self._pack_action("ROPE", direction="LEFT_DOWN")
            elif px == central_axis and py == top: #<---要加個py == top判定，否則下方的CLIMB DOWN不會觸發
                print("原地下降")
                return self._pack_action("ROPE", direction=self.current_verti_target)
            
        #判斷:方向為"DOWN" 且 處於y軸範圍 
        elif self.current_verti_target == "DOWN"  and top < py <= bottom:
            print("正在下爬")
            #狀態改變
            self.is_finding_rope_state =False
            self.is_climbing = True
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        elif self.current_verti_target == "DOWN" and py >= bottom:
            print("到達底部，重置狀態")
            #到達底部，重置狀態
            self.is_climbing_state = False
            return self._pack_action("IDLE", None)
        
        return None
        

    #=================
    # 邏輯塊: 水平平台
    #=================
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

    def _check_current_platform(self):
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

    #=================
    # 邏輯塊: 健康狀態
    #=================
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

    def _mp_status_check(self,player_mp): 

        if not (0 <= player_mp <= 100):
            logging.warning(f"血量取值異常: {player_mp} ")
            return None, None

        #防呆
        if player_mp is None:
            return None, None 

        #按鍵預設，與GameBot同步
        mp_setting = self.mp_setting

        if not mp_setting:
            return None, None 


        #結構: {"light":    {"key": "delete", "value": 80},..,}
        sorted_levels = sorted(
            mp_setting.items(),
            key=lambda item: item[1]["value"]
        )

        #主要判斷
        for level, setting in sorted_levels:
            if player_mp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                return level, key
            
        return None, None
    
    #=================
    # 邏輯塊: 打怪物
    #=================
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
            #debug
            # print(f"目標 [{best_target['name']}] 在攻擊範圍內 距離: {best_target['distance']} 方向: {best_target['direction']}")
            return "ATTACK" , best_target

        return None

    #=================
    # 邏輯塊: 水平移動
    #=================
    def _enable_player_patrol(self)-> tuple[Optional[str], Optional[dict]]:


        px, py = self.mini_player_loc

        #要 -1 因為求平台時多加了
        plat_index = self.current_platform - 1
        current_plat = self.platforms[plat_index]
        
        left_bound = current_plat["t_l"][0]   # 平台的左極限 X
        right_bound = current_plat["b_r"][0]  # 平台的右極限 X

        if px <= left_bound + self.buffer:
            self.search_direction = "RIGHT"   # 走到底右轉

            return self._pack_action("MOVE", direction="RIGHT")

        elif px >= right_bound - self.buffer:
            self.search_direction = "LEFT"    # 走到底左轉

            return self._pack_action("MOVE", direction="LEFT")
        #這句不能改，否則人物會罰站
        else:
            return self._pack_action("MOVE", direction=self.search_direction)

    #=================
    # 工具
    #=================
    def _pack_action(self, action_type, **kwargs):
        """
        將行為打包成字典
        """
        return action_type, kwargs if kwargs else None



