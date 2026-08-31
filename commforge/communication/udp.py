"""UDP 通道。"""

from typing import Any

from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QUdpSocket

from commforge.communication.base import CommunicationChannel
from commforge.core.enums import CommunicationStatus
from commforge.core.exceptions import CommunicationError


class UdpChannel(CommunicationChannel):
    def __init__(self, communication_id: int | None, name: str, config: dict[str, Any]) -> None:
        super().__init__(communication_id, name, config)
        self.socket = QUdpSocket(self)
        self.socket.readyRead.connect(self._read_datagrams)
        self.socket.errorOccurred.connect(lambda _: self._on_error(self.socket.errorString()))

    def open(self) -> None:
        ok = self.socket.bind(
            QHostAddress(str(self.config.get("local_host", "0.0.0.0"))),
            int(self.config.get("local_port", 9002)),
            QAbstractSocket.BindFlag.ShareAddress,
        )
        self._set_status(CommunicationStatus.OPEN if ok else CommunicationStatus.ERROR)
        if not ok:
            self.error_occurred.emit(self.socket.errorString())

    def close(self) -> None:
        self.socket.close()
        self._set_status(CommunicationStatus.STOPPED)

    def _read_datagrams(self) -> None:
        while self.socket.hasPendingDatagrams():
            datagram = self.socket.receiveDatagram()
            self._on_data(
                bytes(datagram.data()), remote_host=datagram.senderAddress().toString(),
                remote_port=datagram.senderPort()
            )

    def _write(self, data: bytes, **target: Any) -> None:
        host = str(target.get("remote_host") or self.config.get("remote_host", "127.0.0.1"))
        port = int(target.get("remote_port") or self.config.get("remote_port", 9002))
        if port <= 0:
            raise CommunicationError("UDP 远程端口不合法")
        self.socket.writeDatagram(data, QHostAddress(host), port)
        self._log_tx(data, remote_host=host, remote_port=port)
