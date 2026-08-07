import time
import interception
import logging
from config.config_loader import config
import threading

class KeyBoard:
    def __init__(self):
        #捕捉與綁定滑鼠
        interception.auto_capture_devices(keyboard=True, mouse=True)
        self.enable_pick = False
        #setting
        
    def attack_action(self)
