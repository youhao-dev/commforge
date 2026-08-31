"""运行状态上下文，和数据库中的静态配置严格分离。"""

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any


@dataclass(slots=True)
class ReceiveContext:
    communication_id: int | None = None
    raw_data: bytes = b""
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str | None = None
    remote_host: str | None = None
    remote_port: int | None = None
    parsed_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeStats:
    sent_frames: int = 0
    received_frames: int = 0
    sent_bytes: int = 0
    received_bytes: int = 0
    task_runs: int = 0


class RuntimeContext:
    """保存字段状态与累计统计；字段状态按 task_id + field_id 隔离。"""

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], Any] = {}
        self._lock = RLock()
        self.stats = RuntimeStats()

    def get(self, task_id: object, field_id: object, default: Any = None) -> Any:
        """读取指定任务中某字段的运行值。"""
        with self._lock:
            return self._values.get((str(task_id), str(field_id)), default)

    def set(self, task_id: object, field_id: object, value: Any) -> None:
        """更新运行值，不触碰持久化配置。"""
        with self._lock:
            self._values[(str(task_id), str(field_id))] = value

    def reset_task(self, task_id: object) -> None:
        """清除单个任务的字段状态。"""
        with self._lock:
            prefix = str(task_id)
            for key in [item for item in self._values if item[0] == prefix]:
                del self._values[key]
