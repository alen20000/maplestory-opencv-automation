
import logging
from config.config_loader import config
from pathlib import Path


def setup_logging():
    log_folder = Path(config.get("logging_setting.log_path"))
    #mkdir 要的是路徑物件，而不是字串路徑
    log_folder.mkdir(parents=True, exist_ok=True)
    log_file_name = config.get("logging_setting.log_file_name")
    full_log_file_path = log_folder / log_file_name
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(full_log_file_path, encoding="utf-8")
        ]
    )