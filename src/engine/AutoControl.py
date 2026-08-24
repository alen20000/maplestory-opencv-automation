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
class AutoControl:
    def __init__(self):

        #---[實例化]
        self.health_manager = HealthManager()
        self.bot_state = BotState(self) # 把自己(AutoControl)交給狀態機當 owner，讓狀態機能反過來呼叫函式或共用資料

        #---[外部參數&設定]
        self.buffer = config.get("auto_control_config.buffer", 0) # <-- 邊界距離緩衝(平台的邊界距離+緩衝距離)
        self.verti_move_threshold = config.get("auto_control_config.verti_move_threshold",10)

        #---[內部參數&設定]
        self.search_direction = random.choice(["LEFT", "RIGHT"]) #<-- 巡邏方向;第一次初始化隨機方向

        #---[座標用容器]
        self.recored_data = []#<-- 所有行為點的容器
        self.platforms = [] #<-- 所有平台
        self.vertical_passage = [] #<-- 所有垂直通道
        self.current_platform = None #<-- 當前人物所在的平台
        self.current_vertical_passage = None #<-- 當前人物所在的垂直通道
        self.mini_player_loc = None #<-- 當前人物位置(小地圖)
        self.last_player_loc = None #<-- 上次人物位置(小地圖)
        self.current_verti_target = None #<-- 當前垂直通道目標方向

        #---[定時器]
        self.detect_move_stuck_timer = 0 #<--移動卡住計時器

        #States
        self.is_climbing_state = False #在爬樓梯狀態
        self.is_finding_rope_state =False #找繩子狀態
        self.is_combat_state = True #戰鬥狀態
        # Loadding Config
        self._load_map_data()
        # Parameters
        self.player_attack_range = config.get("player_setting.auto_control_config.attack_range")


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
                logging.info(f"{map_name}地圖載入完成，平台數量:{len(self.platforms)},垂直通道數量:{len(self.vertical_passage)}")
                print(f"{map_name}地圖載入完成\n平台數量:{len(self.platforms)}\n垂直通道數量:{len(self.vertical_passage)}")
        except Exception as e:
            logging.error(f"載入地圖失敗{e}")
    #=================
    # 功能:地圖解析
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

                top = current["loc"][1] - 5   #向上偏移:5
                bottom = current["loc"][1]  + 5  #向下偏移:3
                left = min(current["loc"][0], next_item["loc"][0])
                right = max(current["loc"][0], next_item["loc"][0]) 

                platforms.append({"t_l":(left,top),"b_r":(right,bottom)})
                i += 2
            else:
                i += 1 

        return platforms
    
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
        self.health_manager.run(state.player_hp,state.player_mp,current_time)

        # state 資料給狀態機，回傳值在拆解為 action ,params ，並回傳給Gamebot模組
        action, params = self.bot_state.handle(state)   

        return action, params 

    '''
    功能塊: 感知函式 
    '''
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
    



    #=================
    # 邏輯塊: 脫困功能
    #=================

    def _unstuck_player(self):
        '''
        功能:
            人物超出範圍、人物不動時、觸發防卡邏輯(這裡的移動是左右直走，還是有可能卡死)
        '''
        # 更新一下目前在哪一個平台
        self.current_platform = self._check_current_platform()

        if self.current_platform is None:
            #移動至最近平台
            result = self._find_nearest_platform()
            if result is not None:

                result = self._move_to_platform(result)
                print(f"移動至最近平台結果:{result}")
                return result
            else:
                return None, None
            
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

            # (1) 防卡監測
            stuck_action =self._detect_move_stuck()
            if stuck_action is not None:
                return stuck_action

            # (2) 主邏輯
            if px < self.platforms[platform_index]["t_l"][0]:
                return self._pack_action("MOVE", direction="RIGHT")
            else:
                return self._pack_action("MOVE", direction="LEFT")
        return None
    
    def _detect_move_stuck(self):
        ''' 
        檢測:
            人物是否卡住沒有移動
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

    #=================
    # 邏輯塊: 垂直通道
    #=================

    def _verti_movement(self,index):
        """
        功能:
            垂直移動邏輯
        行為:
            1. 判斷往上/往下
            2.偵測左走抓繩/右走抓繩
        """

        current_verti_passage = self.vertical_passage[index]

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

        #容忍值
        trigger_tolerance = 3

        if self.current_verti_target == "UP":

            if  py <= top :
                print("到達頂部，重置狀態")
                self._exit_verti()
                return self._pack_action("IDL", direction="RELEASE_ALL")
            
            #行為:找方向跳抓繩子
            if self.current_verti_target == "UP" and  bottom - trigger_tolerance <= py <= bottom :

                #狀態改變:找繩子
                self.is_finding_rope_state = True

                if px <= central_axis :
                    print(f'方向:{self.current_verti_target}，找繩子')
                    return self._pack_action("ROPE", direction="RIGHT_UP")
                elif px >= central_axis :
                    print(f'方向:{self.current_verti_target}，找繩子')
                    return self._pack_action("ROPE", direction="LEFT_UP")

            # 其餘情況全部視為爬行中
            if self.is_finding_rope_state:
                self.is_finding_rope_state = False
            self.is_climbing_state = True
            print(f'方向:{self.current_verti_target}，爬繩子中。。。')
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        if self.current_verti_target == "DOWN":
            if self.current_verti_target == "DOWN" and py >= bottom:
                #到達底部，重置狀態
                print("到達底部")
                self._exit_verti()
                return self._pack_action("IDL", direction="RELEASE_ALL")
            
            if top <= py <= top + trigger_tolerance:
                #狀態改變:找繩子
                self.is_finding_rope_state = True

                if px <= central_axis :
                    print(f'方向:{self.current_verti_target}，找繩子')
                    return self._pack_action("ROPE", direction="RIGHT_DOWN")
                elif px >= central_axis :
                    print(f'方向:{self.current_verti_target}，找繩子')
                    return self._pack_action("ROPE", direction="LEFT_DOWN")

            # 其餘情況全部視為爬行中
            if self.is_finding_rope_state:
                self.is_finding_rope_state = False
            self.is_climbing_state = True
            print(f'方向:{self.current_verti_target}，爬繩子中。。。')
            return self._pack_action("CLIMB", direction=self.current_verti_target)

        return None
    def _enter_verti(self):
        '''
        功能:進入通道前，狀態改變
            關閉:巡邏、打怪
        '''
        self.patrol_active = False   
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
    # 邏輯塊: 垂直移動相關
    #=================

    def _find_nearest_verti_passage(self) -> Optional[int]:
        """
        功能:
            先找目前平台內最近的垂直通道
        return: 
            平台引所對應的index 
        """
        if not self.mini_player_loc or not self.vertical_passage:
            return None
        #更新一下目前在哪一個平台，沒有平台就會進入全域找通道
        self.current_platform = self._check_current_platform()

        px, py = self.mini_player_loc

        # 先試著找「跟目前平台 x 範圍有重疊」的通道，這些是人物可移動到的
        reachable_candidates = []

        if self.current_platform:

            plat = self.platforms[self.current_platform]
            #取出 plat 的 t_l b_r點
            plat_left, plat_right = plat["t_l"][0], plat["b_r"][0]
            plat_top, plat_bottom = plat["t_l"][1], plat["b_r"][1] 

            for index, passage in enumerate(self.vertical_passage):
                p_left, p_right = passage["t_l"][0], passage["b_r"][0]
                p_top, p_bottom = passage["t_l"][1], passage["b_r"][1]

                x_overlap = not (p_right < plat_left or p_left > plat_right)
                y_touch = (plat_top <= p_top <= plat_bottom) or (plat_top <= p_bottom <= plat_bottom)

                if x_overlap and y_touch:
                    reachable_candidates.append(index)

        # 如果有找到能走到的候選，只在這些裡面挑最近的，沒有的話才找全部
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
        功能:控制人物移動到目標垂直通道
        arges: 
            verti_passage_index: 垂直通道的index
        return:
            self._pack_action("MOVE", direction="RIGHT"or "LEFT")
        '''
        px , _ = self.mini_player_loc

        # (1) 防卡監測
        stuck_action =self._detect_move_stuck()
        if stuck_action is not None:
            return stuck_action
        
        # (2) 主邏輯
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
        return action_type, kwargs

    def get_debug_geometry(self):
        '''
        給Gamebot的座標資料封包
        '''
        return [
            {"label": "platform", "color": (193,255,193),   "boxes": [(p["t_l"], p["b_r"]) for p in self.platforms]},
            {"label": "vertical_passage", "color": (0,100,0), "boxes": [(v["t_l"], v["b_r"]) for v in self.vertical_passage]},
        ]

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
        print(f"狀態:巡邏中...平台:{self.current_platform+1}")
        px, _ = self.mini_player_loc

        plat_index = self.current_platform
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
            #debug
            # print(f"目標 [{best_target['name']}] 在攻擊範圍內 距離: {best_target['distance']} 方向: {best_target['direction']}")
            return "ATTACK" , best_target
        print("沒有目標在攻擊範圍內")
        return None, None 

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