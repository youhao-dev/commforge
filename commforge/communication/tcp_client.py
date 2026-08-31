"""TCP Client 通道。"""

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QAbstractSocket, QTcpSocket

from commforge.communication.base import CommunicationChannel
from commforge.core.enums import CommunicationStatus
from commforge.core.exceptions import CommunicationError


class TcpClientChannel(CommunicationChannel):
    def __init__(self, communication_id: int | None, name: str, config: dict[str, Any]) -> None:
        super().__init__(communication_id, name, config)
        self.socket = QTcpSocket(self)
        self._manual_close = True
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self.open)
        self._connect_timeout = QTimer(self)
        self._connect_timeout.setSingleShot(True)
        self._connect_timeout.timeout.connect(self._on_connect_timeout)
        self.socket.connected.connect(self._on_connected)
        self.socket.disconnected.connect(self._on_disconnected)
        self.socket.readyRead.connect(self._read_available)
        self.socket.errorOccurred.connect(lambda _: self._on_error(self.socket.errorString()))

    def open(self) -> None:
        self._manual_close = False
        self._set_status(CommunicationStatus.CONNECTING)
        self.socket.connectToHost(str(self.config.get("host", "127.0.0.1")), int(self.config.get("port", 9000)))
        self._connect_timeout.start(max(100, int(self.config.get("connection_timeout", 5000))))

    def close(self) -> None:
        self._manual_close = True
        self._reconnect_timer.stop()
        self._connect_timeout.stop()
        self.socket.abort()
        self._set_status(CommunicationStatus.STOPPED)

    def _read_available(self) -> None:
        self._on_data(bytes(self.socket.readAll()))

    def _write(self, data: bytes, **target: Any) -> None:
        if self.socket.state() != QAbstractSocket.SocketState.ConnectedState:
            raise CommunicationError("TCP Client 尚未连接")
        self.socket.write(data)
        self._log_tx(data)

    def _on_connected(self) -> None:
        self._connect_timeout.stop()
        self._set_status(CommunicationStatus.OPEN)

    def _on_disconnected(self) -> None:
        self._connect_timeout.stop()
        self._set_status(CommunicationStatus.STOPPED)
        if not self._manual_close and bool(self.config.get("auto_reconnect", False)):
            self._reconnect_timer.start(max(100, int(self.config.get("reconnect_interval", 3000))))

    def _on_connect_timeout(self) -> None:
        """连接超时后中止本次连接，并按配置进入重连。"""
        if self.socket.state() != QAbstractSocket.SocketState.ConnectedState:
            self.socket.abort()
            self._on_error("TCP Client 连接超时")
            self._on_disconnected()
