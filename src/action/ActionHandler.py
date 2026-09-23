import src.action.KeyBoardController as kb
import logging  
from config.config_loader import config
import time
'''
命令分派器

'''
class ActionHandler:
    def __init__(self):

        #State
        self.current_state = "PRESET"  
        self.current_info = None
        #Instance
        self.keyboard = kb.KeyBoard()
        #Flag
        self.is_Night_Lord = config.get("player_setting.auto_control_config.is_Night_Lord") #<-- 是否為鏢賊

    def execute_behavior(self, new_state, target_info=None):
        """
        負責以狀態變更而進行的指令
        args:
            new_state (str): 新的狀態
            target_info (dict):  {"name": mob, "distance": distance, "direction": direction}
        """
        # 把持續狀態轉脈衝狀態，防止重複觸發
        if self.current_state != new_state or self.current_info != target_info:
            self.current_state = new_state
            self.current_info = target_info


        # 判定"攻擊"狀態
        if self.current_state == "ATTACK":
            '''
            Note: 判斷順序 -> 是否 AOE -> 跳打|普通攻擊 
            '''
            # 停止移動
            direction = self.current_info.get("direction")
            self.keyboard.stop_move()

            if direction == "AOE_ATTACK":
                print("AOE攻擊哦!")
                self.keyboard.enable_aoe_attack()

            if self.is_Night_Lord:
                self.keyboard.enable_night_lord_attack(direction)
            else:
                self.keyboard.enable_attack(direction)

        # ====
        # "爬繩"狀態命令
        # ====
        elif self.current_state == "ROPE" and self.current_info:

            direction = self.current_info.get("direction")

            if direction == "LEFT_UP":

                self.keyboard.grab_rope_to_left()
            elif direction == "RIGHT_UP":

                self.keyboard.grab_rope_to_right()
            elif direction == "LEFT_DOWN":

                self.keyboard.move_down_left()
            elif direction == "RIGHT_DOWN":

                self.keyboard.move_down_right()  

            elif direction =="UP":

                self.keyboard.enable_up(duration=1)
                self.keyboard.enable_jump()
            elif direction == "DOWN":

                self.keyboard.enable_down(duration=1)
                


        # ====
        # "攀爬"的狀態命令
        # ====
        elif self.current_state == "CLIMB" :
            direction = self.current_info.get("direction")
            if direction == "UP":
                self.keyboard.climb_up()
            elif direction == "DOWN":
                self.keyboard.climb_down()

        # ====
        # "持續位移"的狀態命令
        # ====
        elif self.current_state == "MOVE" and self.current_info:
            direction = self.current_info.get("direction")

            if direction == "LEFT":
                self.keyboard.enable_move_left()
            elif direction == "RIGHT":
                self.keyboard.enable_move_right()
                
            self.keyboard.enable_pick_up()


        # ====
        # "跳躍"的狀態命令
        # ====
        elif self.current_state == "JUMP":   
            direction = self.current_info.get("direction")
            if direction == "LEFT":

                self.keyboard.jump_left()
            elif direction == "RIGHT":
                self.keyboard.jump_right()

            elif direction =="NONE":  # <- 給平台移動時遇到障礙物的跳躍
                self.keyboard.enable_jump()

            elif direction == "DOWN": # <- 向下跳
                self.keyboard.jump_down()

        # ====
        # "短距離位移"的狀態命令
        # ====
        elif self.current_state == "SMALL_MOVE":
            direction = self.current_info.get("direction")
            if direction == "M2LEFT":
                self.keyboard.move_left_to_jump()# <- 跳抓狀態的短距離左側移動
            elif direction == "M2RIGHT":
                self.keyboard.move_right_to_jump()# <- 跳抓狀態的短距離右側移動


        # ====
        # "跳爬+跳抓"的狀態命令
        # ====
        elif self.current_state == "JUMP_GRAB":
            direction = self.current_info.get("direction")
            self.keyboard.stop_move()
            if direction == "LEFT": # <- 向左跳抓

                self.keyboard.jump_left_grab()
            elif direction == "RIGHT": # <- 向右跳抓

                self.keyboard.jump_right_grab()

            elif direction == "UP": # <- 向上跳抓
                self.keyboard.jump_up_grab()




        elif self.current_state == "IDLE" and self.current_info:
            command = self.current_info.get("command")
            if command == "STOP_MOVE":

                # 停止移動
                self.keyboard.stop_move()
            if command == "RELEASE_ALL":
                # 釋放所有熟鍵
                self.keyboard.stop_move()
                self.keyboard.release_all()

        # 判定"治癒"狀態
        elif self.current_state.startswith("HEAL") and self.current_info:
            #健康修復狀態
            key = self.current_info.get("key")
            if key:
                self.keyboard.enable_use_item(key)
            else:
                logging.info(f"{self.current_state} 觸發，但該該處發值還沒設定按鍵")
                pass
        else:
            self.keyboard.enable_pick_up()


