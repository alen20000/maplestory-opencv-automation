import time
import interception
import logging
from config.config_loader import config
import threading

class KeyBoard:
    def __init__(self):
        #捕捉與綁定滑鼠
        interception.auto_capture_devices(keyboard=True, mouse=True)
        #states
        self._attack_lock = threading.Lock()
        self._move_lock = threading.Lock()
        self._item_lock = threading.Lock()
        self._pick_up_lock = threading.Lock()  
        self._jump_lock = threading.Lock()
        self._status_attack = False
        self._status_jump = False

        self._status_item = False  
        self._pick_up = False
        #key value
        self.attack_key = config.get("keyboard.attack")
        self.up_key = config.get("keyboard.up")
        self.down_key = config.get("keyboard.down")
        self.left_key = config.get("keyboard.left")
        self.right_key = config.get("keyboard.right")
        self.pick_up_key = config.get("keyboard.pick_up")
        self.jump_key = config.get("keyboard.jump")
        #action logging
        self._current_move = None # <- 紀錄目前移動指令

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


    def enable_attack(self,direction):
        with self._attack_lock:
            if self._status_attack:
                #攻擊還在發生，不再傳輸攻擊指令
                return
            self._status_attack = True
            threading.Thread(target=self._attack_command,args=(direction,),daemon=True).start() 

    ''' 移動行為 '''

    def enable_move_right(self):
        with self._move_lock:
            if self._current_move == "RIGHT": #重複指令拋棄
                return
            if self._current_move == "LEFT":
                interception.key_up(self.left_key)
            interception.key_down(self.right_key)
            self._current_move = "RIGHT"

    def enable_move_left(self):
        with self._move_lock:
            if self._current_move == "LEFT":    #重複指令拋棄
                return
            if self._current_move == "RIGHT":
                interception.key_up(self.right_key)
            interception.key_down(self.left_key)
            self._current_move = "LEFT"

    def _jump_command(self):
        try:
            interception.key_down(self.jump_key)
        finally:
            interception.key_up(self.jump_key)
            if self._status_jump:
                self._status_jump = False

    def enable_jump(self):
        with self._jump_lock:
            if self._status_jump:
                return
        self._status_jump = True
        threading.Thread(target=self._jump_command,daemon=True).start() 


    def enable_up(self):

        interception.key_down(self.up_key)
        time.sleep(0.1)
        interception.key_up(self.up_key)
    
    def enable_right(self):
        interception.key_down(self.right_key)

        interception.key_up(self.right_key)

    def enable_left(self):
        interception.key_down(self.left_key)

        interception.key_up(self.left_key)


    ''' 停止釋放'''
    def release_all(self):
        
        self._status_attack= False
        self._stop_move()

    def _stop_move(self):
        with self._move_lock:
            #如果正在移動，左右鍵彈起
            if self._current_move is not None:
                try:
                    interception.key_up(self.left_key)
                    interception.key_up(self.right_key)
                except Exception as e:
                    logging.error(f"釋放移動發生錯誤:{e}")
                finally:
                    self._current_move = None

    ''' 物品使用行為（補血/補魔等） '''

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
                # 上一次使用還沒結束，不重複觸發
                return
            self._status_item = True
            threading.Thread(target=self._item_command, args=(key,), daemon=True).start()

    ''' 撿拾行為 '''
    def _pick_up_command(self, key):
        try:
            interception.key_down(key)
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"撿拾命令發生錯誤:{e}")
        finally:
            interception.key_up(key)
            self._pick_up = False

    def enable_pick_up(self):
        with self._pick_up_lock:
            if not self.pick_up_key:
                return
            self._pick_up = True
        threading.Thread(target=self._pick_up_command, args=(self.pick_up_key,), daemon=True).start()
