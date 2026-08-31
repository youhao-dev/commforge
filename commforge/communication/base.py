"""Qt 事件驱动通信通道抽象。"""

from abc import abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer, Signal

from commforge.communication.frame_decoder import FrameDecoder
from commforge.core.context import ReceiveContext
from commforge.core.enums import CommunicationStatus, FrameDecoderType, LogDirection


@dataclass(slots=True)
class TrafficEvent:
    timestamp: datetime
    direction: LogDirection
    communication_id: int | None
    communication_name: str
    data: bytes
    session_id: str | None = None
    remote_host: str | None = None
    remote_port: int | None = None


class SendQueue(QObject):
    """单通道 FIFO，确保自动回复和定时发送不会并发写 socket。"""

    failed = Signal(str)

    def __init__(self, writer: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._writer = writer
        self._queue: deque[tuple[bytes, dict[str, Any]]] = deque()
        self._busy = False

    def enqueue(self, data: bytes, **target: Any) -> None:
        self._queue.append((bytes(data), target))
        if not self._busy:
            QTimer.singleShot(0, self._drain_one)

    def _drain_one(self) -> None:
        """每次事件循环只发送一项，保持 UI 响应。"""
        if not self._queue:
            self._busy = False
            return
        self._busy = True
        data, target = self._queue.popleft()
        try:
            self._writer(data, **target)
        except Exception as exc:  # 通信异常不能使调度器退出。
            self.failed.emit(str(exc))
        QTimer.singleShot(0, self._drain_one)


class CommunicationChannel(QObject):
    status_changed = Signal(str)
    frame_received = Signal(object)
    traffic = Signal(object)
    error_occurred = Signal(str)

    def __init__(
        self,
        communication_id: int | None,
        name: str,
        config: dict[str, Any],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.communication_id = communication_id
        self.name = name
        self.config = config
        self.status = CommunicationStatus.STOPPED
        self.decoder = FrameDecoder(
            config.get("decoder_type", "RAW"), config.get("decoder_config", {})
        )
        self._last_receive_target: dict[str, Any] = {}
        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._flush_idle_frame)
        self.send_queue = SendQueue(self._write, self)
        self.send_queue.failed.connect(self._on_error)

    @abstractmethod
    def open(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    def send(self, data: bytes, **target: Any) -> None:
        """所有外部发送统一进入有序队列。"""
        self.send_queue.enqueue(data, **target)

    @abstractmethod
    def _write(self, data: bytes, **target: Any) -> None:
        pass

    def is_open(self) -> bool:
        return self.status == CommunicationStatus.OPEN

    def _set_status(self, status: CommunicationStatus) -> None:
        self.status = status
        self.status_changed.emit(status.value)

    def _on_data(
        self,
        data: bytes,
        *,
        session_id: str | None = None,
        remote_host: str | None = None,
        remote_port: int | None = None,
    ) -> None:
        target = {
            "session_id": session_id,
            "remote_host": remote_host,
            "remote_port": remote_port,
        }
        self._last_receive_target = target
        frames = self.decoder.feed(bytes(data))
        if self.decoder.decoder_type == FrameDecoderType.IDLE_TIMEOUT:
            idle_ms = max(1, int(self.decoder.config.get("idle_ms", 50)))
            self._idle_timer.start(idle_ms)
            return
        for frame in frames:
            self._emit_frame(frame, **target)

    def _flush_idle_frame(self) -> None:
        """静默期到达后把缓存作为一帧交给统一接收流程。"""
        for frame in self.decoder.flush():
            self._emit_frame(frame, **self._last_receive_target)

    def _emit_frame(
        self,
        frame: bytes,
        *,
        session_id: str | None = None,
        remote_host: str | None = None,
        remote_port: int | None = None,
    ) -> None:
        context = ReceiveContext(
                communication_id=self.communication_id,
                raw_data=frame,
                session_id=session_id,
                remote_host=remote_host,
                remote_port=remote_port,
        )
        self.frame_received.emit(context)
        self.traffic.emit(
            TrafficEvent(
                datetime.now(), LogDirection.RX, self.communication_id, self.name,
                frame, session_id, remote_host, remote_port
            )
        )

    def _log_tx(self, data: bytes, **target: Any) -> None:
        self.traffic.emit(
            TrafficEvent(
                datetime.now(), LogDirection.TX, self.communication_id, self.name, data,
                target.get("session_id"), target.get("remote_host"), target.get("remote_port")
            )
        )

    def _on_error(self, message: str) -> None:
        self._set_status(CommunicationStatus.ERROR)
        self.error_occurred.emit(message)

    @staticmethod
    def new_session_id() -> str:
        return uuid4().hex[:12]
