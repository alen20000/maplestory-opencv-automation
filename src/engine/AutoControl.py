import time
import logging
from config.config_loader import config
from typing import Optional
from src.engine.game_state import GameState
from src.engine.HealthManager import HealthManager
from src.engine.fsm.BotState import BotState
import time
import random
from pathlib import Path
import yaml
import time
from enum import Enum, auto
'''
改為，接收封包(GameState)，以封包數據進行邏輯運算與決策，
輸出對應行為指令與目標資訊給控制模組

健康控制用插入
狀態種類(互斥責為狀態): COMBAT、
'''
#===全域常數===
VERTI_MOVE_STAY_TIMEOUT = 0.6 # < -  管理"向上攀爬"出去後，停留多久退出攀爬動作的時間記數

#======
class AutoControl:

    def __init__(self):

        #---[實例化]
        self.health_manager = HealthManager()
        self.bot_state = BotState(self) # 把自己(AutoControl)交給狀態機當 owner，讓狀態機能反過來呼叫函式或共用資料

        #---[外部參數&設定]
        self.buffer = config.get("auto_control_config.buffer", 0) # <-- 邊界距離緩衝(平台的邊界距離+緩衝距離)
        self.verti_move_threshold = config.get("auto_control_config.verti_move_threshold",10)
        self.JUMP_DISTANCE_THRESHOLD = config.get("auto_control_config.JUMP_DISTANCE_THRESHOLD", 10)
        self.ACTION_POINT_RANGE = config.get("auto_control_config.ACTION_POINT_RANGE", 1)
        #---[內部參數&設定]
        self.search_direction = random.choice(["LEFT", "RIGHT"]) #<-- 巡邏方向;第一次初始化隨機方向
        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range") # <-- 玩家攻擊範圍

        #---[地圖用容器]
        self.recored_data = []#<-- 所有行為點的容器
        self.platforms = [] #<-- 所有平台
        self.vertical_passage = [] #<-- 所有垂直通道
        self.jump_points = [] #<-- 所有單點跳躍點(JumpLeft/JumpRight)

        #---[座標用容器]
        self.current_platform = None #<-- 當前人物所在的平台
        self.current_vertical_passage = None #<-- 當前人物所在的垂直通道
        self.mini_player_loc = None #<-- 當前人物位置(小地圖)
        self.last_player_loc = None #<-- 上次人物位置(小地圖)
        self.current_verti_target = None #<-- 當前垂直通道目標方向
        self.last_player_y_loc = None #<==defc last_player_y_loc 使用

        #---[定時器]
        self.detect_move_stuck_timer = 0 #<--移動卡住計時器
        self._verti_movement_timer = None #<--垂直移動計時器
        #---[載入設定]
        self._load_map_data()



    #=================
    # 載入設定
    #=================

    def _load_map_data(self):
        '''
        載入地圖模板、預設座標
        '''
        try:
            map_name = config.get("quickly_choice_map")
            self.mini_map = Path(config.get(f"mini_map.{map_name}"))
            folder_path = self.mini_map.parent
            yaml_path = folder_path / f"{map_name}.yaml"

            if yaml_path.exists():
                with open(yaml_path, "r") as f:
                    self.recored_data = yaml.safe_load(f)

                # 解析平台和垂直通道
                self.platforms = self._find_platform()
                self.vertical_passage = self._find_vertical_passage()
                self.jump_points = self._find_jump_points()
                logging.info(f"{map_name}地圖載入完成，平台數量:{len(self.platforms)},垂直通道數量:{len(self.vertical_passage)},跳躍點數量:{len(self.jump_points)}")
                print(f"{map_name}地圖載入完成\n平台數量:{len(self.platforms)}\n垂直通道數量:{len(self.vertical_passage)},跳躍點數量:{len(self.jump_points)}")
        except Exception as e:
            logging.error(f"載入地圖失敗{e}")

    #=================
    # 功能:地圖感測
    #=================

    def _find_platform(self):
        """
        功能:
            分析路徑設定，拆出每個平台、平台範圍。
        """
        platforms = []
        i= 0
        while i < len(self.recored_data)-1:
            current = self.recored_data[i]
            next_item = self.recored_data[i + 1]

            if current["action"] =='walk' and next_item["action"] == 'walk':

                top = min(current["loc"][1], next_item["loc"][1])  - 2
                bottom = max(current["loc"][1], next_item["loc"][1]) + 6
                left = min(current["loc"][0], next_item["loc"][0])
                right = max(current["loc"][0], next_item["loc"][0]) 

                platforms.append({"t_l":(left,top),"b_r":(right,bottom)})
                i += 2
            else:
                i += 1 

        return platforms
    
    def _find_vertical_passage(self):
        '''
        功能:
            分析路徑設定，拆出垂直通道(繩子)，並製作出垂直通道範圍

            垂直通道若 x 為 0 ；  -3 ~3 之間 ，人物基礎素質能跳爬
        '''
        passage = []
        i = 0
        while i < len(self.recored_data) - 1:
            current = self.recored_data[i]
            next_item = self.recored_data[i + 1]

            if current["action"] == "rope" and next_item["action"] == "rope":

                top = min(current["loc"][1],next_item["loc"][1]) - 2
                bottom = max(next_item["loc"][1],current["loc"][1]) + 3

                left = min(current["loc"][0], next_item["loc"][0]) - 3
                right = max(current["loc"][0], next_item["loc"][0]) + 3

                passage.append({"t_l":(left,top),"b_r":(right,bottom)})
                i += 2
            else:
                i += 1

        return passage
    
    def _find_jump_points(self):
        '''
        功能:
            解析路徑設定，拆出單點跳躍點(JumpLeft / JumpRight)。

        '''
        JUMP_ACTION_DIRECTION = {
            "JumpLeft": "LEFT",
            "JumpRight": "RIGHT",
            "JumpDown":"DOWN",
            "JumpUp":"UP"
        }

        jump_points = []
        for item in self.recored_data:
            direction = JUMP_ACTION_DIRECTION.get(item.get("action"))
            if direction is None:
                continue
    
            x, y = item["loc"]
            jump_points.append({"loc": (x, y), "direction": direction})
        print(f"跳躍點數量：{len(jump_points)}")
        return jump_points
    #=================
    # 主要邏輯
    #=================
    def run(self,state: GameState) -> tuple[Optional[str], Optional[dict]]:
        '''
        Args:
            state (GameState): 包含當前角色位置、血量、ROI 範圍及怪物清單的資料容器。
        '''
        #===========
        # 每輪資訊更新
        #===========
        
        if state.mini_player_loc:   #角色座標更新
            self.mini_player_loc = state.mini_player_loc
        current_time =time.time()   #時間標籤

        #依賴檢查
        if self.mini_player_loc is None or self.platforms is None:
            logging.warning("缺失自動化必要信息，跳過此幀")
            return None, None

        if self.current_platform is None:
            self.current_platform = self._check_current_platform() #判斷人在哪一個平台



        #===========
        # 管理模組: 健康模組
        #===========
        # 喝水不再狀態機處理，另外處理
        health_action = self.health_manager.run(state.player_hp,state.player_mp,current_time)

        if health_action is not None:
            return health_action

        # state 資料給狀態機，回傳值在拆解為 action ,params ，並回傳給Gamebot模組
        action, params = self.bot_state.handle(state)   

        return action, params 


    



    #=================
    # 邏輯塊: 脫困功能
    #=================

    def _unstuck_player(self):
            '''
            功能:
                人物超出範圍、人物不動時、觸發防卡邏輯
            '''
            # 更新一下目前在哪一個平台
            self.current_platform = self._check_current_platform()
            is_in_vertical_passage = self._check_vertical_passage()

            # 情況A : 人物在垂直通道卡住
            if is_in_vertical_passage is None:
                return self._random_move()

            # 情況B: 人物在平台卡住
            if self.current_platform is None:
                # 移動至最近平台
                result = self._find_nearest_platform()
                if result is not None:
                    result = self._move_to_platform(result)
                    return result
                else:
                    return None, None
            
            # 情況C: 其他
            else:
                return self._random_move()
    
    def _random_move(self):
        '''
        功能:
            給_unstuck_player 使用
            用list拼出隨機移動
        '''
        action_list = ["JUMP","MOVE"]
        action_direction_list = ["RIGHT","LEFT"]
        action = random.choice(action_list)
        direction = random.choice(action_direction_list)
        return self._pack_action(action, direction=direction)
    
    def _find_nearest_platform(self):
        """
        功能:
            根據玩家目前的座標找最近的平台
        return:
            傳回最近平台的index 
        """

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
    
    def _move_to_platform(self, platform_index)-> tuple[Optional[str], Optional[dict]]:
        '''
        功能:控制人物移動到目標平台
        arges: 
            verti_passage_index: 垂直通道的index
        return:
            self._pack_action("MOVE", direction="RIGHT"or "LEFT")
        '''
        if self.mini_player_loc:
            px , _ = self.mini_player_loc

            # (1) 防卡:防止被怪物攻擊而阻斷移動狀態，發一個"閒置停止"的指令，觸發脈衝
            stuck_action =self._give_pulse_to_stuck()
            if stuck_action is not None:
                return stuck_action

            # (2) 主邏輯
            if px < self.platforms[platform_index]["t_l"][0]:
                return self._pack_action("MOVE", direction="RIGHT")
            else:
                return self._pack_action("MOVE", direction="LEFT")
        return None
    
    def _give_pulse_to_stuck(self):
        ''' 
        功能:
            人物座標沒變化，則產生脈衝
        效果:
            若人物卡住，發一個"閒置停止"的指令，產生脈衝
        '''
        current_time = time.time()

        # 記錄第一次"上次位置"，初始化卡住計時器
        if self.last_player_loc is None:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return None
        
        # 變動監測
        if self.last_player_loc != self.mini_player_loc:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return None 
        
        if current_time - self.detect_move_stuck_timer > 1.5:
            print("人物位置沒有變化，重新觸發脈衝")
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer  = current_time
            return self._pack_action("IDLE",command="STOP_MOVE")
        
    def _is_loc_y_change(self) -> bool:
        '''
        功能:
            用上次的Y軸位置與現在的Y軸位置判斷是否移動
            
        return 
            True | False
        '''

        if self.last_player_y_loc is None:
            self.last_player_y_loc = self.mini_player_loc[1]
            return True  

        changed = self.last_player_y_loc != self.mini_player_loc[1]
        self.last_player_y_loc = self.mini_player_loc[1]
        return changed

    #=================
    # 邏輯塊: 垂直移動相關
    #=================

    def _find_nearest_verti_passage(self) -> Optional[int]:
        """
        功能:
            先找目前平台內最近的垂直通道
        要求:
            self.mini_player_loc
            self.current_platform
        return: 
            平台引所對應的index 
            
        注意: 判定通道的頂部或底部，需要有任一端點落在平台的垂直範圍內
        """
        if not self.mini_player_loc or not self.vertical_passage:
            return None
        # 先找目前平台
        self.current_platform = self._check_current_platform()
        px, py = self.mini_player_loc

        # 先試著找「跟目前平台 x 範圍有重疊」的通道，這些是人物可移動到的
        reachable_candidates = []

        if self.current_platform is not None:  # 一定藥用 not noe 因為 index 是0計數，0會被判別 false

            plat = self.platforms[self.current_platform]

            plat_left, plat_right = plat["t_l"][0], plat["b_r"][0]
            plat_top, plat_bottom = plat["t_l"][1], plat["b_r"][1] 

            for index, passage in enumerate(self.vertical_passage):
                verti_left, verti_right = passage["t_l"][0], passage["b_r"][0]
                verti_top, verti_bottom = passage["t_l"][1], passage["b_r"][1]

                x_overlap = not (verti_right < plat_left or verti_left > plat_right)
                y_touch = (plat_top  <= verti_top <= plat_bottom  ) or (plat_top <= verti_bottom <= plat_bottom)

                if x_overlap and y_touch:
                    reachable_candidates.append(index)

        # 如果當前平台內沒有對應的垂直通道，直接回傳 None
        if not reachable_candidates:
            print("找不到鄰近的垂直通道")
            return None

        nearest_verti_passage_index = None
        nearest_distance = float('inf')

        for index in reachable_candidates:
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
        功能:
            控制人物移動到目標垂直通道範圍內
        arges: 
            verti_passage_index: 垂直通道的index
        return:
            self._pack_action("MOVE", direction="RIGHT"or "LEFT")
        '''
        px , _ = self.mini_player_loc
        my_verti_passage = self._check_vertical_passage()
        # (1) 防卡:防止被怪物攻擊而阻斷移動狀態，發一個"閒置停止"的指令，觸發脈衝
        stuck_action =self._give_pulse_to_stuck()
        if stuck_action is not None:
            return stuck_action
        print(f"目前垂直通道:{my_verti_passage}  目標垂直通道:{verti_passage_index}")
        # (2) 主邏輯
        if my_verti_passage == verti_passage_index: 

            return self._pack_action("IDLE",command="RELEASE_ALL")
        if px < self.vertical_passage[verti_passage_index]["t_l"][0]:
            print(f"玩家座標:{px}；走至座標:{self.vertical_passage[verti_passage_index]['t_l'][0]}")
            return self._pack_action("MOVE", direction="RIGHT")
        else:
            print(f"玩家座標:{px}；走至座標:{self.vertical_passage[verti_passage_index]['t_l'][0]}")
            return self._pack_action("MOVE", direction="LEFT")
    #=================
    # 邏輯塊: 單點跳躍相關(JumpLeft/JumpRight)
    #=================

    def _check_jump_point(self) -> Optional[int]:
        '''
        功能:
            判斷玩家目前座標是否已經落在某個跳躍點的抵達容忍範圍內
        要求:
            self.mini_player_loc
            self.jump_points
        return:
            跳躍點的index | None
        '''
        if not self.mini_player_loc or not self.jump_points:
            return None

        px, py = self.mini_player_loc
        threshold = self.ACTION_POINT_RANGE  # <== 容忍範圍，還要抓合適的參數

        for index, point in enumerate(self.jump_points):
            jx, jy = point["loc"]
            if abs(px - jx) <= threshold and abs(py - jy) <= threshold:
                return index

        return None

    def _find_nearest_jump_point(self) -> Optional[int]:
        '''
        功能:
            在玩家目前座標附近，找出最近的單點跳躍點
        要求:
            self.mini_player_loc
            self.jump_points
        return:
            最近跳躍點的index | None (超出搜尋範圍或沒有跳躍點時回傳None)
        '''
        if not self.mini_player_loc or not self.jump_points:
            return None

        px, py = self.mini_player_loc
        nearest_index = None
        nearest_score = float('inf')

        for index, point in enumerate(self.jump_points):
            jx, jy = point["loc"]

            dx = px  - jx
            dy = py - jy

            y_weight = 5
            score = (dx ** 2 + (dy * y_weight) ** 2) ** 0.5

            if score < nearest_score:
                nearest_score = score
                nearest_index = index

        # 太遠的跳躍點不採用，避免人物跑去很遠的地方硬跳
        if nearest_index is not None:
            jx, jy = self.jump_points[nearest_index]["loc"]
            actual_distance = ((px - jx) ** 2 + (py - jy) ** 2) ** 0.5
            if actual_distance <= self.JUMP_DISTANCE_THRESHOLD:
                return nearest_index

        return None

    def _move_to_jump_point(self, jump_index) -> tuple[Optional[str], Optional[dict]]:
        '''
        功能:控制人物移動到目標跳躍點座標
        args:
            jump_index: 跳躍點的index
        return:
            self._pack_action("MOVE", direction="RIGHT" or "LEFT")
        '''
        if not self.mini_player_loc:
            return None, None

        # (1) 防卡:防止被怪物攻擊而阻斷移動狀態，發一個"閒置停止"的指令，觸發脈衝
        stuck_action = self._give_pulse_to_stuck()
        if stuck_action is not None:
            return stuck_action

        # (2) 主邏輯
        px, _ = self.mini_player_loc
        jx, _ = self.jump_points[jump_index]["loc"]

        if px < jx  :
            return self._pack_action("MOVE", direction="RIGHT")
        else:
            return self._pack_action("MOVE",  direction="LEFT")
 

    def _do_jump(self, jump_index) -> tuple[Optional[str], Optional[dict]]:
        '''
        功能:
            已抵達跳躍點時，依紀錄的方向執行單次跳躍
        args:
            jump_index: 跳躍點的index
        return:
            self._pack_action("JUMP_GRAB", direction="RIGHT" |"LEFT"|"DOWN"|"UP"|M_RIGHT|M_LEFT)
        '''
        direction = self.jump_points[jump_index]["direction"]
        print(f"到達{jump_index}號跳躍點，執行 {direction} 方向跳躍")
        return self._pack_action("JUMP_GRAB", direction=direction)


    #=================
    # 分類: 已與狀態機掛勾執行函式
    #=================
    def _enable_player_patrol(self)-> tuple[Optional[str], Optional[dict]]:
        '''
        功能:
            人物開始巡邏
        效果:
            在平台範圍內左右移動
        需求:
            - self.mini_player_loc : 人物座標
            - self.current_platform : 當前平台index
        '''
        # 依賴檢查：無平台資訊就拋棄此幀
        if self.current_platform is None :
            return None,None

        px, _ = self.mini_player_loc

        plat_index = self.current_platform
        current_plat = self.platforms[plat_index]
        
        left_bound = current_plat["t_l"][0] 
        right_bound = current_plat["b_r"][0]

        #=====
        #   平台內人物的四種情況
        # 1.最左邊與最左邊+緩衝值之間 2.最右邊與最右邊-緩衝值之間 1.最左邊+緩衝值 2.最右邊-緩衝值  
        #=====
        if left_bound <= px <= left_bound + self.buffer:  
            self.search_direction = "RIGHT"
            # print(f"人物位置:{px} 左側極值:{left_bound }")
            return self._pack_action("MOVE", direction="RIGHT")


        elif right_bound - self.buffer <= px <= right_bound:  
            self.search_direction = "LEFT"    # 走到底左轉
            # print(f"人物位置:{px} 右邊側極值:{right_bound}")
            return self._pack_action("MOVE", direction="LEFT")


        elif px < left_bound:
            self.search_direction = "RIGHT"  
            return self._pack_action("MOVE", direction="RIGHT")


        elif px > right_bound:
            self.search_direction = "LEFT"    
            return self._pack_action("MOVE", direction="LEFT")

        # 其他中間情況
        else:
            return self._pack_action("MOVE", direction=self.search_direction)
        
    def _fk_that_mob(self,state):
        '''
        功能:
            計算與怪物距離，判斷目標並攻擊
        '''
        # 依賴檢查：無平台資訊就拋棄此幀
        if not state.player_center_loc:
            return None, None
        if state.roi_BBOX is None:
            return None, None
        px, _ = state.player_center_loc

        # -- 計算最近的怪物
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
        # print("沒有目標在攻擊範圍內")

        # if self.current_platform is None: # <- 人物不在平台範圍，就終止移動
        #     return self._pack_action("IDLE",command="STOP_MOVE")
        
        left_bound,right_bound = self.platforms[self.current_platform]["t_l"][0],self.platforms[self.current_platform]["b_r"][0]
        # print(f"人物位置:{px} 左側極值:{left_bound } 右邊側極值:{right_bound}")
        if  px <= left_bound + self.buffer:  
            self.search_direction = "RIGHT"
            # print(f"人物位置:{px} 左側極值:{left_bound }")
            return self._pack_action("MOVE", direction="RIGHT")


        elif right_bound - self.buffer <= px :  
            self.search_direction = "LEFT"    # 走到底左轉
            # print(f"人物位置:{px} 右邊側極值:{right_bound}")
            return self._pack_action("MOVE", direction="LEFT")
        
        # -- 移動到最近的怪物
        return self._pack_action("MOVE", direction=best_target['direction']) 

    def _verti_movement(self,index):
        """
        功能:
            垂直移動邏輯
        行為:
            1. 判斷往上/往下
            2.偵測左走抓繩/右走抓繩
        """

        # -- 時間計算
        if self._verti_movement_timer is None:
            self._verti_movement_timer = time.time()
        current_time = time.time()
        # -- 數據計算
        current_verti_passage = self.vertical_passage[index]
        px, py = self.mini_player_loc

        top = current_verti_passage["t_l"][1]
        bottom = current_verti_passage["b_r"][1]
        mid_y = (top + bottom) // 2
        central_axis = current_verti_passage["t_l"][0] + (current_verti_passage["b_r"][0] - current_verti_passage["t_l"][0]) // 2

        # -- 固定上下的方向
        if self.current_verti_target is None:
            self.current_verti_target = "UP" if py > mid_y else "DOWN"

        #容忍值
        TOP_TOLERANCE = 5
        BOTTOM_TOLERANCE = 5
        # -- 決策邏輯
        # -- 往上        
        if self.current_verti_target == "UP":
            # 下面兩個if，目的為判斷有沒有成功到頂(底)部
            if self._is_loc_y_change(): # <= - 有變動則重置
                self._verti_movement_timer = current_time
            if  current_time - self._verti_movement_timer > VERTI_MOVE_STAY_TIMEOUT:
                '''
                條件A:超過X秒，判斷人物是否Y軸移動，沒移動代表在頂部
                '''
                #到達底部，重置狀態
                if not self._is_loc_y_change(): #< - 偵測是否移動
                    self.current_verti_target = None # < - 離開要重置
                    self._verti_movement_timer = None
                    self.last_player_loc = None
                    print("到達底部")
                    return self._pack_action("IDLE", command="RELEASE_ALL")
            
            #條件 : 人物處於下層區與 且 y軸沒變動
            if  bottom - BOTTOM_TOLERANCE <= py <= bottom and not self._is_loc_y_change():

                if px <= central_axis :
                    print(f'方向:{self.current_verti_target}，找繩子')
                    return self._pack_action("ROPE", direction="RIGHT_UP")
                elif px >= central_axis :
                    print(f'方向:{self.current_verti_target}，找繩子')
                    return self._pack_action("ROPE", direction="LEFT_UP")

            print(f'方向:{self.current_verti_target}，攀爬中')
            return self._pack_action("CLIMB", direction=self.current_verti_target)
        
        # -- 往下
        if self.current_verti_target == "DOWN":
            if  current_time - self._verti_movement_timer > 2:
                '''
                條件A:超過X秒，判斷人物是否Y軸移動，沒移動代表在頂部
                    '''
                # 下面兩個if，目的為判斷有沒有成功到頂(底)部
                if self._is_loc_y_change(): # <= - 有變動則重置
                    self._verti_movement_timer = current_time

                #到達底部，重置狀態
                if  current_time - self._verti_movement_timer > 2:
                    self.current_verti_target = None # < - 離開要重置
                    self._verti_movement_timer = None
                    self.last_player_loc = None
                    print("到達底部")
                    return self._pack_action("IDLE", command="RELEASE_ALL")
            
            if  top <= py <= top + TOP_TOLERANCE:
                #狀態改變:找繩子

                if px <= central_axis   :
                    print(f'向右，找往下繩子')
                    return self._pack_action("ROPE", direction="RIGHT_DOWN")
                elif px >= central_axis :
                    print(f'向左，找往下繩子')
                    return self._pack_action("ROPE", direction="LEFT_DOWN")

            print(f'方向:{self.current_verti_target}，攀爬中')
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        return None
    #=================
    # 分類: 狀態機判斷
    #=================

    def is_stuck(self):
        current_time = time.time()

        if self.last_player_loc is None:
            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return False

        if self.last_player_loc != self.mini_player_loc: #< -- 人物位置變化

            self.last_player_loc = self.mini_player_loc
            self.detect_move_stuck_timer = current_time
            return False 

        # 時間間隔（Threshold）判定
        if current_time - self.detect_move_stuck_timer > 1.5:
            return True
        return False

    def _check_vertical_passage(self) -> Optional[int]:
        '''
        功能:
            根據玩家目前的座標
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

                return index  

        return None

    def _check_current_platform(self):
        """
        功能:
            根據玩家目前的座標
            判斷人在哪一個平台內
        """
        if not self.mini_player_loc or not self.platforms:
            return None

        px, py = self.mini_player_loc 

        for index, plat in enumerate(self.platforms):
            left, top = plat["t_l"]     
            right, bottom = plat["b_r"] 

            if left <= px <= right and top <= py <= bottom:
                return index  

        return None

    def _check_climbing_up(self):
        '''
        功能:
            檢查是否在攀爬向上的狀態
        '''
        # -- 時間計算
        if self._verti_movement_timer is None:
            self._verti_movement_timer = time.time()
        current_time = time.time()
        if self._is_loc_y_change(): # <= - 有變動則重置
            self._verti_movement_timer = current_time
        #條件:超過X秒，判斷人物是否Y軸移動，沒移動代表在頂部
        if  current_time - self._verti_movement_timer > VERTI_MOVE_STAY_TIMEOUT :

            #到達底部，重置狀態
            if not self._is_loc_y_change(): #< - 偵測是否移動
                self.current_verti_target = None # < - 離開要重置
                self._verti_movement_timer = None
                self.last_player_loc = None
                print("到達頂部")
                return self._pack_action("IDLE", command="RELEASE_ALL")
        return self._pack_action("CLIMB", command="UP")


    #=================
    # 工具
    #=================
    def _pack_action(self, action_type, **kwargs):
        """
        將行為打包成字典
        """
        return action_type, kwargs

    def get_debug_geometry(self):
        '''
        給Gamebot的座標資料封包
        '''
        return [
            {"label": "platform", "color": (193,255,193),   "boxes": [(p["t_l"], p["b_r"]) for p in self.platforms]},
            {"label": "vertical_passage", "color": (0,100,0), "boxes": [(v["t_l"], v["b_r"]) for v in self.vertical_passage]},
            {"label": "jump", "color": (3,193,69), "circle": [j["loc"] for j in self.jump_points]}
        ]
    def _reset_state(self):
        '''
        從狀態機發出的重置按鍵指令
        '''
        return self._pack_action("IDLE",command="RELEASE_ALL")