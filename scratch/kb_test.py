import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.config_loader import config 
import interception
import time

import keyboard as kb
interception.auto_capture_devices(keyboard=True, mouse=True)

key = config.get("keyboard.right")
print(f"key: {key}; {type(key)}")

while True:
    time.sleep(1)
    interception.press(key)

    if kb.is_pressed("esc"):
        break
