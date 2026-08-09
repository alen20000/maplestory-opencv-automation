import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.config_loader import config


if __name__ == "__main__":
    raw = config.get("player_setting.health_setting")

    # print(raw)

    a = {}
    for level, setting in raw.items():
        key = setting.get("key")
        value = setting.get("value")
        if key == "None":
            key = None
        a[level] = {
            "key" : setting.get("key"),
            "value" : setting.get("value"),
        }
    print (a)