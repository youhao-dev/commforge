"""通用仓储实现。"""

from collections.abc import Callable
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from commforge.database.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, session_factory: Callable[[], Session], model: type[ModelT]) -> None:
        self._session_factory = session_factory
        self._model = model

    def add(self, entity: ModelT) -> ModelT:
        """新增实体并刷新数据库生成字段。"""
        with self._session_factory() as session:
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity

    def get(self, entity_id: int) -> ModelT | None:
        with self._session_factory() as session:
            return session.get(self._model, entity_id)

    def list_all(self) -> list[ModelT]:
        with self._session_factory() as session:
            return list(session.scalars(select(self._model).order_by(self._model.id)))

    def update(self, entity_id: int, **values: object) -> ModelT | None:
        """只更新模型已声明的字段。"""
        with self._session_factory() as session:
            entity = session.get(self._model, entity_id)
            if entity is None:
                return None
            for key, value in values.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            session.commit()
            session.refresh(entity)
            return entity

    def delete(self, entity_id: int) -> bool:
        with self._session_factory() as session:
            entity = session.get(self._model, entity_id)
            if entity is None:
                return False
            session.delete(entity)
            session.commit()
            return True
