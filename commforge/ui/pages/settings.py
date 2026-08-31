"""应用设置页面。"""

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from commforge.app.paths import DATABASE_PATH, LOG_PATH
from commforge.ui.widgets.common import Card, PageHeader


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)
        root.addWidget(PageHeader("设置", "界面、日志与运行参数"))
        card = Card("通用设置")
        form = QFormLayout()
        theme = QComboBox()
        theme.addItems(["浅色主题"])
        log_limit = QSpinBox()
        log_limit.setRange(100, 50_000)
        log_limit.setValue(5000)
        auto_scroll = QCheckBox("新日志到达时自动滚动")
        auto_scroll.setChecked(True)
        form.addRow("界面主题", theme)
        form.addRow("界面日志上限", log_limit)
        form.addRow("", auto_scroll)
        form.addRow("数据库位置", QLabel(str(DATABASE_PATH)))
        form.addRow("文件日志位置", QLabel(str(LOG_PATH)))
        card.layout.addLayout(form)
        root.addWidget(card)
        root.addStretch()
