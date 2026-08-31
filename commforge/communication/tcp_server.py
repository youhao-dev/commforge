"""TCP Server 通道，维护独立客户端 session。"""

from datetime import datetime
from typing import Any

from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

from commforge.communication.base import CommunicationChannel
from commforge.core.enums import CommunicationStatus
from commforge.core.exceptions import CommunicationError


class TcpServerChannel(CommunicationChannel):
    def __init__(self, communication_id: int | None, name: str, config: dict[str, Any]) -> None:
        super().__init__(communication_id, name, config)
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._accept_clients)
        self.server.acceptError.connect(lambda _: self._on_error(self.server.errorString()))
        self.clients: dict[str, tuple[QTcpSocket, datetime]] = {}

    def open(self) -> None:
        host = QHostAddress(str(self.config.get("host", "0.0.0.0")))
        if not self.server.listen(host, int(self.config.get("port", 9001))):
            self._on_error(self.server.errorString())
            return
        self._set_status(CommunicationStatus.OPEN)

    def close(self) -> None:
        for socket, _ in self.clients.values():
            socket.abort()
        self.clients.clear()
        self.server.close()
        self._set_status(CommunicationStatus.STOPPED)

    def _accept_clients(self) -> None:
        maximum = int(self.config.get("max_clients", 32))
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if len(self.clients) >= maximum:
                socket.disconnectFromHost()
                continue
            session_id = self.new_session_id()
            self.clients[session_id] = (socket, datetime.now())
            socket.readyRead.connect(lambda s=socket, sid=session_id: self._read_client(s, sid))
            socket.disconnected.connect(lambda sid=session_id: self.clients.pop(sid, None))

    def _read_client(self, socket: QTcpSocket, session_id: str) -> None:
        self._on_data(
            bytes(socket.readAll()), session_id=session_id,
            remote_host=socket.peerAddress().toString(), remote_port=socket.peerPort()
        )

    def _write(self, data: bytes, **target: Any) -> None:
        session_id = target.get("session_id")
        if session_id:
            client = self.clients.get(str(session_id))
            if not client:
                raise CommunicationError("指定 TCP 客户端会话不存在")
            client[0].write(data)
            self._log_tx(data, session_id=session_id)
            return
        if not self.clients:
            raise CommunicationError("TCP Server 当前没有已连接客户端")
        for current_id, (socket, _) in self.clients.items():
            socket.write(data)
            self._log_tx(data, session_id=current_id)
