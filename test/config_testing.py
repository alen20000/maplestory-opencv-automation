import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.config_loader import config 


if __name__ == "__main__":
    print(config.get("logging_setting.log_path"))
    print(config.get("logging_setting.log_file_name"))