
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
        self.stuck_check_timer = time.time()
    def handle(self, context, state_data):
        # print("狀態:平台巡邏...")

        # 條件A:如果有怪物，切換為戰鬥狀態
        if state_data.mobs and self.TOGGLE_COMBAT_ACTION:
            context.change_state(CombatState())
            return None, None
        
        # 條件B:人物座標沒動,超過一定時間,切換為檢查狀態
        elif time.time() - self.stuck_check_timer >= 3:
            self.stuck_check_timer = time.time()
            if context.is_stuck():
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
        if not state_data.mobs:
            context.change_state(PatrolState())
            return None, None
        action, params = context._fk_that_mob(state_data)
        
        return action, params 
        


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
    ((預留))
    這裡分流移動的方法: 繩子、跳躍之類的
    '''
    def __init__(self):
        pass
    def handle(self, context, state_data):

        # 條件A:偵測到鄰近的跳躍點
        nearest_jump_index = context._find_nearest_jump_point()
        if nearest_jump_index is not None:
            print(f"偵測到鄰近的{nearest_jump_index}號跳躍點，轉換到跳躍狀態")
            context.change_state(JumpState(nearest_jump_index))
            return None, None
        # 條件B: 偵測平台內垂直通道
        if context._check_current_platform() is not None or context._check_vertical_passage() is not None:
            print("偵測在平台內，轉到到爬繩狀態")
            context.change_state(RopeState())
            return None, None
        
        # 其餘: 重置 
        context.reset_state()
        return None, None


class JumpState(State):
    '''
    功能:
        負責走到指定的單點跳躍座標(YAML中紀錄的 JumpLeft / JumpRight)，
        抵達後依紀錄的方向執行單次跳躍。
    '''
    TIMEOUT = 3  # <-- 保險機制:太久走不到跳躍點就放棄，避免卡死在這個狀態

    def __init__(self, jump_index):
        self.jump_index = jump_index
        self.start_time = time.time()

    def handle(self, context, state_data):
        print(f"狀態:前往{self.jump_index}號跳躍點...")

        # 逾時保護:走太久還沒到，放棄本次跳躍，回到巡邏重新判斷
        if time.time() - self.start_time > JumpState.TIMEOUT:
            print("前往跳躍點逾時，放棄本次跳躍")
            context.reset_state()
            return None, None

        current_jump_index = context._check_jump_point()

        # 已經站在目標跳躍點上，執行跳躍動作
        if current_jump_index == self.jump_index:
            action, params = context._do_jump(self.jump_index)
            context.reset_state()
            return action, params

        # 還沒抵達，繼續往跳躍點方向移動
        return context._move_to_jump_point(self.jump_index)
    
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
                context.reset_state()
                nearest_jump_index = context._find_nearest_jump_point()
                if nearest_jump_index is not None:
                    context.change_state(PathfindState())
                        
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
    
    #====單點跳躍(JumpLeft/JumpRight)相關借殼

    def _check_jump_point(self):
            return self.owner._check_jump_point()

    def _find_nearest_jump_point(self):
            return self.owner._find_nearest_jump_point()

    def _move_to_jump_point(self, jump_index):
            return self.owner._move_to_jump_point(jump_index)

    def _do_jump(self, jump_index):
            return self.owner._do_jump(jump_index)
    

