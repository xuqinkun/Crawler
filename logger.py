import logging
import os

from concurrent_log_handler import ConcurrentRotatingFileHandler


def setup_concurrent_logging():
    logger = logging.getLogger('concurrent_logger')
    logger.setLevel(logging.DEBUG)

    # 使用ConcurrentRotatingFileHandler
    log_file = "logs/app.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_handler = ConcurrentRotatingFileHandler(
        filename=log_file,
        mode='a',
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger