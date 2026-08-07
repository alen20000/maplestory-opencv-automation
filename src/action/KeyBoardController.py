import time
import interception
import logging
from config.config_loader import config
import threading

class KeyBoard:
    def __init__(self):
        #捕捉與綁定滑鼠
        interception.auto_capture_devices(keyboard=True, mouse=True)
        self.enable_pick = None
        self.enable_attack = None
        #key setting
        self.attack_ley = config.get("keybind.attack")
        self.left_key = config.get("keybind.left")
        self.right_key = config.get("keybind.right")
    def attack_act(self):
            time.sleep(0.1)
            # interception.press(key='a')

    def move_right(self):
            time.sleep(0.1)
            interception.press('right')

    def move_left(self):
            time.sleep(0.1)
            # interception.press(self.left_key)

        
