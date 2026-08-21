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
        #---[座標用容器]
        self.recored_data = []#<-- 所有行為點的容器
        self.platforms = [] #<-- 所有平台
        self.vertical_passage = [] #<-- 所有垂直通道
        self.current_platform = None #<-- 當前人物所在的平台
        self.current_vertical_passage = None #<-- 當前人物所在的垂直通道
        self.mini_player_loc = None #<-- 當前人物位置(小地圖)
        self.current_verti_target = None #<-- 當前垂直通道目標方向
        #---[道具用容器]
        self.mp_sorted_levels = [] #<-- 藍水等級排序
        self.hp_sorted_levels =[] #<-- 紅水等級排序
        #Timer
        self.patrol_start_time = None #巡邏開始時間
        self.hp_cooldown = 5 #<--紅水冷卻時間
        self.mp_cooldown = 5 #<--藍水冷卻時間
        self.last_hp_time = None #<--上次喝紅時間
        self.last_mp_time = None #<--上次喝藍時間
        #States
        self.is_climbing_state = False #在爬樓梯狀態
        self.is_finding_rope_state =False #找繩子狀態
        self.is_combat_state = True #戰鬥狀態
        # Loadding Config
        self._load_health_config()
        self._load_map_data()
        # Parameters
        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range")

        #Flags
        self.patrol_active = True  #巡邏
        self.battle_active = True  #戰鬥
        #Toggle/
        self.enable_searching_mob = config.get("auto_control_config.search_interval", False) # <-- 搜尋怪物功能(開//關)
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
        # mp_setting 結構範例: {"light": {"key": "delete", "value": 80}, ...}
        self.hp_sorted_levels = sorted(
            self.health_setting.items(),
            key=lambda item: item[1]["value"]
        )
        mp_raw = config.get("player_setting.mp_setting") or {}
        for level, setting in mp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":           #<--沒設置的水線，會被拋棄
                key = None

            self.mp_setting[level] = {
                "value" : value,
                "key" : key,
            }
        # mp_setting 結構範例: {"light": {"key": "delete", "value": 80}, ...}
        self.mp_sorted_levels = sorted(
            self.mp_setting.items(),
            key=lambda item: item[1]["value"]
        )
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

                logging.info(f"{map_name}地圖載入完成，平台數量:{len(self.platforms)},垂直通道數量:{len(self.vertical_passage)}")
                print(f"{map_name}地圖載入完成\n平台數量:{len(self.platforms)}\n垂直通道數量:{len(self.vertical_passage)}")
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
        level , heal_key = self._health_status_check(state.player_hp,current_time)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}
        level , mp_key = self._mp_status_check(state.player_mp, current_time)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": mp_key}
        
        '''測試用'''
        # # 判斷: (人物超出範圍) 人物在平台外，也不再繩子上
        # if not self.current_platform and self.current_vertical_passage is None:
        #     result = self._find_nearest_platform()
        #     print(f"最近的平台是{result}")
        # # 判斷: (人物超出範圍) 人物在平台外，也不再平台上
        # if not self.current_platform and self.current_platform  is None:
        #     result = self._find_nearest_platform()
        #     print(f"最近的垂直通道是{result}")
        '''
        =======
        '''

        # 模塊:打怪物
        if self.battle_active :
            if self.mini_player_loc and self.enable_searching_mob :
                if platform:= self._handle_platform_logic(state):
                    return platform

        # 模塊:左右邊界巡邏
        if self.current_platform and self.enable_searching_mob :
            # 初始化"巡邏狀態"
            if self.patrol_start_time is None:
                self.patrol_start_time = current_time
                self.patrol_state = True

            # 判斷:幾秒找不到怪，進入找通道
            if   current_time - self.patrol_start_time > self.verti_move_threshold:

                action = self._enter_verti()
            elif self.patrol_active:
                # 開始巡弋找怪
                result = self._enable_player_patrol()
                return result
        
        # 模塊:開始找路徑進行垂直移動
        if self.mini_player_loc:
            try:

                # 判斷:人物是否在垂直通道內
                self.current_vertical_passage = self._check_vertical_passage()

                # 觸發:不在垂直通道範圍
                if self.current_vertical_passage is None:
                    #自動去最近的垂直通道
                    index = self._find_nearest_verti_passage()
                    print(f"自動去最近的{index +1}號垂直通道")
                    return  self._move_to_verti_passage(index)

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
                    # 假如，爬繩子，則重置狀態屬性
                    
                    if self.is_climbing_state or self.is_finding_rope_state:
                        self.patrol_active = True
                    self.is_climbing_state = False
                    self.is_finding_rope_state = False
                    
            except Exception as e:
                logging.error(f"垂直通道判斷失敗{e}")

        # 重置爬行方向的狀態
        if self.current_verti_target is None:
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
    
    def _check_vertical_passage(self) -> Optional[int]:
        '''
        判斷玩家在哪個垂直通道內

        returns: 
            傳回垂直通道的index|None
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
        垂直移動邏輯
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
            print(f"進入通道，鎖定目標方向:{self.current_verti_target}")

        #=================
        #   假設 繩子 X為0  原地上跳 X也要為0 才能抓住；
        #   x = -1 與 1 左跳,右跳都抓不到繩子，要移動到x=0 用直接跳 或是 移動到 x= -2,2 則左跳右跳可以抓到繩子 
        #=================
        #容忍值
        trigger_tolerance = 3
        #判斷:方向為"UP" 且 人物處於通道底部附近
        if self.current_verti_target == "UP" and  bottom - trigger_tolerance <= py <= bottom :

            #狀態改變:找繩子
            self.is_finding_rope_state = True

            if px < central_axis :
                print("往右跳爬")
                return self._pack_action("ROPE", direction="RIGHT_UP")
            elif px > central_axis :
                print("往左跳爬")
                return self._pack_action("ROPE", direction="LEFT_UP")

            
        #判斷:方向為"UP" 且 處於y軸範圍 
        elif self.current_verti_target == "UP" and top - trigger_tolerance < py < bottom:

            print("向上爬行...")

            #狀態改變:退出找繩子，進入爬繩子
            self.is_finding_rope_state =False
            self.is_climbing_state = True
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        elif self.current_verti_target == "UP" and py <= top - trigger_tolerance:
            print("到達頂部，重置狀態")
            self._exit_verti()
            return None
        
        #判斷:方向為"DOWN"
        if self.current_verti_target == "DOWN" and  top <= py <= top + trigger_tolerance:

            #狀態改變:找繩子
            self.is_finding_rope_state = True

            if px < central_axis :
                print("往右下跑")
                return self._pack_action("ROPE", direction="RIGHT_DOWN")
            elif px > central_axis :
                print("往左下跑")
                return self._pack_action("ROPE", direction="LEFT_DOWN")

            
        #判斷:方向為"DOWN" 且 處於y軸範圍 
        elif self.current_verti_target == "DOWN"  and top < py <= bottom:
            print("正在下爬")
            #狀態改變:退出找繩子，進入爬繩子
            self.is_finding_rope_state =False
            self.is_climbing = True
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        elif self.current_verti_target == "DOWN" and py >= bottom:
            print("到達底部，重置狀態")
            #到達底部，重置狀態
            self._exit_verti()
            return None
        
        return None
    def _enter_verti(self):
        '''
        功能:進入通道前，狀態改變
            關閉:巡邏、打怪
        '''
        self.patrol_active = False   #
        self.patrol_start_time = None
        self.battle_active = False

    def _exit_verti(self):
        '''
        功能:離開通道時，狀態重置
        '''
        self.current_verti_target = None
        self.is_climbing_state = False
        self.patrol_active = True
        self.battle_active = True
    #=================
    # 邏輯塊: 水平平台
    #=================
    def _find_platform(self):
        """
        找出平台
        用滑動窗口直接從list內抓出平台，加上偏移量，製作出平台範圍
        """

        platforms = []

        #平台誤差範圍

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
    def _health_status_check(self,player_hp,current_time): 

        '''
        血量情況判斷與行動分流
        回傳: 血量分級、對應按鍵
        '''

        if player_hp is None:
            return None, None  # 防呆:# player_hp 為 None 時提前擋下

        if not (0 < player_hp <= 100):
            logging.debug(f"血量取值異常: {player_hp} ")
            return None, None

        if not self.health_setting:
            return None, None 



        if self.last_hp_time is None:
            self.last_hp_time = current_time
        # 喝水冷卻時間
        if (current_time - self.last_hp_time) < self.hp_cooldown:
            return None, None

        #主要判斷
        for level, setting in self.hp_sorted_levels:
            if player_hp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                self.last_hp_time = current_time
                return level, key
        return None, None

    def _mp_status_check(self,player_mp,current_time): 


        if player_mp is None:
            return None, None  # 防呆:# player_mp 為 None 時提前擋下

        if not (0 < player_mp <= 100):
            logging.info(f"魔力取值異常: {player_mp} ")
            return None, None


        # 沒有設定喝水，直接回傳None
        if not self.mp_setting:
            return None, None 

        if self.last_mp_time is None:
            self.last_mp_time = current_time
        # 喝水冷卻時間
        if (current_time - self.last_mp_time) < self.mp_cooldown:
            return None, None
        
        #主要判斷
        for level, setting in self.mp_sorted_levels:
            if player_mp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                self.last_mp_time = current_time
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
    # 邏輯塊: 人物移動
    #=================
    def _enable_player_patrol(self)-> tuple[Optional[str], Optional[dict]]:
        '''
        功能:平台範圍內左右巡邏
        '''

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

    def _find_nearest_platform(self):
        """
        功能:找最近的平台
        return: 平台引所對應的index 
        """
        if not self.mini_player_loc or not self.platforms:
            return None

        px , py = self.mini_player_loc

        nearest_platform_index = None
        #跟找怪邏輯一樣，從無限距離開始判斷
        nearest_distance = float('inf')

        for index, plat in enumerate(self.platforms):

            left, top = plat["t_l"]
            right, bottom = plat["b_r"]

            if left <= px <= right:
                dx = 0
            else:
                dx = min(abs(px - left), abs(px - right))
            dy = min(abs(py - top), abs(py - bottom))

            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_platform_index  = index

        return nearest_platform_index 
    
    # def _find_nearest_verti_passage(self) -> Optional[int]:
    #     """
    #     功能:找最近的垂直通道
    #     return: 平台引所對應的index 
    #     問題:純畢氏距離找最近通道
    #         隔著平台會卡住
    #     """
    #     if not self.mini_player_loc or not self.vertical_passage:
    #         return None

    #     px , py = self.mini_player_loc

    #     nearest_verti_passage_index = None
    #     #跟找怪邏輯一樣，從無限距離開始判斷
    #     nearest_distance = float('inf')

    #     for index, plat in enumerate(self.vertical_passage):

    #         left, top = plat["t_l"]
    #         right, bottom = plat["b_r"]

    #         if left <= px <= right:
    #             dx = 0
    #         else:
    #             dx = min(abs(px - left), abs(px - right))

    #         dy = min(abs(py - top), abs(py - bottom))
    #         distance = (dx ** 2 + dy ** 2) ** 0.5

    #         if distance < nearest_distance:
    #             nearest_distance = distance
    #             nearest_verti_passage_index  = index

    #     return nearest_verti_passage_index

    def _find_nearest_verti_passage(self) -> Optional[int]:

        if not self.mini_player_loc or not self.vertical_passage:
            return None

        px, py = self.mini_player_loc

        # 先試著找「跟目前平台 x 範圍有重疊」的通道，這些是人物可移動到的
        reachable_candidates = []
        if self.current_platform:
            #先抓定位平台座標
            plat = self.platforms[self.current_platform - 1]
            plat_left, plat_right = plat["t_l"][0], plat["b_r"][0]

            for index, passage in enumerate(self.vertical_passage):
                p_left, p_right = passage["t_l"][0], passage["b_r"][0]
                # 通道的 x 範圍，跟目前平台的 x 範圍有重疊，才算走得到
                if not (p_right < plat_left or p_left > plat_right):
                    reachable_candidates.append(index)

        # 如果有找到能走到的候選，只在這些裡面挑最近的
        search_pool = reachable_candidates if reachable_candidates else range(len(self.vertical_passage))

        nearest_verti_passage_index = None
        nearest_distance = float('inf')

        for index in search_pool:
            plat = self.vertical_passage[index]
            left, top = plat["t_l"]
            right, bottom = plat["b_r"]

            if left <= px <= right:
                dx = 0
            else:
                dx = min(abs(px - left), abs(px - right))
            dy = min(abs(py - top), abs(py - bottom))

            distance = (dx ** 2 + dy ** 2) ** 0.5

            if distance < nearest_distance:
                nearest_distance = distance
                nearest_verti_passage_index = index

        return nearest_verti_passage_index

    def _move_to_verti_passage(self, verti_passage_index)-> tuple[Optional[str], Optional[dict]]:
        '''
        arges: 
            verti_passage_index: 垂直通道的index
        return:
            self._pack_action("MOVE", direction="RIGHT"or "LEFT")
        '''
        px , py = self.mini_player_loc

        if px < self.vertical_passage[verti_passage_index]["t_l"][0]:
            return self._pack_action("MOVE", direction="RIGHT")
        else:
            return self._pack_action("MOVE", direction="LEFT")
    #=================
    # 工具
    #=================
    def _pack_action(self, action_type, **kwargs):
        """
        將行為打包成字典
        """
        return action_type, kwargs if kwargs else None



