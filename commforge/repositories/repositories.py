"""各聚合根仓储及引用保护。"""

from collections.abc import Callable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from commforge.core.exceptions import DependencyError
from commforge.database.models import (
    AutomationTaskModel,
    CommunicationModel,
    MessageRuleModel,
    ReceiveRuleModel,
)
from commforge.repositories.base import Repository


class CommunicationRepository(Repository[CommunicationModel]):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        super().__init__(session_factory, CommunicationModel)

    def delete(self, entity_id: int) -> bool:
        """通信被自动化任务引用时拒绝删除并给出明确原因。"""
        with self._session_factory() as session:
            referenced = session.scalar(
                select(AutomationTaskModel.id).where(
                    or_(
                        AutomationTaskModel.communication_id == entity_id,
                        AutomationTaskModel.target_communication_id == entity_id,
                    )
                )
            )
            if referenced:
                raise DependencyError("该通信仍被自动化任务引用，不能删除")
        return super().delete(entity_id)


class MessageRuleRepository(Repository[MessageRuleModel]):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        super().__init__(session_factory, MessageRuleModel)

    def delete(self, entity_id: int) -> bool:
        with self._session_factory() as session:
            if session.scalar(
                select(AutomationTaskModel.id).where(
                    AutomationTaskModel.message_rule_id == entity_id
                )
            ):
                raise DependencyError("该报文规则仍被自动化任务引用，不能删除")
        return super().delete(entity_id)


class ReceiveRuleRepository(Repository[ReceiveRuleModel]):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        super().__init__(session_factory, ReceiveRuleModel)

    def delete(self, entity_id: int) -> bool:
        with self._session_factory() as session:
            if session.scalar(
                select(AutomationTaskModel.id).where(
                    AutomationTaskModel.receive_rule_id == entity_id
                )
            ):
                raise DependencyError("该接收规则仍被自动化任务引用，不能删除")
        return super().delete(entity_id)


class AutomationRepository(Repository[AutomationTaskModel]):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        super().__init__(session_factory, AutomationTaskModel)
