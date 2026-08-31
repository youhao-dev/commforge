"""集中管理源码之外的运行时目录。"""

import sys
from pathlib import Path


def resolve_project_root() -> Path:
    """返回源码根目录，冻结后则返回可执行文件所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = resolve_project_root()
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
DATABASE_PATH = DATA_DIR / "commforge.db"
LOG_PATH = LOG_DIR / "commforge.log"


def ensure_runtime_dirs() -> None:
    """首次启动时创建数据库与日志目录。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
