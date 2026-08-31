"""统一 Trigger → Condition → Action 自动化引擎。"""

import json
import logging
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal

from commforge.core.context import ReceiveContext
from commforge.core.enums import CodecType, MatchType, TaskTargetType, TriggerType
from commforge.database.models import AutomationTaskModel
from commforge.message.builder import BuildContext
from commforge.receive.rules import ReceiveFieldSpec, ReceiveRule
from commforge.services.application import ApplicationServices

LOGGER = logging.getLogger(__name__)


class AutomationEngine(QObject):
    task_executed = Signal(int, bool, str)

    def __init__(self, services: ApplicationServices, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.services = services
        self._timers: dict[int, QTimer] = {}
        self.services.manager.frame_received.connect(self._on_receive)
        self.services.manager.status_changed.connect(self._on_status_changed)

    def start_enabled(self) -> None:
        """为启用的 TIMER 任务注册 QTimer。"""
        for task in self.services.automations.list_all():
            if task.enabled and task.trigger_type == TriggerType.TIMER:
                self.start_task(task)

    def start_task(self, task: AutomationTaskModel) -> None:
        if task.id in self._timers:
            return
        config = json.loads(task.config_json or "{}")
        interval = max(20, int(config.get("interval_ms", 1000)))
        timer = QTimer(self)
        timer.setInterval(interval)
        timer.timeout.connect(lambda task_id=task.id: self.execute(task_id))
        self._timers[task.id] = timer
        initial_delay = max(0, int(config.get("initial_delay", 0)))
        QTimer.singleShot(initial_delay, timer.start)

    def stop_task(self, task_id: int) -> None:
        timer = self._timers.pop(task_id, None)
        if timer:
            timer.stop()
            timer.deleteLater()

    def execute(self, task_id: int, receive: ReceiveContext | None = None) -> None:
        """隔离任务异常，构建并发送一次消息。"""
        task = self.services.automations.get(task_id)
        if not task:
            return
        try:
            rule = self.services.get_rule(task.message_rule_id)
            if not rule:
                raise RuntimeError("报文规则不存在")
            result = self.services.builder.build(
                self.services.to_field_specs(rule),
                BuildContext(task_id=task.id, runtime=self.services.runtime, receive=receive),
            )
            target_id = task.target_communication_id or task.communication_id
            if target_id is None:
                raise RuntimeError("未配置目标通信")
            target: dict[str, object] = {}
            if receive and task.target_type in (
                TaskTargetType.CURRENT_SOURCE,
                TaskTargetType.TCP_CURRENT_SESSION,
                TaskTargetType.UDP_CURRENT_REMOTE,
            ):
                target = {
                    "session_id": receive.session_id,
                    "remote_host": receive.remote_host,
                    "remote_port": receive.remote_port,
                }
            delay_ms = int(json.loads(task.config_json or "{}").get("delay_ms", 0))
            QTimer.singleShot(
                max(0, delay_ms),
                lambda: self.services.manager.send(target_id, result.data, **target),
            )
            self.services.runtime.stats.task_runs += 1
            self.task_executed.emit(task_id, True, datetime.now().isoformat(timespec="seconds"))
        except Exception as exc:
            LOGGER.exception("自动化任务 %s 执行失败", task_id)
            self.task_executed.emit(task_id, False, str(exc))

    def _on_receive(self, context: ReceiveContext) -> None:
        for task in self.services.automations.list_all():
            if (
                task.enabled
                and task.trigger_type == TriggerType.RECEIVE
                and task.communication_id == context.communication_id
            ):
                parsed_context = context
                if task.receive_rule_id:
                    entity = self.services.get_receive_rule(task.receive_rule_id)
                    if not entity:
                        continue
                    rule = ReceiveRule(
                        entity.name,
                        MatchType(entity.match_type),
                        entity.pattern,
                        [
                            ReceiveFieldSpec(
                                item.name, item.offset, item.length, CodecType(item.codec_type),
                                item.expected_value, item.required
                            )
                            for item in entity.fields
                        ],
                    )
                    if not rule.matches(context.raw_data):
                        continue
                    try:
                        parsed_context = rule.parse(
                            context.raw_data,
                            communication_id=context.communication_id,
                            session_id=context.session_id,
                            remote_host=context.remote_host,
                            remote_port=context.remote_port,
                            timestamp=context.timestamp,
                        )
                    except Exception:
                        LOGGER.exception("接收规则 %s 解析失败", task.receive_rule_id)
                        continue
                self.execute(task.id, parsed_context)

    def _on_status_changed(self, communication_id: int, status: str) -> None:
        """将连接状态变化映射为 CONNECTED / DISCONNECTED 触发器。"""
        expected = TriggerType.CONNECTED if status == "OPEN" else TriggerType.DISCONNECTED
        if status not in ("OPEN", "STOPPED"):
            return
        for task in self.services.automations.list_all():
            if (
                task.enabled
                and task.trigger_type == expected
                and task.communication_id == communication_id
            ):
                self.execute(task.id)

    def shutdown(self) -> None:
        """应用关闭前停止全部定时器。"""
        for task_id in list(self._timers):
            self.stop_task(task_id)
