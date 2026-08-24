
from config.config_loader import config
from abc import ABC, abstractmethod
import time

class State(ABC):
    #強制約束方法
    @abstractmethod
    def handle(self, context, state_data):
        pass


class PatrolState(State):

    TIMEOUT = 3 # <-- 平台巡邏超過幾秒，結束巡邏，進入下一個狀態

    def __init__(self):
        self.patrolling_timer = time.time() # <-- 記錄「巡邏時間」的時間戳

    def handle(self, context, state_data):
        print("狀態:平台巡邏...")

        # 如果有怪物，切換為戰鬥狀態
        if state_data.mobs:
            context.change_state(CombatState())
            return None, None
        # if time.time() - self.patrolling_timer > PatrolState.TIMEOUT:
        #     context.change_state(CombatState())
        #     return None, None
        # 沒怪就繼續原本的巡邏動作
        return context._enable_player_patrol()
    
class CombatState(State):

    LOST_TARGET_TIMEOUT = 0.5 # <-- 找不到怪超過幾秒，才切回巡邏
    def __init__(self):
        self.lost_target_timer = None # <-- 記錄「開始找不到怪」的時間戳

    def handle(self, context, state_data):
        print("狀態:進入戰鬥...")

        # 有怪，重置計時器，正常打怪
        if state_data.mobs:
            self.lost_target_timer = None
            return context._fk_that_mob(state_data)
        
        # 第一次沒看到怪，記錄時間戳
        if self.lost_target_timer is None:
            self.lost_target_timer = time.time()
            return None, None
        
        passed_time = time.time() - self.lost_target_timer
        print(f"已經{passed_time:.1f} 秒沒有看到怪物了...")

        #  超過預設時間，切回巡邏
        if passed_time > self.LOST_TARGET_TIMEOUT:
            print(f"已經{passed_time:.1f} 秒沒有看到怪物了，切回巡邏狀態")
            context.change_state(PatrolState())
            return None, None
        
        print(f"等待怪物出現中... ({int(passed_time)}秒")
        return None, None
    
class BotState():
    '''
    state manager    
    '''
    def __init__(self,owner):
        self.owner = owner
        self.current_state = PatrolState() #<-- 初始狀態是巡邏

    def change_state(self, new_state):
        print(f"[狀態切換] {self.current_state.__class__.__name__} -> {new_state.__class__.__name__}")
        self.current_state = new_state

    #調用
    def handle(self, state_data):
        result = self.current_state.handle(self, state_data)

        # 統一防呆:少傳Noe 則多補None 
        if result is None:
            return None, None
        return result

    #====借殼用函式
    def _enable_player_patrol(self):
        return self.owner._enable_player_patrol()

    def _fk_that_mob(self, state_data):
        return self.owner._fk_that_mob(state_data)