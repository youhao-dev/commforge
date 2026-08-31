"""应用日志初始化。"""

import logging
from logging.handlers import RotatingFileHandler

from commforge.app.paths import LOG_PATH, ensure_runtime_dirs


def configure_logging() -> None:
    """配置大小轮转日志，避免长期运行无限占用磁盘。"""
    ensure_runtime_dirs()
    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(item, RotatingFileHandler) for item in root.handlers):
        root.addHandler(handler)
