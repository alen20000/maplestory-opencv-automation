import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.utils.logger import setup_logging 
import logging
import src.utils.logger as logger

logger.setup_logging()
# 手動觸發不同層級的日誌
logging.debug("這是一則 Debug 訊息（用於細部除錯）")
logging.info("這是一則 Info 訊息（代表程式正常運行）")
logging.warning("這是一則 Warning 訊息（可能有潛在問題）")
logging.error("這是一則 Error 訊息（發生了錯誤！）")