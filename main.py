import ctypes
# 強制讓 Python 程式識別真實的螢幕 DPI 像素，避免抓圖範圍縮水
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass
from src.engine.GameBot import GameBot
import src.utils.logger as logger
import logging
import os
import sys
    #=================
    # 作業系統管理員權限
    #=================
def is_admin():
    """檢查當前是否擁有管理員權限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理員權限重新執行當前"""

    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)


if __name__ == "__main__":

    #---管理員權限
    if not is_admin():
        run_as_admin()
        sys.exit()
    # 啟動日誌
    logger.setup_logging()
    try:

        run = GameBot()
        run.run()
    except Exception as e:
        logging.exception(f"未預期的例外錯誤: {e}")
    except KeyboardInterrupt:
        logging.info("'Ctrl+C'中斷程式")
    finally:
        logging.info("正常關閉")
        input("程式已結束，請按 Enter 鍵關閉視窗...")