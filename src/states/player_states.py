import src.action.KeyBoardController as kb

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
            print(f"[狀態切換] 當前狀態變更為: {self.current_state}")

        # 根據不同的狀態，讓 States 直接指揮 Input 發動鍵盤指令
        if self.current_state == "ATTACK":
            print(">>> 發送攻擊按鍵！")
            self.keyboard.attack_act() # 實際呼叫鍵盤模組
            
        elif self.current_state == "APPROACH" and target_info:
            direction = target_info.get("direction")
            print(f">>> [States 觸發 Input] 往 {direction} 方向移動！")
            if direction == "LEFT":
                self.keyboard.move_left()
            else:
                self.keyboard.move_right()
            
        elif self.current_state == "IDLE":
            # 什麼都不用按，或是放開按鍵
            pass