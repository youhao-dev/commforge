"""SQLite 引擎和会话工厂。"""

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from commforge.app.paths import DATABASE_PATH, ensure_runtime_dirs
from commforge.database.models import Base


def create_database_engine(path: str | Path | None = None) -> Engine:
    """创建启用外键和 WAL 的 SQLite 引擎。"""
    ensure_runtime_dirs()
    database_path = Path(path) if path else DATABASE_PATH
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{database_path}", future=True)

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection: Any, _: Any) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def initialize_database(engine: Engine) -> None:
    """创建当前版本所需的全部数据表。"""
    Base.metadata.create_all(engine)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
