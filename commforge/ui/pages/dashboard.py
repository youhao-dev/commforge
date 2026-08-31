"""总览页面。"""

import json

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from commforge.core.enums import CommunicationStatus
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import Card, MetricCard, PageHeader, badge_cell, configure_table


class DashboardPage(QWidget):
    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)
        root.addWidget(PageHeader("总览", "通信与自动化运行状态"))

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.metric_cards = [
            MetricCard("通信连接", "0", "正常 0    异常 0", "#7657ff", QStyle.StandardPixmap.SP_DriveNetIcon),
            MetricCard("自动化任务", "0", "运行中 0    已停止 0", "#f5a13d", QStyle.StandardPixmap.SP_MediaPlay),
            MetricCard("发送帧数", "0", "今日累计", "#4999ef", QStyle.StandardPixmap.SP_ArrowUp),
            MetricCard("接收帧数", "0", "今日累计", "#49a86e", QStyle.StandardPixmap.SP_ArrowDown),
        ]
        for card in self.metric_cards:
            metrics.addWidget(card)
        root.addLayout(metrics)

        status_card = Card("通信状态")
        self.status_table = QTableWidget()
        configure_table(
            self.status_table,
            ["名称", "类型", "地址", "状态", "接收帧数", "发送帧数"],
        )
        self.status_table.setMinimumHeight(235)
        status_card.layout.addWidget(self.status_table)
        root.addWidget(status_card, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        recent = Card("最近活动")
        self.recent_table = QTableWidget()
        configure_table(self.recent_table, ["时间", "方向", "通信", "长度"])
        recent.layout.addWidget(self.recent_table)
        bottom.addWidget(recent, 3)
        task_card = Card("任务运行状态")
        self.task_table = QTableWidget()
        configure_table(self.task_table, ["任务名称", "状态"])
        task_card.layout.addWidget(self.task_table)
        bottom.addWidget(task_card, 2)
        root.addLayout(bottom, 1)

        self._recent_events: list[object] = []
        services.manager.traffic.connect(self._on_traffic)
        services.manager.status_changed.connect(lambda *_: self.refresh())
        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self.refresh)
        timer.start()
        self.refresh()

    def refresh(self) -> None:
        """刷新统计卡片和通道列表。"""
        communications = self.services.communications.list_all()
        open_count = sum(
            1 for item in communications
            if self.services.manager.get(item.id)
            and self.services.manager.get(item.id).status == CommunicationStatus.OPEN
        )
        error_count = sum(
            1 for item in communications
            if self.services.manager.get(item.id)
            and self.services.manager.get(item.id).status == CommunicationStatus.ERROR
        )
        tasks = self.services.automations.list_all()
        enabled = sum(1 for task in tasks if task.enabled)
        stats = self.services.runtime.stats
        values = [len(communications), len(tasks), stats.sent_frames, stats.received_frames]
        details = [
            f"正常 {open_count}    异常 {error_count}",
            f"运行中 {enabled}    已停止 {len(tasks) - enabled}",
            f"今日 +{stats.sent_frames}",
            f"今日 +{stats.received_frames}",
        ]
        for card, value, detail in zip(self.metric_cards, values, details):
            card.value_label.setText(f"{value:,}")
            card.layout.itemAt(card.layout.count() - 1).widget().setText(detail)

        self.status_table.setRowCount(0)
        self.status_table.setRowCount(len(communications))
        for row, item in enumerate(communications):
            config = json.loads(item.config_json or "{}")
            address = self._address(item.communication_type, config)
            channel = self.services.manager.get(item.id)
            status = channel.status.value if channel else "STOPPED"
            labels = [item.name, item.communication_type.replace("_", " "), address, status, "0", "0"]
            for column, text in enumerate(labels):
                if column == 3:
                    continue
                self.status_table.setItem(row, column, QTableWidgetItem(text))
            status_text, tone = {
                "OPEN": ("已打开", "success"),
                "CONNECTING": ("连接中", "warning"),
                "ERROR": ("异常", "danger"),
                "STOPPED": ("未启动", "neutral"),
            }.get(status, (status, "neutral"))
            self.status_table.setCellWidget(row, 3, badge_cell(status_text, tone))

        self.task_table.setRowCount(0)
        self.task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            self.task_table.setItem(row, 0, QTableWidgetItem(task.name))
            self.task_table.setCellWidget(
                row, 1, badge_cell("运行中" if task.enabled else "已停止", "success" if task.enabled else "neutral")
            )

    @staticmethod
    def _address(kind: str, config: dict[str, object]) -> str:
        if kind == "TCP_CLIENT":
            return f"{config.get('host', '')}:{config.get('port', '')}"
        if kind == "TCP_SERVER":
            return f"{config.get('host', '')}:{config.get('port', '')}"
        if kind == "UDP":
            return f"{config.get('local_host', '')}:{config.get('local_port', '')}"
        return f"{config.get('port_name', '')} · {config.get('baud_rate', '')}"

    def _on_traffic(self, event: object) -> None:
        self._recent_events.insert(0, event)
        self._recent_events = self._recent_events[:8]
        self.recent_table.setRowCount(0)
        self.recent_table.setRowCount(len(self._recent_events))
        for row, item in enumerate(self._recent_events):
            values = [
                item.timestamp.strftime("%H:%M:%S"), item.direction.value,
                item.communication_name, str(len(item.data)),
            ]
            for column, value in enumerate(values):
                if column == 1:
                    continue
                self.recent_table.setItem(row, column, QTableWidgetItem(value))
            self.recent_table.setCellWidget(
                row, 1, badge_cell(item.direction.value, "success" if item.direction.value == "TX" else "info")
            )
