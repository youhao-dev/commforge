"""卡片、页面头部和表格等通用组件。"""

from collections.abc import Iterable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        title_box.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("Muted")
            title_box.addWidget(subtitle_label)
        layout.addLayout(title_box)
        layout.addStretch()
        self.actions = QHBoxLayout()
        self.actions.setSpacing(7)
        layout.addLayout(self.actions)

    def add_action(self, text: str, callback: object, primary: bool = False) -> QPushButton:
        """在标题右侧添加统一样式的操作按钮。"""
        button = QPushButton(text)
        button.setMinimumWidth(max(64, button.sizeHint().width() + 8))
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if primary:
            button.setObjectName("PrimaryButton")
        button.clicked.connect(callback)
        self.actions.addWidget(button)
        return button


class Card(QFrame):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("SectionTitle")
            self.layout.addWidget(label)


class MetricCard(Card):
    def __init__(
        self,
        title: str,
        value: str,
        detail: str,
        accent: str,
        icon_type: QStyle.StandardPixmap = QStyle.StandardPixmap.SP_ComputerIcon,
    ) -> None:
        """创建带真实系统图标和独立强调色的指标卡片。"""
        super().__init__()
        head = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("SectionTitle")
        icon = QToolButton()
        icon.setIcon(QApplication.style().standardIcon(icon_type))
        icon.setIconSize(QSize(16, 16))
        icon.setEnabled(False)
        icon.setStyleSheet(
            f"background:{accent}18;border:0;border-radius:15px;min-width:30px;min-height:30px;"
        )
        head.addWidget(label)
        head.addStretch()
        head.addWidget(icon)
        self.layout.addLayout(head)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        self.layout.addWidget(self.value_label)
        detail_label = QLabel(detail)
        detail_label.setObjectName("MetricDelta")
        self.layout.addWidget(detail_label)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(118)


class StatusBadge(QLabel):
    """用于表格状态列的轻量语义标签。"""

    COLORS = {
        "success": ("#e9f8ef", "#278a50", "#c6ecd5"),
        "warning": ("#fff6e5", "#a46612", "#f6dfad"),
        "danger": ("#fff0f1", "#cf3f49", "#ffd1d5"),
        "neutral": ("#f1f3f6", "#667085", "#e1e5eb"),
        "info": ("#eef4ff", "#3975d2", "#d5e3ff"),
    }

    def __init__(self, text: str, tone: str = "neutral") -> None:
        super().__init__(text)
        background, foreground, border = self.COLORS.get(tone, self.COLORS["neutral"])
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(24)
        self.setStyleSheet(
            f"background:{background};color:{foreground};border:1px solid {border};"
            "border-radius:11px;padding:1px 9px;font-size:12px;font-weight:600;"
        )


def badge_cell(text: str, tone: str = "neutral") -> QWidget:
    """把状态标签居中放入表格单元格。"""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(6, 5, 6, 5)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(StatusBadge(text, tone))
    return container


def action_cell(*buttons: QPushButton, align_right: bool = False) -> QWidget:
    """创建不会被表格行高裁切的行内操作区。"""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(6)
    if align_right:
        layout.addStretch()
    for button in buttons:
        button.setObjectName("TableAction")
        button.setMinimumWidth(max(54, button.sizeHint().width() + 6))
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
    if not align_right:
        layout.addStretch()
    return container


def configure_table(table: QTableWidget, headers: Iterable[str]) -> None:
    """配置项目内一致的可读表格行为。"""
    header_list = list(headers)
    table.setColumnCount(len(header_list))
    table.setHorizontalHeaderLabels(header_list)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(52)
    table.verticalHeader().setMinimumSectionSize(52)
    table.horizontalHeader().setMinimumSectionSize(72)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setStretchLastSection(False)
    table.setShowGrid(False)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setSortingEnabled(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setFrameShape(QFrame.Shape.NoFrame)
