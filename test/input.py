import interception
import time

interception.auto_capture_devices(keyboard=True, mouse=True)

while True:
    time.sleep(0.1)
    interception.press(key='ctrl')