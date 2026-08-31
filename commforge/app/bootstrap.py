"""QApplication 启动入口。"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from commforge.services.application import ApplicationServices
from commforge.ui.main_window import MainWindow
from commforge.ui.styles.theme import LIGHT_THEME
from commforge.utils.logging import configure_logging


def create_application(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    """创建应用和主窗口，供 main 与启动测试复用。"""
    configure_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(argv or sys.argv)
    app.setApplicationName("CommForge")
    app.setOrganizationName("CommForge")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(LIGHT_THEME)
    services = ApplicationServices.create()
    window = MainWindow(services)
    return app, window


def run() -> int:
    """显示主窗口并进入 Qt 事件循环。"""
    app, window = create_application()
    window.show()
    return app.exec()
