import src.action.KeyBoardController as kb
import logging  
'''
行為模式: ATTACK 、 APPROACH 、 IDLE
ATTACK: 攻擊命令
APPROACH: 追蹤命令，下達左右前進命令
IDEL: 空狀態
撿拾命命，先用外部腳本

'''
class PlayerStates:
    def __init__(self):
        # 初始化預設狀態

        self.current_state = "IDLE"  
        #instance
        self.keyboard = kb.KeyBoard()

    def execute_behavior(self, new_state, target_info=None):
        """
        負責以狀態變更而進行的指令
        args:
            new_state (str): 新的狀態
            target_info (dict):  {"name": mob, "distance": distance, "direction": direction}
        """
        # 更新狀態
        if self.current_state != new_state:
            self.current_state = new_state
            print(f"狀態更新為: {self.current_state}")

        # 根據狀態發送指令
        if self.current_state == "ATTACK":
            # 停止移動
            direction = target_info.get("direction")
            self.keyboard._stop_move()

            self.keyboard.enable_attack(direction)

        elif self.current_state == "ROPE" and target_info:

            direction = target_info.get("direction")
            if direction == "LEFT_UP":
                self.keyboard._stop_move()
                self.keyboard.grab_rope_to_left()
            elif direction == "RIGHT_UP":
                self.keyboard._stop_move()
                self.keyboard.grab_rope_to_right()
            elif direction == "LEFT_DOWN":
                self.keyboard.move_down_to_left()
            elif direction == "RIGHT_DOWN":
                self.keyboard.move_down_to_right()
            elif direction =="UP":
                self.keyboard.enable_up(duration=3)

        elif self.current_state == "MOVE" and target_info:
            direction = target_info.get("direction")

            if direction == "LEFT":
                self.keyboard.enable_move_left()
            elif direction == "RIGHT":
                self.keyboard.enable_move_right()
            self.keyboard.enable_pick_up()
            
        elif self.current_state == "IDLE":
            self.keyboard.release_all()
            # 人物閒置狀態
            pass

        #放後面點，閒置就不喝水
        elif self.current_state.startswith("HEAL") and target_info:
            #健康修復狀態
            key = target_info.get("key")
            if key:
                self.keyboard.enable_use_item(key)
            else:
                logging.info(f"{self.current_state} 觸發，但該該處發值還沒設定按鍵")
                pass
        else:
            self.keyboard.enable_pick_up()

    def tobe_IDEL(self):

        self.current_state = "IDLE"
        self.keyboard.release_all()
