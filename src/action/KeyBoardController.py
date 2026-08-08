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
        self.status_loop = False
        #key value
        self.attack_ley = config.get("keyboard.attack")
        self.left_key = config.get("keyboard.left")
        self.right_key = config.get("keyboard.right")
    
    def _attack_loop(self):
        while self.status_loop:
            interception.key_down(self.attack_ley)
            time.sleep(0.2)
            interception.key_up(self.attack_ley)

    def enable_attack(self):
            self.status_loop = True
            threading.Thread(target=self._attack_loop, daemon=True).start() 

    def _moveing_right(self):
        while self.status_loop:
            interception.key_down(self.right_ley)
            time.sleep(0.2)
            interception.key_up(self.right_ley)

    def enable_move_right(self):
        self.status_loop = True
        threading.Thread(target=self._moveing_right, daemon=True).start()

    def _moveing_left(self):
        while self.status_loop:
            interception.key_down(self.left_key)
            time.sleep(0.2)
            interception.key_up(self.left_key)

    def enable_move_left(self):
        self.status_loop = True
        threading.Thread(target=self._moveing_left, daemon=True).start()

    def release_all(self):
        self.status_loop = False

