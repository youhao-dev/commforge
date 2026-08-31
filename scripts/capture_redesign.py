"""离屏渲染全部页面和关键弹窗，用于界面回归检查。"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget

from commforge.app.bootstrap import create_application
from commforge.automation.engine import AutomationEngine
from commforge.communication.manager import CommunicationManager
from commforge.ui.pages.automation import AutomationDialog
from commforge.ui.pages.receive_rules import ReceiveRuleEditorDialog


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "images"


def _render_widget(app: QApplication, widget: object, filename: str) -> None:
    """显示并稳定处理事件后保存窗口截图。"""
    widget.show()
    for _ in range(4):
        app.processEvents()
    widget.grab().save(str(OUTPUT_DIR / filename))


def _assert_table_headers_centered(page: object) -> None:
    """验证当前页面的所有表头都采用水平居中。"""
    for table in page.findChildren(QTableWidget):
        alignment = table.horizontalHeader().defaultAlignment()
        assert alignment & Qt.AlignmentFlag.AlignHCenter, "发现未居中的表头"


def _assert_buttons_visible(page: object) -> None:
    """检查可见按钮的实际尺寸足以容纳其最小高度和文本宽度。"""
    failures: list[str] = []
    for button in page.findChildren(QPushButton):
        if not button.isVisible() or not button.text().strip():
            continue
        if button.height() < button.minimumSizeHint().height():
            failures.append(f"{button.text()} 高度 {button.height()}")
        if button.width() + 2 < min(button.sizeHint().width(), button.minimumWidth() or 10_000):
            failures.append(f"{button.text()} 宽度 {button.width()}")
    assert not failures, "按钮显示不全：" + ", ".join(failures)


def main() -> int:
    """捕获全页面，并验证自动化按钮和接收规则测试链路。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # 视觉回归禁止打开真实端口或启动周期任务，所有外部动作都替换为本地反馈。
    CommunicationManager.open = lambda self, communication_id: None
    AutomationEngine.start_enabled = lambda self: None
    app, window = create_application([])
    window.resize(1440, 880)
    _render_widget(app, window, "qa-dashboard.png")
    page_names = [
        "dashboard",
        "communications",
        "message-rules",
        "receive-rules",
        "automation",
        "monitor",
        "logs",
        "settings",
    ]
    for index, name in enumerate(page_names):
        window._navigate(index)
        app.processEvents()
        page = window.page_widgets[index]
        _assert_table_headers_centered(page)
        _assert_buttons_visible(page)
        window.grab().save(str(OUTPUT_DIR / f"qa-{name}.png"))

    # 用户问题截图同时包含 1920 宽屏状态，单独验证接收规则和自动化表格的宽屏节奏。
    window.resize(1920, 994)
    for index, name in ((3, "receive-rules-wide"), (4, "automation-wide")):
        window._navigate(index)
        for _ in range(4):
            app.processEvents()
        page = window.page_widgets[index]
        _assert_table_headers_centered(page)
        _assert_buttons_visible(page)
        window.grab().save(str(OUTPUT_DIR / f"qa-{name}.png"))
    window.resize(1440, 880)

    receive_page = window.page_widgets[3]
    receive = receive_page.selected()
    if receive:
        editor = ReceiveRuleEditorDialog(window.services, window, receive)
        _render_widget(app, editor, "qa-receive-editor.png")
        editor.test_match()
        app.processEvents()
        assert "匹配成功" in editor.result.text(), editor.result.text()
        editor.grab().save(str(OUTPUT_DIR / "qa-receive-editor-tested.png"))
        editor.close()

    automation_page = window.page_widgets[4]
    automation_page.table.selectRow(0)
    task = automation_page.selected()
    assert task is not None, "自动化页面无法读取选中任务"
    automation_page.engine.start_task = lambda current: None
    automation_page.engine.stop_task = lambda task_id: None
    automation_page.engine.execute = lambda task_id: automation_page.engine.task_executed.emit(
        task_id, True, "界面回归模拟执行成功"
    )
    before = task.enabled
    try:
        automation_page.toggle_task()
        assert window.services.automations.get(task.id).enabled is not before, "启停按钮没有修改任务状态"
        automation_page.table.selectRow(0)
        automation_page.toggle_task()
        assert window.services.automations.get(task.id).enabled is before, "启停按钮没有恢复任务状态"
        automation_page.table.selectRow(0)
        automation_page.run_task()
        for _ in range(4):
            app.processEvents()
        assert task.id in automation_page.last_results, "立即执行按钮没有返回执行结果"
        dialog = AutomationDialog(window.services, window, window.services.automations.get(task.id))
        _render_widget(app, dialog, "qa-automation-editor.png")
        dialog.close()
    finally:
        # 即使断言失败，也恢复用户原有启停状态，视觉回归不污染真实配置。
        window.services.automations.update(task.id, enabled=before)

    window.close()
    app.processEvents()
    print("UI_REGRESSION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
