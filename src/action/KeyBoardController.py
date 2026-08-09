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
        self._status_attack = False
        self._status_move= False
        #key value
        self.attack_key = config.get("keyboard.attack")
        self.left_key = config.get("keyboard.left")
        self.right_key = config.get("keyboard.right")

    ''' 攻擊行為 '''

    def _attack_command(self):
        try: 
            interception.key_down(self.attack_key)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"攻擊行為發生錯誤:{e}")
            
        finally:
            interception.key_up(self.attack_key)
            with self._attack_lock:
                self._status_attack = False


    def enable_attack(self):
        with self._attack_lock:
            if self._status_attack:
                #攻擊還在發生，不再傳輸攻擊指令
                return
            self._status_attack = True
            threading.Thread(target=self._attack_command, daemon=True).start() 

    ''' 移動行為 '''


    def _move_command(self, key):
        try:
            interception.key_down(key)
            time.sleep(0.7)
        except Exception as e:
            logging.error(f"移動發生錯誤:{e}")
        finally:
            interception.key_up(key)
            with self._move_lock:
                self._status_move = False

    def _enable_move(self, key):
        with self._move_lock :
            if self._status_move:
                #移動還在發生，不再傳輸移動指令
                return
            self.status_move = True
            threading.Thread(target=self._move_command, args=(key,), daemon=True).start()

    def enable_move_right(self):
        self._enable_move(self.right_key)
 
    def enable_move_left(self):
        self._enable_move(self.left_key)

    ''' 停止釋放'''
    def release_all(self):
        with self._attack_lock:
            self._attack_busy = False
        with self._move_lock:
            self._move_busy = False
