
from config.config_loader import config
from abc import ABC, abstractmethod
import time

class State(ABC):
    #強制約束方法
    @abstractmethod
    def handle(self, context, state_data):
        pass


class PatrolState(State):

    PATROL_TIMEOUT = config.get("auto_control_config.find_mob_time_threshold") # <-- 平台巡邏超過幾秒，結束巡邏，進入下一個狀態
    STUCK_CHECK_TIMEOUT = config.get("auto_control_config.stuck_check_time_threshold")
    def __init__(self):
        self.patrolling_timer = time.time() # <-- 記錄「巡邏時間」的時間戳
        self.TOGGLE_PATROL_ACTION = config.get("auto_control_config.TOGGLE_PATROL_ACTION") # <-- 是否切換巡邏動作
        self.TOGGLE_COMBAT_ACTION = config.get("auto_control_config.TOGGLE_COMBAT_ACTION") # <-- 是否切換戰鬥動作
        self.TOGGLE_Stuck_ACTION = config.get("auto_control_config.TOGGLE_Stuck_ACTION")
        self.stuck_check_timer = time.time()

    def handle(self, context, state_data):
        # print("狀態:平台巡邏...")

        # 條件A:如果有怪物，切換為戰鬥狀態
        if state_data.mobs and self.TOGGLE_COMBAT_ACTION:
            print("狀態:進入戰鬥...")
            context.change_state(CombatState())
            return None, None
        
        # 條件B:人物座標沒動,超過一定時間,切換為檢查狀態
        elif time.time() - self.stuck_check_timer >= PatrolState.STUCK_CHECK_TIMEOUT:
            self.stuck_check_timer = time.time()
            if context.is_stuck():
                context.change_state(StuckState())
                return None, None

        # 條件C:超過一定時間,切換為尋路狀態(爬繩、跳躍點、etc..)
        elif time.time() - self.patrolling_timer > PatrolState.PATROL_TIMEOUT:
            context.change_state(PathfindState())
            return None, None
        
        # 沒怪就繼續原本的巡邏動作
        if self.TOGGLE_PATROL_ACTION :
            return context._enable_player_patrol()
    
class CombatState(State):
    STUCK_CHECK_INTERVAL = 3

    def __init__(self):
        self.stuck_check_timer = time.time()

    def handle(self, context, state_data):

        if not state_data.mobs:
            context.reset_state()
            return None, None

        # 檢查角色是否卡頓
        if time.time() - self.stuck_check_timer >= self.STUCK_CHECK_INTERVAL: 
            self.stuck_check_timer = time.time()
            if context.is_stuck():
                context.change_state(StuckState())
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
    TIMEOUT = 5  # <-- 第一層保險機制:太久走不到跳躍點就放棄，避免卡死在這個狀態
    NEXT_TIMEOUT = 5 #<-- 第二層保險機制:連續跳躍判斷中的逾時時間上限
    AIR_TIME = 1.0  # 滯空等待時間

    def __init__(self, jump_index):
        self.jump_index = jump_index
        self.start_time = time.time()
        self.last_jump_index = None
        # Flag
        self.next_start_jump_time = None
        self.has_jumped = False
    def handle(self, context, state_data):

        now = time.time()
        # 逾時保護:走太久還沒到，放棄本次跳躍，回到巡邏重新判斷
        if now  - self.start_time > JumpState.TIMEOUT:
            print("前往跳躍點逾時，放棄本次跳躍")
            context.reset_state()
            return None, None

        print(f"狀態:前往{self.jump_index}號跳躍點...")
        current_jump_index = context._check_jump_point()

        # 情況 A：已經跳過了，檢查落下點是否還是為跳躍點
        if self.has_jumped:
            
            if now  - self.jump_start_time > self.AIR_TIME: # <- 放了一秒，因為角色跳在空中
                # 直接檢查現在腳下是不是跳躍點
                new_jump_index = context._check_jump_point()
                self.last_jump_index = new_jump_index # 紀錄上一次的跳躍點

                # 逾時保護:二次跳躍後的逾時保護
                if self.next_start_jump_time is not None and (now - self.next_start_jump_time > JumpState.NEXT_TIMEOUT):
                    print("前往跳躍點逾時，放棄本次跳躍")
                    context.change_state(ClimbState())
                    return None, None
                
                if new_jump_index is not None and self.last_jump_index != new_jump_index:

                    print(f"順利落到下一個跳躍點: {new_jump_index}，繼續留在 JumpState！")

                    
                    # 更新目標為當前腳下的新跳躍點，重設狀態繼續下一跳
                    self.jump_index = new_jump_index
                    self.start_time = now 
                    self.has_jumped = False
                    self.next_start_jump_time = now # < - 重製時間判斷，因為跳躍點可能是多個連續的
                    return None, None
                else:
                    print("落地後不在跳躍點上，連續跳躍結束，離開 JumpState")
                    context.change_state(ClimbState())
                    return None, None
            
            return None, None 
            
        # 情況 B：已經走到目標跳躍點上，執行跳躍】
        if current_jump_index == self.jump_index:
            print(f"到達 {self.jump_index} 號點，執行跳躍！")
            action, params = context._do_jump(self.jump_index)
            
            self.has_jumped = True
            self.jump_start_time = now   # 記錄起跳時間
            self.next_start_jump_tim = now # 這是給繼續跳的逾時保護基點
            return action, params
        
        # 情況C :還沒抵達，繼續往跳躍點方向移動
        return context._move_to_jump_point(self.jump_index)

class ClimbState(State):
    '''
    功能:
        會偵測Y軸變動狀態，重製按鍵。
        負責跳躍後爬繩，爬上去後若偵測到跳躍點則再次執行跳躍。
    '''
    TIMEOUT = 5  # 爬繩階段的逾時保護（避免卡在繩子上）

    def __init__(self):
        self.start_time = time.time()
        self.has_reached_rope = False

    def handle(self, context, state_data):
        now = time.time()
        
        # 1. 逾時保護：爬太久沒反應就放棄，重置狀態
        if now - self.start_time > ClimbState.TIMEOUT:
            print("爬繩/攀爬階段逾時，放棄並重置狀態")
            context.reset_state()
            return None, None

        print("狀態:跳躍後爬繩中...")
        
        # 2. 核心檢查：爬繩動作與狀態
        action, params = context._check_climbing_up()
        
        # 3. 檢查是否已經碰到/到達新的跳躍點
        new_jump_index = context._check_jump_point()
        
        if new_jump_index is not None:
            print(f"偵測到新跳躍點 ({new_jump_index})！切換回 JumpState 進行連續跳躍")
            # 切換狀態到 JumpState，並帶入新的 jump_index
            context.change_state(JumpState(new_jump_index))
            return None, None

        # 4. 判斷 IDLE 結束重置
        if action == "IDLE":
            print("攀爬結束，未發現新跳躍點，重置狀態")
            context.reset_state()
            
        return action, params
                
class RopeState(State):

    TIMEOUT = 60  # <-- 保險機制:1分鐘沒動，判斷卡死狀態

    def __init__(self):
        self.start_time = time.time()

    def handle(self, context, state_data):

        # 先判斷人物現在是不是已經站在垂直通道範圍內
        current_passage_index = context._check_vertical_passage()
        current_play_indx =context._check_current_platform()
        print(f"目前所在平台: {current_play_indx}號平台;所在垂直通道: {current_passage_index}號通道")

        # 逾時保護:走太久還沒到，放棄本次爬繩，回到巡邏重新判斷
        if time.time() - self.start_time > RopeState.TIMEOUT:
            print("前往爬繩逾時，放棄本次爬繩")
            context.reset_state()
            return None, None
        
        # 如果不在垂直通道內，去找最近的垂直通道
        if current_passage_index is None:  
            next_rope_index = context._find_nearest_verti_passage()

            if next_rope_index is None: # <-找不到就reset
                return context.reset_state()
            
            if next_rope_index != current_passage_index:
                return context._move_to_verti_passage(next_rope_index)

        elif current_passage_index is not None: # <-若在垂直通道內
            action, params = context._verti_movement(current_passage_index) # 垂直移動
            #到達通到盡頭，觸發IDL，重置狀態
            if action == "IDLE":
                context.reset_state()
                nearest_jump_index = context._find_nearest_jump_point()
                if nearest_jump_index is not None: # < -  (測試)爬繩到盡頭，找到跳躍點
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
    
    def _check_climbing_up(self):
            return self.owner._check_climbing_up()
    
    def _is_loc_y_change(self):
            return self.owner._is_loc_y_change()