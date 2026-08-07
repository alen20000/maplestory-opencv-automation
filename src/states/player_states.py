class PlayerStates:
    def __init__(self):
        # 初始化預設狀態
        self.current_state = "IDLE"  # 可能的值: "IDLE", "COMBAT", "LOOTING"

    def decide_state(self, has_mobs: bool, enable_pick: bool) -> str:
        """
        根據當前環境條件，決定並切換狀態
        """
        if has_mobs:
            self.current_state = "COMBAT"
        elif enable_pick:
            self.current_state = "LOOTING"
        else:
            self.current_state = "IDLE"
            
        return self.current_state