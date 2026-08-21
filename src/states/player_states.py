import src.action.KeyBoardController as kb
import logging  
from config.config_loader import config
'''
行為模式: ATTACK 、 APPROACH 、 IDLE
ATTACK: 攻擊命令
APPROACH: 追蹤命令，下達左右前進命令
IDEL: 空狀態
撿拾命命，先用外部腳本

'''
class PlayerStates:
    def __init__(self):

        #State
        self.current_state = "IDLE"  
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
            direction = self.current_info.get("direction")
            logging.info(f"狀態更新為: {self.current_state} ；方向為: {direction}")

        # 判定"攻擊"狀態
        if self.current_state == "ATTACK":
            # 停止移動
            direction = self.current_info.get("direction")
            self.keyboard.stop_move()
            if self.is_Night_Lord:
                self.keyboard.enable_night_lord_attack(direction)
            else:
                self.keyboard.enable_attack(direction)

        # 判定"去爬繩"狀態
        elif self.current_state == "ROPE" and self.current_info:
            self.keyboard.stop_move()
            direction = self.current_info.get("direction")
            if direction == "LEFT_UP":
                # self.keyboard.release_all()
                self.keyboard.grab_rope_to_left()
            elif direction == "RIGHT_UP":
                # self.keyboard.release_all()
                self.keyboard.grab_rope_to_right()
            elif direction == "LEFT_DOWN":
                self.keyboard.release_all()
                self.keyboard.move_down_left()
            elif direction == "RIGHT_DOWN":
                self.keyboard.release_all()
                self.keyboard.move_down_right()  

            elif direction =="UP":
                # self.keyboard.release_all()
                self.keyboard.enable_up(duration=1)
                self.keyboard.enable_jump()
            elif direction == "DOWN":
                # self.keyboard.release_all()
                self.keyboard.enable_down(duration=1)
                


        # 判定"攀爬中"狀態

        elif self.current_state == "CLIMB" :
            self.keyboard.stop_move()
            direction = self.current_info.get("direction")
            # distance = self.current_info.get("distance")
            if direction == "UP":
                self.keyboard.climb_up()
            elif direction == "DOWN":
                self.keyboard.climb_down()

            

        elif self.current_state == "MOVE" and self.current_info:
            direction = self.current_info.get("direction")

            if direction == "LEFT":
                self.keyboard.enable_move_left()
            elif direction == "RIGHT":
                self.keyboard.enable_move_right()
            self.keyboard.enable_pick_up()
            
        elif self.current_state == "IDLE" and self.current_info:
            command = self.current_info.get("command")
            if command == "STOP_MOVE":
                print("停止移動")
                # 停止移動
                self.keyboard.stop_move()

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


if __name__ == "__main__":
    run = PlayerStates()
    print(run.is_Night_Lord)