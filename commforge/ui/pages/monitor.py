"""运行监控页面。"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from commforge.core.enums import CommunicationStatus
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import MetricCard, PageHeader


class MonitorPage(QWidget):
    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(18)
        root.addWidget(PageHeader("运行监控", "实时查看连接、任务与流量统计"))
        grid = QGridLayout()
        grid.setSpacing(14)
        titles = [
            "活动通信数", "TCP 客户端连接数", "运行任务数", "累计发送帧数",
            "累计接收帧数", "发送字节数", "接收字节数", "任务执行次数",
        ]
        self.cards = [MetricCard(title, "0", "实时统计", "#7657ff") for title in titles]
        for index, card in enumerate(self.cards):
            grid.addWidget(card, index // 4, index % 4)
        root.addLayout(grid)
        root.addStretch()
        timer = QTimer(self)
        timer.setInterval(500)
        timer.timeout.connect(self.refresh)
        timer.start()
        self.refresh()

    def refresh(self) -> None:
        channels = self.services.manager.channels.values()
        stats = self.services.runtime.stats
        values = [
            sum(channel.status == CommunicationStatus.OPEN for channel in channels),
            sum(len(getattr(channel, "clients", {})) for channel in channels),
            sum(task.enabled for task in self.services.automations.list_all()),
            stats.sent_frames, stats.received_frames, stats.sent_bytes,
            stats.received_bytes, stats.task_runs,
        ]
        for card, value in zip(self.cards, values):
            card.value_label.setText(f"{value:,}")
