def execute_behavior(self, new_state, target_info=None):
    if self.current_state != new_state:
        self.current_state = new_state
        print(f"狀態更新為: {self.current_state}")

    if self.current_state == "ATTACK":
        direction = target_info.get("direction") if target_info else None
        # 進入攻擊範圍時，停止移動並發動攻擊
        self.keyboard.stop_move()
        self.keyboard.enable_attack(direction)

    elif self.current_state == "APPROACH" and target_info:
        direction = target_info.get("direction")

        # 移動指令會在底層持續按住，直到方向改變或進入 ATTACK 狀態
        if direction == "LEFT":
            self.keyboard.enable_move_left()
        elif direction == "RIGHT":
            self.keyboard.enable_move_right()

        self.keyboard.enable_pick_up()
        
    elif self.current_state == "IDLE":
        self.keyboard.stop_move()

    elif self.current_state.startswith("HEAL") and target_info:
        key = target_info.get("key")
        if key:
            self.keyboard.enable_use_item(key)
        else:
            logging.info(f"{self.current_state} 觸發，但該觸發值還沒設定按鍵")
    else:
        self.keyboard.enable_pick_up()


            self._status_attack = False
    self._current_move = None  # 紀錄當前按住的方向 ("LEFT", "RIGHT" 或 None)
    self._status_item = False  
    self._pick_up = False

    # key value
    self.attack_key = config.get("keyboard.attack")
    self.left_key = config.get("keyboard.left")
    self.right_key = config.get("keyboard.right")
    self._pick_up_key = config.get("keyboard.pick_up")

''' 攻擊行為 '''

def _attack_command(self, direction):
    try: 
        key = self.right_key if direction == "RIGHT" else self.left_key
        interception.key_down(key)
        interception.key_up(key)
        interception.key_down(self.attack_key)
        time.sleep(0.3)
    except Exception as e:
        logging.error(f"攻擊行為發生錯誤:{e}")
        
    finally:
        interception.key_up(self.attack_key)
        with self._attack_lock:
            self._status_attack = False

def enable_attack(self, direction):
    with self._attack_lock:
        if self._status_attack:
            return
        self._status_attack = True
        threading.Thread(target=self._attack_command, args=(direction,), daemon=True).start() 

''' 移動行為（長按狀態控制，流暢走動不卡頓） '''

def enable_move_left(self):
    with self._move_lock:
        if self._current_move == "LEFT":
            return  # 已經在向左走，不重複發送指令
        if self._current_move == "RIGHT":
            interception.key_up(self.right_key)
        interception.key_down(self.left_key)
        self._current_move = "LEFT"

def enable_move_right(self):
    with self._move_lock:
        if self._current_move == "RIGHT":
            return  # 已經在向右走，不重複發送指令
        if self._current_move == "LEFT":
            interception.key_up(self.left_key)
        interception.key_down(self.right_key)
        self._current_move = "RIGHT"

''' 停止釋放 '''

def stop_move(self):
    with self._move_lock:
        if self._current_move is not None:
            try:
                interception.key_up(self.left_key)
                interception.key_up(self.right_key)
            except Exception as e:
                logging.error(f"釋放移動發生錯誤:{e}")
            finally:
                self._current_move = None

def release_all(self):
    self.stop_move()

''' 物品使用行為 '''

def _item_command(self, key):
    try:
        interception.key_down(key)
        time.sleep(3)
    except Exception as e:
        logging.error(f"使用物品發生錯誤:{e}")
    finally:
        interception.key_up(key)
        with self._item_lock:
            self._status_item = False

def enable_use_item(self, key):
    if not key:
        return
    with self._item_lock:
        if self._status_item:
            return
        self._status_item = True
        threading.Thread(target=self._item_command, args=(key,), daemon=True).start()

''' 撿拾行為（修正線程防爆） '''

def _pick_up_command(self, key):
    try:
        interception.key_down(key)
        time.sleep(0.05)
    except Exception as e:
        logging.error(f"撿拾命令發生錯誤:{e}")
    finally:
        interception.key_up(key)
        with self._pick_up_lock:
            self._pick_up = False

def enable_pick_up(self):
    with self._pick_up_lock:
        if not self._pick_up_key or self._pick_up:
            return
        self._pick_up = True
    threading.Thread(target=self._pick_up_command, args=(self._pick_up_key,), daemon=True).start()