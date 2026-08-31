"""自动化任务配置、启停与即时执行页面。"""

import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from commforge.automation.engine import AutomationEngine
from commforge.core.enums import TaskTargetType, TriggerType
from commforge.database.models import AutomationTaskModel
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import (
    Card,
    PageHeader,
    action_cell,
    badge_cell,
    configure_table,
)


TRIGGER_LABELS = {
    TriggerType.TIMER.value: "定时触发",
    TriggerType.RECEIVE.value: "收到报文",
    TriggerType.MANUAL.value: "手动执行",
    TriggerType.CONNECTED.value: "通信连接",
    TriggerType.DISCONNECTED.value: "通信断开",
}

TARGET_LABELS = {
    TaskTargetType.CURRENT_SOURCE.value: "当前来源",
    TaskTargetType.COMMUNICATION.value: "指定通信",
    TaskTargetType.TCP_CURRENT_SESSION.value: "当前 TCP 会话",
    TaskTargetType.TCP_ALL_SESSIONS.value: "全部 TCP 会话",
    TaskTargetType.UDP_CURRENT_REMOTE.value: "当前 UDP 远端",
}


class AutomationDialog(QDialog):
    """根据触发方式动态展示有效任务配置。"""

    def __init__(
        self,
        services: ApplicationServices,
        parent: QWidget | None = None,
        entity: AutomationTaskModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.services = services
        self.setWindowTitle("自动化任务")
        self.resize(760, 560)
        self.setMinimumSize(680, 520)
        config = json.loads(entity.config_json or "{}") if entity else {}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel("编辑自动化任务" if entity else "新建自动化任务")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("只显示当前触发方式与目标类型需要的配置")
        subtitle.setObjectName("Muted")
        root.addWidget(title)
        root.addWidget(subtitle)

        columns = QHBoxLayout()
        columns.setSpacing(14)
        basic = Card("任务与触发")
        self.basic_form = QFormLayout()
        self.basic_form.setHorizontalSpacing(14)
        self.basic_form.setVerticalSpacing(12)
        self.name = QLineEdit(entity.name if entity else "")
        self.name.setPlaceholderText("例如：TCP01 心跳包")
        self.trigger = QComboBox()
        for value, label in TRIGGER_LABELS.items():
            self.trigger.addItem(label, value)
        self.communication = QComboBox()
        self.communication.addItem("— 未指定", None)
        for item in services.communications.list_all():
            self.communication.addItem(item.name, item.id)
        self.receive_rule = QComboBox()
        self.receive_rule.addItem("— 不使用接收规则", None)
        for item in services.receive_rules.list_all():
            self.receive_rule.addItem(item.name, item.id)
        self.interval = QSpinBox()
        self.interval.setRange(20, 86_400_000)
        self.interval.setValue(int(config.get("interval_ms", 1000)))
        self.interval.setSuffix(" ms")
        self.enabled = QCheckBox("保存后立即启用")
        self.enabled.setChecked(entity.enabled if entity else True)
        self.basic_form.addRow("任务名称", self.name)
        self.basic_form.addRow("触发方式", self.trigger)
        self.basic_form.addRow("来源通信", self.communication)
        self.basic_form.addRow("接收规则", self.receive_rule)
        self.basic_form.addRow("执行周期", self.interval)
        self.basic_form.addRow("", self.enabled)
        basic.layout.addLayout(self.basic_form)
        basic.layout.addStretch()
        columns.addWidget(basic, 1)

        action = Card("发送动作")
        self.action_form = QFormLayout()
        self.action_form.setHorizontalSpacing(14)
        self.action_form.setVerticalSpacing(12)
        self.message_rule = QComboBox()
        for item in services.message_rules.list_all():
            self.message_rule.addItem(item.name, item.id)
        self.target_type = QComboBox()
        for value, label in TARGET_LABELS.items():
            self.target_type.addItem(label, value)
        self.target_communication = QComboBox()
        self.target_communication.addItem("— 未指定", None)
        for item in services.communications.list_all():
            self.target_communication.addItem(item.name, item.id)
        self.delay = QSpinBox()
        self.delay.setRange(0, 60_000)
        self.delay.setValue(int(config.get("delay_ms", 0)))
        self.delay.setSuffix(" ms")
        self.action_form.addRow("发送规则", self.message_rule)
        self.action_form.addRow("发送目标", self.target_type)
        self.action_form.addRow("目标通信", self.target_communication)
        self.action_form.addRow("发送延迟", self.delay)
        action.layout.addLayout(self.action_form)
        note = QLabel("接收触发可将回复发送到当前 TCP 会话或 UDP 远端；定时任务通常发送到指定通信。")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        action.layout.addWidget(note)
        action.layout.addStretch()
        columns.addWidget(action, 1)
        root.addLayout(columns, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存任务")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        if entity:
            self._set_combo(self.trigger, entity.trigger_type)
            self._set_combo(self.communication, entity.communication_id)
            self._set_combo(self.receive_rule, entity.receive_rule_id)
            self._set_combo(self.message_rule, entity.message_rule_id)
            self._set_combo(self.target_type, entity.target_type)
            self._set_combo(self.target_communication, entity.target_communication_id)
        self.trigger.currentIndexChanged.connect(self._sync_fields)
        self.target_type.currentIndexChanged.connect(self._sync_fields)
        self._sync_fields()

    @staticmethod
    def _set_combo(combo: QComboBox, value: object) -> None:
        """按 data 而非显示文本恢复下拉框值。"""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _set_form_row_visible(form: QFormLayout, widget: QWidget, visible: bool) -> None:
        """同步隐藏表单标签和字段，避免留下空白行。"""
        label = form.labelForField(widget)
        if label:
            label.setVisible(visible)
        widget.setVisible(visible)

    def _sync_fields(self) -> None:
        """仅展示当前触发类型和目标需要的配置。"""
        trigger = self.trigger.currentData()
        needs_source = trigger in {
            TriggerType.RECEIVE.value,
            TriggerType.CONNECTED.value,
            TriggerType.DISCONNECTED.value,
        }
        self._set_form_row_visible(self.basic_form, self.communication, needs_source)
        self._set_form_row_visible(
            self.basic_form, self.receive_rule, trigger == TriggerType.RECEIVE.value
        )
        self._set_form_row_visible(
            self.basic_form, self.interval, trigger == TriggerType.TIMER.value
        )
        needs_target = self.target_type.currentData() in {
            TaskTargetType.COMMUNICATION.value,
            TaskTargetType.TCP_ALL_SESSIONS.value,
        }
        self._set_form_row_visible(self.action_form, self.target_communication, needs_target)

    def _validate(self) -> None:
        """校验任务执行所需的最小配置。"""
        if not self.name.text().strip() or self.message_rule.currentData() is None:
            QMessageBox.warning(self, "输入错误", "任务名称和发送规则不能为空")
            return
        if self.communication.isVisible() and self.communication.currentData() is None:
            QMessageBox.warning(self, "输入错误", "当前触发方式必须选择来源通信")
            return
        if self.target_communication.isVisible() and self.target_communication.currentData() is None:
            QMessageBox.warning(self, "输入错误", "当前发送目标必须选择目标通信")
            return
        self.accept()

    def values(self) -> dict[str, object]:
        """输出与数据库任务模型一致的配置。"""
        return {
            "name": self.name.text().strip(),
            "enabled": self.enabled.isChecked(),
            "trigger_type": self.trigger.currentData(),
            "communication_id": self.communication.currentData(),
            "receive_rule_id": self.receive_rule.currentData(),
            "message_rule_id": self.message_rule.currentData(),
            "target_type": self.target_type.currentData(),
            "target_communication_id": self.target_communication.currentData(),
            "config_json": json.dumps(
                {"interval_ms": self.interval.value(), "delay_ms": self.delay.value()}
            ),
        }


class AutomationPage(QWidget):
    """提供可直接操作且带执行反馈的自动化任务列表。"""

    def __init__(self, services: ApplicationServices, engine: AutomationEngine) -> None:
        super().__init__()
        self.services = services
        self.engine = engine
        self.last_results: dict[int, tuple[bool, str]] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)
        header = PageHeader("自动化任务", "统一管理定时发送、接收响应和手动任务")
        header.add_action("＋ 新建任务", self.add_task, True)
        header.add_action("编辑", self.edit_task)
        header.add_action("启用 / 停用", self.toggle_task)
        header.add_action("立即执行", self.run_task)
        header.add_action("删除", self.delete_task)
        root.addWidget(header)

        card = Card()
        card.layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        configure_table(
            self.table,
            ["启用", "任务名称", "触发方式", "来源通信", "规则链路", "发送目标", "运行状态", "操作"],
        )
        table_header = self.table.horizontalHeader()
        for column in (2,):
            table_header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        table_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        table_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 88)
        self.table.setColumnWidth(6, 104)
        self.table.setColumnWidth(7, 224)
        self.table.doubleClicked.connect(self.edit_task)
        card.layout.addWidget(self.table)
        root.addWidget(card, 1)
        self.feedback = QLabel("选择任务后可编辑、启停或立即执行")
        self.feedback.setObjectName("Muted")
        root.addWidget(self.feedback)
        self.engine.task_executed.connect(self._task_result)
        self.refresh()

    def refresh(self) -> None:
        """刷新任务摘要、状态标签和行内操作。"""
        tasks = self.services.automations.list_all()
        communications = {item.id: item.name for item in self.services.communications.list_all()}
        message_rules = {item.id: item.name for item in self.services.message_rules.list_all()}
        receive_rules = {item.id: item.name for item in self.services.receive_rules.list_all()}
        self.table.setRowCount(0)
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            rule_path = message_rules.get(task.message_rule_id, "规则已删除")
            if task.receive_rule_id:
                rule_path = f"{receive_rules.get(task.receive_rule_id, '接收规则已删除')} → {rule_path}"
            target_name = TARGET_LABELS.get(task.target_type, task.target_type)
            if task.target_communication_id:
                target_name = f"{target_name} · {communications.get(task.target_communication_id, '未知通信')}"
            values = [
                task.name,
                TRIGGER_LABELS.get(task.trigger_type, task.trigger_type),
                communications.get(task.communication_id, "—"),
                rule_path,
                target_name,
            ]
            for column, value in enumerate(values, 1):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, task.id)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    if column in (1, 4, 5)
                    else Qt.AlignmentFlag.AlignCenter
                )
                self.table.setItem(row, column, item)
            self.table.setCellWidget(
                row, 0, badge_cell("启用" if task.enabled else "停用", "success" if task.enabled else "neutral")
            )
            result = self.last_results.get(task.id)
            if result:
                status_text = "执行成功" if result[0] else "执行失败"
                status_tone = "success" if result[0] else "danger"
            else:
                status_text = "运行中" if task.enabled else "已停止"
                status_tone = "info" if task.enabled else "neutral"
            self.table.setCellWidget(row, 6, badge_cell(status_text, status_tone))
            toggle = QPushButton("停用" if task.enabled else "启用")
            toggle.clicked.connect(lambda _=False, current=row: self._run_for_row(current, self.toggle_task))
            execute = QPushButton("执行")
            execute.clicked.connect(lambda _=False, current=row: self._run_for_row(current, self.run_task))
            edit = QPushButton("编辑")
            edit.clicked.connect(lambda _=False, current=row: self._run_for_row(current, self.edit_task))
            self.table.setCellWidget(row, 7, action_cell(toggle, execute, edit))
        if tasks:
            self.table.selectRow(0)

    def _run_for_row(self, row: int, callback: object) -> None:
        """先选中操作所在行，再调用对应命令。"""
        self.table.selectRow(row)
        callback()

    def selected(self) -> AutomationTaskModel | None:
        """从实际存在的任务名称单元格读取任务编号。"""
        row = self.table.currentRow()
        item = self.table.item(row, 1) if row >= 0 else None
        return self.services.automations.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _require_selected(self) -> AutomationTaskModel | None:
        """统一提示未选择任务，避免按钮点击后毫无反馈。"""
        task = self.selected()
        if not task:
            QMessageBox.information(self, "请选择任务", "请先选择一条自动化任务")
        return task

    def _show_feedback(self, text: str, success: bool = True) -> None:
        """在页面底部展示短时操作结果。"""
        self.feedback.setText(text)
        self.feedback.setStyleSheet(f"color:{'#278a50' if success else '#c93f4a'};font-weight:600;")
        QTimer.singleShot(5000, lambda: self.feedback.setStyleSheet(""))

    def add_task(self) -> None:
        """创建任务并同步注册定时器。"""
        dialog = AutomationDialog(self.services, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                task = self.services.automations.add(AutomationTaskModel(**dialog.values()))
                if task.enabled and task.trigger_type == TriggerType.TIMER.value:
                    self.engine.start_task(task)
                self.refresh()
                self._show_feedback(f"已创建任务：{task.name}")
            except Exception as exc:
                QMessageBox.warning(self, "创建失败", str(exc))

    def edit_task(self) -> None:
        """编辑任务，并按新配置重新注册定时器。"""
        task = self._require_selected()
        if not task:
            return
        dialog = AutomationDialog(self.services, self, task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.engine.stop_task(task.id)
                updated = self.services.automations.update(task.id, **dialog.values())
                if updated.enabled and updated.trigger_type == TriggerType.TIMER.value:
                    self.engine.start_task(updated)
                self.refresh()
                self._show_feedback(f"已保存任务：{updated.name}")
            except Exception as exc:
                QMessageBox.warning(self, "保存失败", str(exc))

    def toggle_task(self) -> None:
        """立即启用或停用所选任务。"""
        task = self._require_selected()
        if not task:
            return
        updated = self.services.automations.update(task.id, enabled=not task.enabled)
        if updated.enabled and updated.trigger_type == TriggerType.TIMER.value:
            self.engine.start_task(updated)
        else:
            self.engine.stop_task(task.id)
        self.refresh()
        self._show_feedback(f"{updated.name} 已{'启用' if updated.enabled else '停用'}")

    def run_task(self) -> None:
        """手动执行一次任务，并等待引擎回传结果。"""
        task = self._require_selected()
        if not task:
            return
        self.feedback.setText(f"正在执行：{task.name} …")
        self.feedback.setStyleSheet("color:#3975d2;font-weight:600;")
        self.engine.execute(task.id)

    def _task_result(self, task_id: int, success: bool, message: str) -> None:
        """记录引擎执行结果并更新对应状态标签。"""
        self.last_results[task_id] = (success, message)
        task = self.services.automations.get(task_id)
        name = task.name if task else f"任务 {task_id}"
        self.refresh()
        self._show_feedback(
            f"{name}：{'执行成功' if success else '执行失败'}{'' if success else f' · {message}'}",
            success,
        )

    def delete_task(self) -> None:
        """确认后停止并删除所选任务。"""
        task = self._require_selected()
        if not task:
            return
        if QMessageBox.question(self, "删除任务", f"确定删除“{task.name}”吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.engine.stop_task(task.id)
            self.services.automations.delete(task.id)
            self.last_results.pop(task.id, None)
            self.refresh()
            self._show_feedback(f"已删除任务：{task.name}")
        except Exception as exc:
            QMessageBox.warning(self, "删除失败", str(exc))
