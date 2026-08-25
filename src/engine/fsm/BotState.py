
from config.config_loader import config
from abc import ABC, abstractmethod
import time

class State(ABC):
    #強制約束方法
    @abstractmethod
    def handle(self, context, state_data):
        pass


class PatrolState(State):

    TIMEOUT = 2 # <-- 平台巡邏超過幾秒，結束巡邏，進入下一個狀態

    def __init__(self):
        self.patrolling_timer = time.time() # <-- 記錄「巡邏時間」的時間戳

    def handle(self, context, state_data):
        # print("狀態:平台巡邏...")

        # 條件A:如果有怪物，切換為戰鬥狀態
        if state_data.mobs:
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
    STUCK_TIMEOUT = 3
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
    先把爬繩子弄好，再添加跳躍點、之類的其他命令
    '''
    def __init__(self):
        pass
    def handle(self, context, state_data):
        print("狀態:爬繩...")

        # 先判斷人物現在是不是已經站在垂直通道範圍內
        current_passage_index = context._check_vertical_passage()
        print(f"目前所在垂直通道: {current_passage_index}號通道")

        
        if current_passage_index is not None: # <-若在垂直通道內
            action, params = context._verti_movement(current_passage_index)
            #到達通到盡頭，觸發IDL，重置狀態
            if action == "IDLE":
                context.change_state(PatrolState())
            return action, params
        
        # 如果不在垂直通道內，去找最近的垂直通道
        next_rope_index = context._find_nearest_verti_passage()
        if next_rope_index is not None:  # <- 用 is not None，避免 index=0 被 if 判成 False
            return context._move_to_verti_passage(next_rope_index)
        else:

            context.change_state(PatrolState())
            return None, None

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
    #====小工具
