
import logging
from config.config_loader import config
from pathlib import Path


def setup_logging():
    log_folder = Path(config.get("logging_setting.log_path"))
    log_folder.mkdir(parents=True, exist_ok=True)

    #日誌路徑與檔名
    log_file_name = config.get("logging_setting.log_file_name")
    full_log_file_path = log_folder / log_file_name
    
    #日誌等級
    log_level = config.get("logging_setting.log_level")
    logging.basicConfig(
        level= log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(full_log_file_path, encoding="utf-8")
        ]
    )