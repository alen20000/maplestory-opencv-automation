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
        self.status_move= False
        self.status_attack = False
        #key value
        self.attack_ley = config.get("keyboard.attack")
        self.left_key = config.get("keyboard.left")
        self.right_key = config.get("keyboard.right")
    
    def _attack_loop(self):
        while self.status_attack:
            interception.key_down(self.attack_ley)
            time.sleep(0.3)
            interception.key_up(self.attack_ley)
            self.status_attack = False

    def enable_attack(self):
            self.status_attack= True
            threading.Thread(target=self._attack_loop, daemon=True).start() 

    def _moveing_right(self):
        while self.status_move:
            interception.key_down(self.right_key)
            time.sleep(0.2)
            interception.key_up(self.right_key)
            self.status_move = False

    def enable_move_right(self):
        self.status_move = True
        threading.Thread(target=self._moveing_right, daemon=True).start()

    def _moveing_left(self):
        while self.status_move:
            interception.key_down(self.left_key)
            time.sleep(0.2)
            interception.key_up(self.left_key)
            self.status_move = False

    def enable_move_left(self):
        self.status_move = True
        threading.Thread(target=self._moveing_left, daemon=True).start()

    def release_all(self):
        self.status_action_loop = False

