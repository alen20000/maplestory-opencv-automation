from src.engine.GameBot import GameBot
import src.utils.logger as logger
import logging

if __name__ == "__main__":
    # 啟動日誌
    logger.setup_logging()
    try:

        run = GameBot()
        run.run()
    except Exception as e:
        logging.log.exception(f"未預期的例外錯誤: {e}")
    except KeyboardInterrupt:
        logging.info("'Ctrl+C'中斷程式")
    finally:
        logging.info("正常關閉")