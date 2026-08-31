"""通信类型工厂和实例生命周期管理。"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal

from commforge.communication.base import CommunicationChannel, TrafficEvent
from commforge.communication.serial import SerialChannel
from commforge.communication.tcp_client import TcpClientChannel
from commforge.communication.tcp_server import TcpServerChannel
from commforge.communication.udp import UdpChannel
from commforge.core.context import ReceiveContext
from commforge.core.enums import CommunicationType
from commforge.core.exceptions import CommunicationError

ChannelFactory = Callable[[int | None, str, dict[str, Any]], CommunicationChannel]


class CommunicationManager(QObject):
    traffic = Signal(object)
    frame_received = Signal(object)
    status_changed = Signal(int, str)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._factories: dict[CommunicationType, ChannelFactory] = {}
        self._channels: dict[int, CommunicationChannel] = {}
        self.register(CommunicationType.TCP_CLIENT, TcpClientChannel)
        self.register(CommunicationType.TCP_SERVER, TcpServerChannel)
        self.register(CommunicationType.UDP, UdpChannel)
        self.register(CommunicationType.SERIAL, SerialChannel)

    def register(self, communication_type: CommunicationType, factory: ChannelFactory) -> None:
        """注册新通信类型，管理器无需了解其内部实现。"""
        self._factories[communication_type] = factory

    def create_channel(
        self, communication_id: int, name: str, communication_type: str, config: dict[str, Any]
    ) -> CommunicationChannel:
        try:
            channel = self._factories[CommunicationType(communication_type)](
                communication_id, name, config
            )
        except KeyError as exc:
            raise CommunicationError(f"未注册通信类型：{communication_type}") from exc
        channel.traffic.connect(self.traffic)
        channel.frame_received.connect(self.frame_received)
        channel.error_occurred.connect(self.error_occurred)
        channel.status_changed.connect(
            lambda status, cid=communication_id: self.status_changed.emit(cid, status)
        )
        self._channels[communication_id] = channel
        return channel

    def get(self, communication_id: int) -> CommunicationChannel | None:
        return self._channels.get(communication_id)

    def open(self, communication_id: int) -> None:
        channel = self.get(communication_id)
        if not channel:
            raise CommunicationError("通信实例不存在")
        channel.open()

    def close(self, communication_id: int) -> None:
        channel = self.get(communication_id)
        if channel:
            channel.close()

    def close_all(self) -> None:
        """应用退出前同步关闭所有通道。"""
        for channel in list(self._channels.values()):
            channel.close()

    def send(self, communication_id: int, data: bytes, **target: Any) -> None:
        channel = self.get(communication_id)
        if not channel:
            raise CommunicationError("目标通信实例不存在")
        channel.send(data, **target)

    @property
    def channels(self) -> dict[int, CommunicationChannel]:
        return dict(self._channels)
