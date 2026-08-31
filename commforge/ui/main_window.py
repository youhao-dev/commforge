"""主窗口与左侧导航。"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from commforge import __version__
from commforge.automation.engine import AutomationEngine
from commforge.services.application import ApplicationServices
from commforge.ui.pages.automation import AutomationPage
from commforge.ui.pages.communications import CommunicationsPage
from commforge.ui.pages.dashboard import DashboardPage
from commforge.ui.pages.logs import LogsPage
from commforge.ui.pages.message_rules import MessageRulesPage
from commforge.ui.pages.monitor import MonitorPage
from commforge.ui.pages.receive_rules import ReceiveRulesPage
from commforge.ui.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        self.engine = AutomationEngine(services, self)
        self.setWindowTitle("CommForge · 通信报文构建与自动化")
        self.resize(1440, 880)
        self.setMinimumSize(1120, 700)
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        self.pages = QStackedWidget()
        self.page_widgets = [
            DashboardPage(services),
            CommunicationsPage(services),
            MessageRulesPage(services),
            ReceiveRulesPage(services),
            AutomationPage(services, self.engine),
            MonitorPage(services),
            LogsPage(services),
            SettingsPage(),
        ]
        for page in self.page_widgets:
            self.pages.addWidget(page)
        layout.addWidget(self.pages, 1)
        self.statusBar().showMessage("就绪 · 数据库与运行目录已初始化")
        services.manager.error_occurred.connect(
            lambda message: self.statusBar().showMessage(f"通信异常：{message}", 8000)
        )
        self.engine.start_enabled()

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(192)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 18, 12, 16)
        layout.setSpacing(7)
        brand = QHBoxLayout()
        brand_icon = QLabel()
        brand_icon.setPixmap(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon).pixmap(26, 26)
        )
        title = QLabel("CommForge")
        title.setObjectName("BrandTitle")
        brand.addWidget(brand_icon)
        brand.addWidget(title)
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(16)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        nav_items = [
            ("总览", QStyle.StandardPixmap.SP_DesktopIcon),
            ("通信管理", QStyle.StandardPixmap.SP_DriveNetIcon),
            ("报文规则", QStyle.StandardPixmap.SP_FileDialogDetailedView),
            ("接收规则", QStyle.StandardPixmap.SP_ArrowDown),
            ("自动化任务", QStyle.StandardPixmap.SP_MediaPlay),
            ("运行监控", QStyle.StandardPixmap.SP_ComputerIcon),
            ("收发日志", QStyle.StandardPixmap.SP_FileDialogContentsView),
            ("设置", QStyle.StandardPixmap.SP_FileDialogInfoView),
        ]
        for index, (text, icon_type) in enumerate(nav_items):
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setIcon(self.style().standardIcon(icon_type))
            button.setIconSize(QSize(18, 18))
            button.clicked.connect(lambda _, page=index: self._navigate(page))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)
        layout.addStretch()
        footer = QHBoxLayout()
        footer_icon = QLabel()
        footer_icon.setPixmap(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon).pixmap(22, 22)
        )
        footer_text = QVBoxLayout()
        footer_text.setSpacing(0)
        footer_text.addWidget(QLabel("CommForge"))
        version = QLabel(f"v{__version__}")
        version.setObjectName("Version")
        footer_text.addWidget(version)
        footer.addWidget(footer_icon)
        footer.addLayout(footer_text)
        footer.addStretch()
        layout.addLayout(footer)
        return sidebar

    def _navigate(self, index: int) -> None:
        """切换页面并在需要时刷新其数据。"""
        self.pages.setCurrentIndex(index)
        page = self.page_widgets[index]
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    def closeEvent(self, event: object) -> None:
        """按顺序停止调度器与所有通道，避免残留 Qt 对象。"""
        self.engine.shutdown()
        self.services.shutdown()
        event.accept()
