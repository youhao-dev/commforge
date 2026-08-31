"""高容量收发日志和报文详情。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from commforge.communication.base import TrafficEvent
from commforge.core.enums import LogDirection
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import Card, PageHeader, configure_table


class TrafficDetailDialog(QDialog):
    def __init__(self, event: TrafficEvent, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("完整报文详情")
        self.setMinimumSize(680, 460)
        root = QVBoxLayout(self)
        metadata = QLabel(
            f"时间：{event.timestamp.isoformat(sep=' ', timespec='milliseconds')}    "
            f"方向：{event.direction.value}    通信：{event.communication_name}\n"
            f"远程：{event.remote_host or '—'}:{event.remote_port or '—'}    "
            f"Session：{event.session_id or '—'}    长度：{len(event.data)} bytes"
        )
        metadata.setObjectName("Muted")
        root.addWidget(metadata)
        tabs = QTabWidget()
        self.hex_text = QPlainTextEdit(event.data.hex(" ").upper())
        self.ascii_text = QPlainTextEdit(
            "".join(chr(item) if 32 <= item < 127 else "." for item in event.data)
        )
        self.hex_text.setReadOnly(True)
        self.ascii_text.setReadOnly(True)
        tabs.addTab(self.hex_text, "HEX")
        tabs.addTab(self.ascii_text, "ASCII")
        root.addWidget(tabs)
        actions = QHBoxLayout()
        actions.addStretch()
        copy_hex = QPushButton("复制 HEX")
        copy_hex.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.hex_text.toPlainText()))
        copy_ascii = QPushButton("复制 ASCII")
        copy_ascii.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.ascii_text.toPlainText()))
        close = QPushButton("关闭")
        close.setObjectName("PrimaryButton")
        close.clicked.connect(self.accept)
        actions.addWidget(copy_hex)
        actions.addWidget(copy_ascii)
        actions.addWidget(close)
        root.addLayout(actions)


class LogsPage(QWidget):
    MAX_ROWS = 5000

    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        self.events: list[TrafficEvent] = []
        self.visible_events: list[TrafficEvent] = []
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(12)
        header = PageHeader("收发日志", "实时查看、过滤并复制完整通信报文")
        header.add_action("清空", self.clear)
        root.addWidget(header)
        filters = QHBoxLayout()
        self.communication_filter = QComboBox()
        self.communication_filter.addItem("全部通信", None)
        for item in services.communications.list_all():
            self.communication_filter.addItem(item.name, item.id)
        self.direction_filter = QComboBox()
        self.direction_filter.addItems(["全部方向", "TX", "RX"])
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索内容（HEX / ASCII）")
        self.search.setClearButtonEnabled(True)
        self.auto_scroll = QCheckBox("自动滚动")
        self.auto_scroll.setChecked(True)
        self.paused = QCheckBox("暂停显示")
        for widget in [self.communication_filter, self.direction_filter, self.search]:
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.apply_filters)
            else:
                widget.textChanged.connect(self.apply_filters)
        filters.addWidget(self.communication_filter)
        filters.addWidget(self.direction_filter)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.paused)
        filters.addWidget(self.auto_scroll)
        card = Card()
        card.layout.addLayout(filters)
        self.table = QTableWidget()
        configure_table(self.table, ["时间", "方向", "通信", "远程地址", "长度", "ASCII", "HEX"])
        self.table.doubleClicked.connect(self.open_detail)
        card.layout.addWidget(self.table)
        self.count_label = QLabel("共 0 条")
        self.count_label.setObjectName("Muted")
        card.layout.addWidget(self.count_label)
        root.addWidget(card, 1)
        services.manager.traffic.connect(self.add_event)

    def add_event(self, event: TrafficEvent) -> None:
        """保留最近 5000 条，并同步更新全局流量统计。"""
        self.events.append(event)
        if len(self.events) > self.MAX_ROWS:
            del self.events[: len(self.events) - self.MAX_ROWS]
        stats = self.services.runtime.stats
        if event.direction == LogDirection.TX:
            stats.sent_frames += 1
            stats.sent_bytes += len(event.data)
        else:
            stats.received_frames += 1
            stats.received_bytes += len(event.data)
        if not self.paused.isChecked():
            self.apply_filters()

    def apply_filters(self) -> None:
        communication_id = self.communication_filter.currentData()
        direction = self.direction_filter.currentText()
        keyword = self.search.text().strip().upper()
        visible: list[TrafficEvent] = []
        for event in self.events:
            if communication_id is not None and event.communication_id != communication_id:
                continue
            if direction != "全部方向" and event.direction.value != direction:
                continue
            ascii_text = "".join(chr(item) if 32 <= item < 127 else "." for item in event.data)
            hex_text = event.data.hex(" ").upper()
            if keyword and keyword not in hex_text and keyword not in ascii_text.upper():
                continue
            visible.append(event)
        self.visible_events = visible
        self.table.setRowCount(len(visible))
        for row, event in enumerate(visible):
            remote = f"{event.remote_host}:{event.remote_port}" if event.remote_host else "—"
            ascii_text = "".join(chr(item) if 32 <= item < 127 else "." for item in event.data)
            values = [
                event.timestamp.strftime("%H:%M:%S.%f")[:-3], event.direction.value,
                event.communication_name, remote, str(len(event.data)),
                ascii_text[:42], event.data.hex(" ").upper()[:70],
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.count_label.setText(f"共 {len(visible)} 条（保留最近 {self.MAX_ROWS} 条）")
        if self.auto_scroll.isChecked() and visible:
            self.table.scrollToBottom()

    def open_detail(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self.visible_events):
            TrafficDetailDialog(self.visible_events[row], self).exec()

    def clear(self) -> None:
        self.events.clear()
        self.apply_filters()
