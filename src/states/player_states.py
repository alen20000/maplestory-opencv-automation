import src.action.KeyBoardController as kb
'''
行為模式: ATTACK 、 APPROACH 、 IDLE
ATTACK: 攻擊命令
APPROACH: 追蹤命令，下達左右前進命令
IDEL: 空狀態，常駐撿拾命令
'''
class PlayerStates:
    def __init__(self):
        # 初始化預設狀態

        self.current_state = "IDLE"  
        #instance
        self.keyboard = kb.KeyBoard()

    def update_and_execute(self, new_state, target_info=None):
        """
        1. 接收 Bot 傳來的狀態並更新
        2. 根據狀態直接發送指令給 Input (鍵盤)
        """
        if self.current_state != new_state:
            self.current_state = new_state
            print(f"狀態更新為: {self.current_state}")
        if self.current_state == "ATTACK":

            self.keyboard.enable_attack()
            print("攻擊")
        elif self.current_state == "APPROACH" and target_info:
            direction = target_info.get("direction")
            print(f"前進方向: {direction}")
            if direction == "LEFT":
                self.keyboard.enable_move_left()
            else:
                self.keyboard.enable_move_right()
            
        elif self.current_state == "IDLE":
            # 空狀態不做任何動作
            pass