
from config.config_loader import config
from abc import ABC, abstractmethod
import time

class State(ABC):
    #強制約束方法
    @abstractmethod
    def handle(self, context, state_data):
        pass


class PatrolState(State):

    TIMEOUT = config.get("auto_control_config.find_mob_time_threshold") # <-- 平台巡邏超過幾秒，結束巡邏，進入下一個狀態
    
    def __init__(self):
        self.patrolling_timer = time.time() # <-- 記錄「巡邏時間」的時間戳
        self.TOGGLE_PATROL_ACTION = config.get("auto_control_config.TOGGLE_PATROL_ACTION") # <-- 是否切換巡邏動作
        self.TOGGLE_COMBAT_ACTION = config.get("auto_control_config.TOGGLE_COMBAT_ACTION") # <-- 是否切換戰鬥動作
    def handle(self, context, state_data):
        # print("狀態:平台巡邏...")

        # 條件A:如果有怪物，切換為戰鬥狀態
        if state_data.mobs and self.TOGGLE_COMBAT_ACTION:
            context.change_state(CombatState())
            return None, None
        
        # 條件B:人物座標沒動,超過一定時間,切換為檢查狀態
        elif context.is_stuck():

            context.change_state(StuckState())
            return None, None

        # 條件C:超過一定時間,切換為尋路狀態(爬繩、跳躍點、etc..)
        elif time.time() - self.patrolling_timer > PatrolState.TIMEOUT:
            context.change_state(PathfindState())
            return None, None
        
        # 沒怪就繼續原本的巡邏動作
        if self.TOGGLE_PATROL_ACTION :
            return context._enable_player_patrol()
    
class CombatState(State):


    def __init__(self):
        pass

    def handle(self, context, state_data):
        print("狀態:進入戰鬥...")

        # 有怪，打怪
        if state_data.mobs:
            return context._fk_that_mob(state_data)
        else:
            context.change_state(PatrolState())
            return None, None
        


class StuckState(State):
    STUCK_TIMEOUT = 1
    def __init__(self):
        self.stuck_timer = time.time()

    def handle(self, context, state_data):

        print("狀態:檢查角色是否卡頓...")
        if time.time() - self.stuck_timer > StuckState.STUCK_TIMEOUT:
            context.reset_state()
            return None, None
        return context._unstuck_player(state_data)   

class PathfindState(State):
    '''
    這裡分流移動的方法: 繩子、跳躍之類的
    '''
    def __init__(self):
        pass
    def handle(self, context, state_data):
        if context._check_current_platform() is not None or context._check_vertical_passage() is not None:
            print("偵測在平台內，轉到到爬繩狀態")
            context.change_state(RopeState())
            return None, None
class RopeState(State):

    def __init__(self):
        pass

    def handle(self, context, state_data):

        # 先判斷人物現在是不是已經站在垂直通道範圍內
        current_passage_index = context._check_vertical_passage()
        current_play_indx =context._check_current_platform()
        print(f"目前所在平台: {current_play_indx}號平台;所在垂直通道: {current_passage_index}號通道")

        # 如果不在垂直通道內，去找最近的垂直通道
        if current_passage_index is None:  
            next_rope_index = context._find_nearest_verti_passage()
            if next_rope_index != current_passage_index:
                return context._move_to_verti_passage(next_rope_index)
            
        elif current_passage_index is not None: # <-若在垂直通道內
            action, params = context._verti_movement(current_passage_index)
            #到達通到盡頭，觸發IDL，重置狀態
            if action == "IDLE":
                context.change_state(PatrolState())
            return action, params



class BotState():
    '''
    state manager    
    '''
    def __init__(self,owner):
        self.owner = owner
        self.initial_state_cls = PatrolState   # <-- 初始狀態的「類別」

        self.current_state = self.initial_state_cls()

    def change_state(self, new_state):
        print(f"[狀態切換] {self.current_state.__class__.__name__} -> {new_state.__class__.__name__}")
        self.current_state = new_state

    def reset_state(self):
        '''重製回預設初始狀「類別」'''

        self.change_state(self.initial_state_cls())
        return self._reset_state()
    #調用
    def handle(self, state_data):
        result = self.current_state.handle(self, state_data)

        # 統一防呆:若缺一個None，就補一個None 
        if result is None:
            return None, None
        return result

    #====借殼用函式
    def _enable_player_patrol(self):
        return self.owner._enable_player_patrol()

    def _fk_that_mob(self, state_data):
        return self.owner._fk_that_mob(state_data)
    
    def _unstuck_player(self, state_data):
        return self.owner._unstuck_player()
    
    def is_stuck(self):
        return self.owner.is_stuck()

    def _check_vertical_passage(self):
        return self.owner._check_vertical_passage()

    def _find_nearest_verti_passage(self):
            return self.owner._find_nearest_verti_passage()

    def  _move_to_verti_passage(self,index):
            return self.owner._move_to_verti_passage(index)

    def _verti_movement(self,index):
            return self.owner._verti_movement(index)
    def _check_current_platform(self):
            return self.owner._check_current_platform()
    def _reset_state(self):
            return self.owner._reset_state()
    #====小工具
