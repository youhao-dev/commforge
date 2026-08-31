"""可拖拽排序的报文规则编辑器。"""

import json
from collections.abc import Callable

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from commforge.core.enums import ChecksumType, CodecType, FieldType
from commforge.core.exceptions import ValidationError
from commforge.database.models import MessageRuleModel
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import Card, PageHeader, action_cell, configure_table


FIELD_META = {
    FieldType.FIXED: ("固定值", "输入固定的 HEX、文本或数值"),
    FieldType.TIME: ("时间", "当前时间与常用时间格式"),
    FieldType.CHANGE: ("变化值", "按规则连续变化的模拟数值"),
    FieldType.RANDOM: ("随机值", "每帧随机生成一个数值"),
    FieldType.SEQUENCE: ("序列值", "按照步长循环递增"),
    FieldType.LENGTH: ("长度", "计算指定字段范围字节数"),
    FieldType.CHECKSUM: ("校验", "生成 XOR、SUM 或 CRC 校验"),
    FieldType.RECEIVED_VALUE: ("接收值", "引用接收规则解析的字段"),
    FieldType.RECEIVED_BYTES: ("接收字节", "复制接收报文中的原始片段"),
}

FIELD_ICONS = {
    FieldType.FIXED: QStyle.StandardPixmap.SP_FileIcon,
    FieldType.TIME: QStyle.StandardPixmap.SP_BrowserReload,
    FieldType.CHANGE: QStyle.StandardPixmap.SP_ArrowUp,
    FieldType.RANDOM: QStyle.StandardPixmap.SP_DialogResetButton,
    FieldType.SEQUENCE: QStyle.StandardPixmap.SP_ArrowForward,
    FieldType.LENGTH: QStyle.StandardPixmap.SP_FileDialogDetailedView,
    FieldType.CHECKSUM: QStyle.StandardPixmap.SP_DialogApplyButton,
    FieldType.RECEIVED_VALUE: QStyle.StandardPixmap.SP_ArrowDown,
    FieldType.RECEIVED_BYTES: QStyle.StandardPixmap.SP_DialogSaveButton,
}

FIELD_CARD_COLORS = [
    ("#faf7ff", "#e3d9ff"), ("#f6fbf4", "#d8ecd1"),
    ("#fff8f1", "#f5ddc1"), ("#f2f8ff", "#d8e8fb"),
    ("#fff4f7", "#f4d7df"), ("#f2fbfb", "#d3e9e8"),
    ("#f4f8ff", "#d7e3fb"), ("#f1faf6", "#d1ebdc"),
    ("#f7f5ff", "#dfd8fb"),
]


class FieldTypeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("字段类型选择")
        self.setMinimumSize(720, 440)
        self.selected_type: FieldType | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        title = QLabel("字段类型选择")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        subtitle = QLabel("选择一种字段生成方式，添加后可继续配置输出编码")
        subtitle.setObjectName("Muted")
        root.addWidget(subtitle)
        grid = QGridLayout()
        grid.setSpacing(12)
        for index, (field_type, (name, description)) in enumerate(FIELD_META.items()):
            button = QPushButton(f"{name}\n{field_type.value}\n{description}")
            button.setMinimumSize(205, 92)
            background, border = FIELD_CARD_COLORS[index]
            button.setStyleSheet(
                f"text-align:left;padding:12px;line-height:1.5;background:{background};"
                f"border:1px solid {border};border-radius:8px;"
            )
            button.setIcon(self.style().standardIcon(FIELD_ICONS[field_type]))
            button.setIconSize(QSize(26, 26))
            button.clicked.connect(lambda _, value=field_type: self._choose(value))
            grid.addWidget(button, index // 3, index % 3)
        root.addLayout(grid)

    def _choose(self, field_type: FieldType) -> None:
        self.selected_type = field_type
        self.accept()


class FieldConfigPanel(Card):
    def __init__(self, on_save: Callable[[], None]) -> None:
        super().__init__("字段配置")
        self.field_id: int | None = None
        self.field_type: FieldType | None = None
        self._on_save = on_save
        self.enabled = QCheckBox("启用字段")
        self.enabled.setChecked(True)
        self.name = QLineEdit()
        self.codec = QComboBox()
        self.codec.addItems([item.value for item in CodecType])
        self.param_labels: list[QLabel] = []
        self.params: dict[str, QWidget] = {}
        self.form = QGridLayout()
        self.form.setVerticalSpacing(9)
        self.layout.addLayout(self.form)
        self._add_row("字段名称", self.name)
        self._add_row("输出编码", self.codec)
        self.layout.addWidget(self.enabled)
        self.save_button = QPushButton("保存字段配置")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(on_save)
        self.layout.addWidget(self.save_button)
        self.layout.addStretch()
        self.setMinimumWidth(340)

    def _add_row(self, text: str, widget: QWidget, dynamic: bool = False) -> None:
        label = QLabel(text)
        row = self.form.rowCount()
        self.form.addWidget(label, row, 0)
        self.form.addWidget(widget, row, 1)
        if dynamic:
            self.param_labels.append(label)

    def _clear_dynamic(self) -> None:
        for widget in self.params.values():
            self.form.removeWidget(widget)
            widget.hide()
            widget.deleteLater()
        for label in self.param_labels:
            self.form.removeWidget(label)
            label.hide()
            label.deleteLater()
        self.params.clear()
        self.param_labels.clear()

    def load_field(self, entity: object) -> None:
        """按字段类型生成紧凑配置表单。"""
        self._clear_dynamic()
        self.field_id = entity.id
        self.field_type = FieldType(entity.field_type)
        self.name.setText(entity.name)
        self.codec.setCurrentText(entity.codec_type)
        self.enabled.setChecked(entity.enabled)
        cfg = json.loads(entity.config_json or "{}")
        definitions: list[tuple[str, str, object, list[str] | None]] = []
        if self.field_type == FieldType.FIXED:
            definitions = [("value", "固定内容", cfg.get("value", "AA55"), None)]
        elif self.field_type == FieldType.TIME:
            definitions = [
                ("format", "时间格式", cfg.get("format", "yyyyMMddHHmmss"), [
                    "yyyyMMddHHmmss", "yyyyMMddHHmmssSSS", "yyyy-MM-dd HH:mm:ss",
                    "yyyyMMddHHmm", "HHmmss", "HH:mm:ss", "yyyy-MM-dd",
                    "Unix秒时间戳", "Unix毫秒时间戳"
                ]),
                ("offset", "时间偏移", cfg.get("offset", 0), None),
                ("offset_unit", "偏移单位", cfg.get("offset_unit", "seconds"), [
                    "milliseconds", "seconds", "minutes", "hours", "days"
                ]),
            ]
        elif self.field_type == FieldType.CHANGE:
            definitions = [
                ("initial", "初始值", cfg.get("initial", 25.0), None),
                ("mode", "变化模式", cfg.get("mode", "RANDOM_WALK"), [
                    "RANDOM_WALK", "INCREMENT", "DECREMENT", "LOOP", "BOUNCE"
                ]),
                ("step_min", "单次最小变化", cfg.get("step_min", -3), None),
                ("step_max", "单次最大变化", cfg.get("step_max", 3), None),
                ("min", "最小值", cfg.get("min", -40), None),
                ("max", "最大值", cfg.get("max", 60), None),
                ("scale", "倍率 Scale", cfg.get("scale", 10), None),
                ("precision", "小数位数", cfg.get("precision", 1), None),
                ("boundary", "越界处理", cfg.get("boundary", "BOUNCE"), ["CLAMP", "WRAP", "BOUNCE"]),
            ]
        elif self.field_type in (FieldType.RANDOM, FieldType.SEQUENCE):
            definitions = [
                ("initial", "初始值", cfg.get("initial", 0), None),
                ("step", "步长", cfg.get("step", 1), None),
                ("min", "最小值", cfg.get("min", 0), None),
                ("max", "最大值", cfg.get("max", 255), None),
                ("precision", "小数位数", cfg.get("precision", 0), None),
                ("scale", "倍率 Scale", cfg.get("scale", 1), None),
            ]
        elif self.field_type in (FieldType.LENGTH, FieldType.CHECKSUM):
            if self.field_type == FieldType.CHECKSUM:
                definitions.append(("algorithm", "校验算法", cfg.get("algorithm", "CRC16_MODBUS"), [item.value for item in ChecksumType]))
            definitions.extend([
                ("start", "起始字段索引", cfg.get("start", 0), None),
                ("end", "结束字段索引", cfg.get("end", 0), None),
            ])
        elif self.field_type == FieldType.RECEIVED_VALUE:
            definitions = [
                ("source", "接收字段名", cfg.get("source", "address"), None),
                ("default", "默认值", cfg.get("default", 0), None),
                ("scale", "倍率 Scale", cfg.get("scale", 1), None),
            ]
        else:
            definitions = [
                ("start", "开始索引", cfg.get("start", 0), None),
                ("length", "复制长度", cfg.get("length", 1), None),
            ]

        for key, label, value, choices in definitions:
            if choices:
                widget = QComboBox()
                widget.addItems(choices)
                widget.setCurrentText(str(value))
            else:
                widget = QLineEdit(str(value))
            self.params[key] = widget
            self._add_row(label, widget, True)

    def config(self) -> dict[str, object]:
        """把表单值转换为 JSON 可序列化配置。"""
        result: dict[str, object] = {}
        numeric_keys = {
            "initial", "step", "step_min", "step_max", "min", "max", "scale",
            "precision", "offset", "start", "end", "length", "default"
        }
        for key, widget in self.params.items():
            text = widget.currentText() if isinstance(widget, QComboBox) else widget.text().strip()
            if key in numeric_keys:
                try:
                    number = float(text)
                    result[key] = int(number) if number.is_integer() else number
                except ValueError as exc:
                    raise ValidationError(f"{key} 必须是数值") from exc
            else:
                result[key] = text
        return result


class MessageRuleEditorWidget(QWidget):
    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        self.current_rule_id: int | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(12)
        self.header = PageHeader("报文规则", "拖拽字段构建真实 byte[] 报文")
        self.rule_combo = QComboBox()
        self.rule_combo.setMinimumWidth(210)
        self.rule_combo.currentIndexChanged.connect(self._rule_changed)
        self.header.actions.addWidget(self.rule_combo)
        self.header.add_action("＋ 新建规则", self.add_rule, True)
        self.header.add_action("删除规则", self.delete_rule)
        root.addWidget(self.header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        fields_card = Card("字段列表（拖拽排序）")
        toolbar = QHBoxLayout()
        add_button = QPushButton("＋ 添加字段")
        add_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(self.add_field)
        toolbar.addWidget(add_button)
        for text, callback in [("复制", self.copy_field), ("删除", self.delete_field), ("↑", self.move_up), ("↓", self.move_down)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        fields_card.layout.addLayout(toolbar)
        self.field_list = QListWidget()
        self.field_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.field_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.field_list.currentItemChanged.connect(self._field_changed)
        self.field_list.model().rowsMoved.connect(lambda *_: self._save_order())
        fields_card.layout.addWidget(self.field_list)
        fields_card.setMinimumWidth(270)
        splitter.addWidget(fields_card)

        self.config_panel = FieldConfigPanel(self.save_field)
        splitter.addWidget(self.config_panel)

        preview_card = Card("报文预览")
        buttons = QHBoxLayout()
        for text, callback, primary in [
            ("生成一次", self.refresh_preview, True),
            ("连续 5 次", self.generate_five, False),
            ("复制 HEX", self.copy_hex, False),
            ("复制 ASCII", self.copy_ascii, False),
        ]:
            button = QPushButton(text)
            if primary:
                button.setObjectName("PrimaryButton")
            button.clicked.connect(callback)
            buttons.addWidget(button)
        preview_card.layout.addLayout(buttons)
        self.preview_tabs = QTabWidget()
        self.hex_preview = QPlainTextEdit()
        self.ascii_preview = QPlainTextEdit()
        self.hex_preview.setReadOnly(True)
        self.ascii_preview.setReadOnly(True)
        self.preview_tabs.addTab(self.hex_preview, "HEX")
        self.preview_tabs.addTab(self.ascii_preview, "ASCII")
        preview_card.layout.addWidget(self.preview_tabs)
        self.byte_count = QLabel("总字节数：0")
        self.byte_count.setObjectName("Muted")
        preview_card.layout.addWidget(self.byte_count)
        self.test_table = QTableWidget()
        configure_table(self.test_table, ["#", "HEX", "ASCII", "长度"])
        self.test_table.setMinimumHeight(190)
        preview_card.layout.addWidget(self.test_table)
        splitter.addWidget(preview_card)
        splitter.setSizes([310, 370, 520])
        root.addWidget(splitter, 1)
        self.reload_rules()

    def reload_rules(self) -> None:
        previous = self.current_rule_id
        self.rule_combo.blockSignals(True)
        self.rule_combo.clear()
        for rule in self.services.list_rules_with_fields():
            self.rule_combo.addItem(rule.name, rule.id)
        self.rule_combo.blockSignals(False)
        target = self.rule_combo.findData(previous) if previous else 0
        self.rule_combo.setCurrentIndex(max(0, target))
        self._rule_changed()

    def _rule_changed(self) -> None:
        self.current_rule_id = self.rule_combo.currentData()
        self.reload_fields()

    def reload_fields(self) -> None:
        self.field_list.clear()
        rule = self.services.get_rule(self.current_rule_id) if self.current_rule_id else None
        if not rule:
            return
        for index, field in enumerate(rule.fields, 1):
            item = QListWidgetItem(
                f"{index:02d}   {field.name}\n       {field.field_type}  ·  {field.codec_type}"
            )
            item.setIcon(self.style().standardIcon(FIELD_ICONS[FieldType(field.field_type)]))
            item.setData(Qt.ItemDataRole.UserRole, field.id)
            item.setSizeHint(QSize(0, 58))
            self.field_list.addItem(item)
        if self.field_list.count():
            self.field_list.setCurrentRow(0)
        self.refresh_preview()

    def _field_changed(self, current: QListWidgetItem | None) -> None:
        if not current:
            return
        entity = self.services.get_message_field(current.data(Qt.ItemDataRole.UserRole))
        if entity:
            self.config_panel.load_field(entity)

    def add_rule(self) -> None:
        index = len(self.services.message_rules.list_all()) + 1
        rule = self.services.message_rules.add(MessageRuleModel(name=f"新报文规则 {index}"))
        self.current_rule_id = rule.id
        self.reload_rules()

    def delete_rule(self) -> None:
        if not self.current_rule_id:
            return
        if QMessageBox.question(self, "删除规则", "确定删除当前报文规则吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.services.message_rules.delete(self.current_rule_id)
            self.current_rule_id = None
            self.reload_rules()
        except Exception as exc:
            QMessageBox.warning(self, "无法删除", str(exc))

    def add_field(self) -> None:
        if not self.current_rule_id:
            return
        dialog = FieldTypeDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.selected_type is None:
            return
        field_type = dialog.selected_type
        default_codec = {
            FieldType.FIXED: CodecType.HEX_BYTES,
            FieldType.TIME: CodecType.ASCII,
            FieldType.CHANGE: CodecType.INT16_BE,
            FieldType.RANDOM: CodecType.UINT16_BE,
            FieldType.SEQUENCE: CodecType.UINT8,
            FieldType.LENGTH: CodecType.UINT8,
            FieldType.CHECKSUM: CodecType.UINT16_LE,
            FieldType.RECEIVED_VALUE: CodecType.UINT8,
            FieldType.RECEIVED_BYTES: CodecType.RAW_BYTES,
        }[field_type]
        default_config = {
            FieldType.FIXED: {"value": "AA55"},
            FieldType.TIME: {"format": "yyyyMMddHHmmss"},
            FieldType.CHANGE: {"initial": 25, "mode": "RANDOM_WALK", "step_min": -3, "step_max": 3, "min": -40, "max": 60, "scale": 10, "precision": 1, "boundary": "BOUNCE"},
            FieldType.RANDOM: {"min": 0, "max": 100, "precision": 0, "scale": 1},
            FieldType.SEQUENCE: {"initial": 0, "step": 1, "min": 0, "max": 255},
            FieldType.LENGTH: {"start": 0, "end": 0},
            FieldType.CHECKSUM: {"algorithm": "CRC16_MODBUS", "start": 0, "end": 0},
            FieldType.RECEIVED_VALUE: {"source": "address", "default": 0, "scale": 1},
            FieldType.RECEIVED_BYTES: {"start": 0, "length": 1},
        }[field_type]
        self.services.add_message_field(
            self.current_rule_id, FIELD_META[field_type][0], field_type.value,
            default_codec.value, default_config
        )
        self.reload_fields()
        self.field_list.setCurrentRow(self.field_list.count() - 1)

    def save_field(self) -> None:
        if not self.config_panel.field_id:
            return
        try:
            self.services.update_message_field(
                self.config_panel.field_id,
                name=self.config_panel.name.text().strip() or "未命名字段",
                codec_type=self.config_panel.codec.currentText(),
                config=self.config_panel.config(),
                enabled=self.config_panel.enabled.isChecked(),
            )
            row = self.field_list.currentRow()
            self.reload_fields()
            self.field_list.setCurrentRow(max(0, row))
        except Exception as exc:
            QMessageBox.warning(self, "配置错误", str(exc))

    def copy_field(self) -> None:
        current = self.field_list.currentItem()
        if not current or not self.current_rule_id:
            return
        entity = self.services.get_message_field(current.data(Qt.ItemDataRole.UserRole))
        if entity:
            self.services.add_message_field(
                self.current_rule_id, f"{entity.name} 副本", entity.field_type,
                entity.codec_type, json.loads(entity.config_json or "{}")
            )
            self.reload_fields()

    def delete_field(self) -> None:
        current = self.field_list.currentItem()
        if current:
            self.services.delete_message_field(current.data(Qt.ItemDataRole.UserRole))
            self.reload_fields()

    def move_up(self) -> None:
        row = self.field_list.currentRow()
        if row > 0:
            item = self.field_list.takeItem(row)
            self.field_list.insertItem(row - 1, item)
            self.field_list.setCurrentRow(row - 1)
            self._save_order()

    def move_down(self) -> None:
        row = self.field_list.currentRow()
        if 0 <= row < self.field_list.count() - 1:
            item = self.field_list.takeItem(row)
            self.field_list.insertItem(row + 1, item)
            self.field_list.setCurrentRow(row + 1)
            self._save_order()

    def _save_order(self) -> None:
        if not self.current_rule_id:
            return
        ids = [self.field_list.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.field_list.count())]
        self.services.save_field_order(self.current_rule_id, ids)

    def refresh_preview(self) -> None:
        if not self.current_rule_id:
            return
        try:
            data = self.services.preview_rule(self.current_rule_id)
            self.hex_preview.setPlainText(data.hex(" ").upper())
            self.ascii_preview.setPlainText("".join(chr(value) if 32 <= value < 127 else "." for value in data))
            self.byte_count.setText(f"总字节数：{len(data)}")
        except Exception as exc:
            self.hex_preview.setPlainText(f"预览失败：{exc}")
            self.ascii_preview.clear()
            self.byte_count.setText("总字节数：0")

    def generate_five(self) -> None:
        if not self.current_rule_id:
            return
        rows: list[bytes] = []
        try:
            for _ in range(5):
                rows.append(self.services.preview_rule(self.current_rule_id, "rule-test"))
        except Exception as exc:
            QMessageBox.warning(self, "生成失败", str(exc))
            return
        self.test_table.setRowCount(len(rows))
        for row, data in enumerate(rows):
            values = [
                str(row + 1), data.hex(" ").upper(),
                "".join(chr(item) if 32 <= item < 127 else "." for item in data), str(len(data))
            ]
            for column, value in enumerate(values):
                self.test_table.setItem(row, column, QTableWidgetItem(value))

    def copy_hex(self) -> None:
        QGuiApplication.clipboard().setText(self.hex_preview.toPlainText())

    def copy_ascii(self) -> None:
        QGuiApplication.clipboard().setText(self.ascii_preview.toPlainText())


class MessageRuleEditorDialog(QDialog):
    """在独立窗口中编辑单条报文规则和字段。"""

    def __init__(
        self,
        services: ApplicationServices,
        rule_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.services = services
        self.rule_id = rule_id
        rule = services.get_rule(rule_id)
        self.setWindowTitle(f"报文规则 · {rule.name if rule else ''}")
        self.resize(1360, 820)
        self.setMinimumSize(1080, 680)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        top = QFrame()
        top.setObjectName("DialogSection")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(16, 12, 16, 12)
        title_box = QVBoxLayout()
        title = QLabel("报文规则编辑器")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("拖拽字段排序，右侧实时生成 HEX / ASCII 预览")
        subtitle.setObjectName("Muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top_layout.addLayout(title_box)
        top_layout.addSpacing(22)
        form = QFormLayout()
        self.name = QLineEdit(rule.name if rule else "")
        self.name.setMinimumWidth(260)
        self.description = QLineEdit(rule.description if rule else "")
        self.description.setPlaceholderText("简短说明这条规则的用途")
        self.description.setMinimumWidth(330)
        form.addRow("规则名称", self.name)
        form.addRow("说明", self.description)
        top_layout.addLayout(form, 1)
        self.save_button = QPushButton("保存规则")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save_rule)
        top_layout.addWidget(self.save_button)
        root.addWidget(top)

        self.editor = MessageRuleEditorWidget(services)
        self.editor.header.hide()
        index = self.editor.rule_combo.findData(rule_id)
        if index >= 0:
            self.editor.rule_combo.setCurrentIndex(index)
        self.editor.current_rule_id = rule_id
        self.editor.reload_fields()
        root.addWidget(self.editor, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def save_rule(self) -> None:
        """保存规则名称和说明；字段由编辑器各操作即时保存。"""
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "规则名称不能为空")
            return
        try:
            self.services.message_rules.update(
                self.rule_id, name=name, description=self.description.text().strip()
            )
            self.setWindowTitle(f"报文规则 · {name}")
            self.save_button.setText("已保存")
            QTimer.singleShot(1200, lambda: self.save_button.setText("保存规则"))
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))


class MessageRulesPage(QWidget):
    """报文规则列表页；详细内容只在新增或编辑时打开。"""

    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)
        header = PageHeader("报文规则", "集中管理所有报文结构和字段配置")
        header.add_action("＋ 新建规则", self.add_rule, True)
        header.add_action("编辑", self.edit_rule)
        header.add_action("复制", self.copy_rule)
        header.add_action("删除", self.delete_rule)
        root.addWidget(header)
        card = Card()
        card.layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        configure_table(
            self.table,
            ["规则名称", "说明", "字段数", "字段构成", "预览长度", "更新时间", "操作"],
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 176)
        self.table.doubleClicked.connect(self.edit_rule)
        card.layout.addWidget(self.table)
        root.addWidget(card, 1)
        self.refresh()

    def refresh(self) -> None:
        """把每条规则呈现为独立行，并显示结构摘要。"""
        rules = self.services.list_rules_with_fields()
        self.table.setRowCount(0)
        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            types = []
            for field in rule.fields:
                if field.field_type not in types:
                    types.append(field.field_type)
            try:
                preview_length = len(self.services.preview_rule(rule.id, f"rule-list-{rule.id}"))
            except Exception:
                preview_length = 0
            values = [
                rule.name,
                rule.description or "—",
                str(len(rule.fields)),
                " · ".join(types[:4]) + (" …" if len(types) > 4 else ""),
                f"{preview_length} bytes",
                rule.updated_at.strftime("%Y-%m-%d %H:%M"),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, rule.id)
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
            self.table.setCellWidget(row, 6, self._action_cell(row))
        if rules:
            self.table.selectRow(0)

    def _action_cell(self, row: int) -> QWidget:
        edit = QPushButton("编辑")
        edit.clicked.connect(lambda: self._run_for_row(row, self.edit_rule))
        copy = QPushButton("复制")
        copy.clicked.connect(lambda: self._run_for_row(row, self.copy_rule))
        return action_cell(edit, copy)

    def _run_for_row(self, row: int, callback: object) -> None:
        self.table.selectRow(row)
        callback()

    def selected_id(self) -> int | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _unique_name(self, base: str) -> str:
        existing = {rule.name for rule in self.services.message_rules.list_all()}
        if base not in existing:
            return base
        index = 2
        while f"{base} {index}" in existing:
            index += 1
        return f"{base} {index}"

    def add_rule(self) -> None:
        name = self._unique_name("新报文规则")
        rule = self.services.message_rules.add(
            MessageRuleModel(name=name, description="新建的报文规则")
        )
        dialog = MessageRuleEditorDialog(self.services, rule.id, self)
        dialog.exec()
        self.refresh()

    def edit_rule(self) -> None:
        rule_id = self.selected_id()
        if not rule_id:
            return
        MessageRuleEditorDialog(self.services, rule_id, self).exec()
        self.refresh()

    def copy_rule(self) -> None:
        rule_id = self.selected_id()
        rule = self.services.get_rule(rule_id) if rule_id else None
        if not rule:
            return
        self.services.copy_message_rule(rule.id, self._unique_name(f"{rule.name} 副本"))
        self.refresh()

    def delete_rule(self) -> None:
        rule_id = self.selected_id()
        if not rule_id:
            return
        if QMessageBox.question(
            self, "删除规则", "确定删除选中的报文规则吗？"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.services.message_rules.delete(rule_id)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "无法删除", str(exc))
