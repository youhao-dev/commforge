"""接收匹配与字段解析规则页面。"""

from typing import Any

from PySide6.QtCore import Qt
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
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from commforge.core.enums import CodecType, MatchType
from commforge.database.models import ReceiveRuleModel
from commforge.receive.rules import ReceiveFieldSpec, ReceiveRule
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import (
    Card,
    PageHeader,
    action_cell,
    badge_cell,
    configure_table,
)


class ReceiveFieldDialog(QDialog):
    """编辑一个固定偏移解析字段。"""

    def __init__(self, parent: QWidget | None = None, value: dict[str, Any] | None = None) -> None:
        super().__init__(parent)
        value = value or {}
        self.setWindowTitle("解析字段")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        form.setContentsMargins(22, 22, 22, 18)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.name = QLineEdit(str(value.get("name", "address")))
        self.offset = QSpinBox()
        self.offset.setRange(0, 1_000_000)
        self.offset.setValue(int(value.get("offset", 0)))
        self.length = QSpinBox()
        self.length.setRange(1, 1_000_000)
        self.length.setValue(int(value.get("length", 1)))
        self.codec = QComboBox()
        self.codec.addItems([item.value for item in CodecType])
        self.codec.setCurrentText(str(value.get("codec_type", CodecType.UINT8.value)))
        self.expected = QLineEdit(str(value.get("expected_value") or ""))
        self.expected.setPlaceholderText("留空表示只解析、不校验")
        self.required = QCheckBox("数据不足时判定匹配失败")
        self.required.setChecked(bool(value.get("required", True)))
        for label, widget in [
            ("字段名称", self.name),
            ("字节偏移", self.offset),
            ("字段长度", self.length),
            ("输入编码", self.codec),
            ("期望值", self.expected),
            ("", self.required),
        ]:
            form.addRow(label, widget)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存字段")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate(self) -> None:
        """确保字段在进入规则快照前具有可读名称。"""
        if not self.name.text().strip():
            QMessageBox.warning(self, "输入错误", "字段名称不能为空")
            return
        self.accept()

    def values(self) -> dict[str, Any]:
        """返回可直接交给规则编辑器的字段快照。"""
        return {
            "name": self.name.text().strip(),
            "offset": self.offset.value(),
            "length": self.length.value(),
            "codec_type": self.codec.currentText(),
            "expected_value": self.expected.text().strip() or None,
            "required": self.required.isChecked(),
        }


class ReceiveRuleEditorDialog(QDialog):
    """把规则设置、解析字段和真实匹配测试放在同一编辑窗口。"""

    def __init__(
        self,
        services: ApplicationServices,
        parent: QWidget | None = None,
        entity: ReceiveRuleModel | None = None,
        focus_test: bool = False,
    ) -> None:
        super().__init__(parent)
        self.services = services
        self.rule_id = entity.id if entity else None
        detailed = services.get_receive_rule(entity.id) if entity else None
        self.fields: list[dict[str, Any]] = [
            {
                "name": field.name,
                "offset": field.offset,
                "length": field.length,
                "codec_type": field.codec_type,
                "expected_value": field.expected_value,
                "required": field.required,
            }
            for field in (detailed.fields if detailed else [])
        ]
        self.setWindowTitle("接收规则编辑器")
        self.resize(1280, 760)
        self.setMinimumSize(1020, 660)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("接收规则编辑器")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("定义帧匹配条件、解析字段，并在保存前验证真实 HEX 数据")
        subtitle.setObjectName("Muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        top.addLayout(title_box)
        top.addStretch()
        save = QPushButton("保存规则")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save_rule)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        top.addWidget(cancel)
        top.addWidget(save)
        root.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_rule_panel(entity))
        splitter.addWidget(self._build_fields_panel())
        splitter.addWidget(self._build_test_panel())
        splitter.setSizes([310, 500, 420])
        root.addWidget(splitter, 1)
        self._refresh_fields()
        if focus_test:
            self.test_input.setFocus()

    def _build_rule_panel(self, entity: ReceiveRuleModel | None) -> Card:
        """构建左侧规则基本信息区。"""
        card = Card("规则配置")
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        self.name = QLineEdit(entity.name if entity else "")
        self.name.setPlaceholderText("例如：设备状态上报")
        self.match_type = QComboBox()
        self.match_type.addItems([item.value for item in MatchType])
        self.pattern = QLineEdit(entity.pattern if entity else "AA 55 ?? 03")
        self.pattern.setPlaceholderText("HEX 模式可使用 ?? 通配一个字节")
        self.enabled = QCheckBox("启用此接收规则")
        self.enabled.setChecked(entity.enabled if entity else True)
        if entity:
            self.match_type.setCurrentText(entity.match_type)
        form.addRow("规则名称", self.name)
        form.addRow("匹配方式", self.match_type)
        form.addRow("匹配内容", self.pattern)
        form.addRow("", self.enabled)
        card.layout.addLayout(form)
        hint = QLabel(
            "匹配方式说明\n"
            "• HEX_PATTERN：按十六进制字节匹配，?? 表示任意字节\n"
            "• HEX_EXACT：报文必须完全一致\n"
            "• 文本模式：按解码后的字符串匹配"
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        card.layout.addWidget(hint)
        card.layout.addStretch()
        return card

    def _build_fields_panel(self) -> Card:
        """构建中间解析字段表与行级操作。"""
        card = Card("解析字段")
        actions = QHBoxLayout()
        add = QPushButton("＋ 添加字段")
        add.setObjectName("PrimaryButton")
        add.clicked.connect(self.add_field)
        edit = QPushButton("编辑字段")
        edit.clicked.connect(self.edit_field)
        delete = QPushButton("删除字段")
        delete.setObjectName("DangerButton")
        delete.clicked.connect(self.delete_field)
        actions.addWidget(add)
        actions.addWidget(edit)
        actions.addWidget(delete)
        actions.addStretch()
        card.layout.addLayout(actions)
        self.field_table = QTableWidget()
        configure_table(
            self.field_table,
            ["名称", "偏移", "长度", "编码", "期望值", "必需"],
        )
        self.field_table.doubleClicked.connect(self.edit_field)
        card.layout.addWidget(self.field_table)
        count = QLabel("解析字段按字节偏移读取；双击字段可修改")
        count.setObjectName("Muted")
        card.layout.addWidget(count)
        return card

    def _build_test_panel(self) -> Card:
        """构建右侧实时匹配与解析结果区。"""
        card = Card("匹配测试")
        label = QLabel("输入测试报文（HEX）")
        label.setObjectName("SectionTitle")
        card.layout.addWidget(label)
        self.test_input = QPlainTextEdit("AA 55 01 03")
        self.test_input.setPlaceholderText("例如：AA 55 01 03")
        self.test_input.setMaximumHeight(150)
        card.layout.addWidget(self.test_input)
        test = QPushButton("运行匹配测试")
        test.setObjectName("PrimaryButton")
        test.clicked.connect(self.test_match)
        card.layout.addWidget(test)
        self.result = QLabel("尚未测试")
        self.result.setObjectName("InfoPill")
        self.result.setWordWrap(True)
        card.layout.addWidget(self.result)
        parsed_title = QLabel("解析结果")
        parsed_title.setObjectName("SectionTitle")
        card.layout.addWidget(parsed_title)
        self.parsed_table = QTableWidget()
        configure_table(self.parsed_table, ["字段", "值"])
        card.layout.addWidget(self.parsed_table, 1)
        return card

    def _refresh_fields(self) -> None:
        """刷新编辑器中的本地字段快照。"""
        self.field_table.setRowCount(len(self.fields))
        for row, field in enumerate(self.fields):
            values = [
                str(field["name"]),
                str(field["offset"]),
                str(field["length"]),
                str(field["codec_type"]),
                str(field.get("expected_value") or "—"),
                "是" if field.get("required", True) else "否",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.field_table.setItem(row, column, item)

    def add_field(self) -> None:
        """添加字段到本地规则快照。"""
        dialog = ReceiveFieldDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.fields.append(dialog.values())
            self._refresh_fields()
            self.field_table.selectRow(len(self.fields) - 1)

    def edit_field(self) -> None:
        """修改当前字段，不立即写入数据库。"""
        row = self.field_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "请选择字段", "请先选择要编辑的解析字段")
            return
        dialog = ReceiveFieldDialog(self, self.fields[row])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.fields[row] = dialog.values()
            self._refresh_fields()
            self.field_table.selectRow(row)

    def delete_field(self) -> None:
        """从本地快照删除当前字段。"""
        row = self.field_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "请选择字段", "请先选择要删除的解析字段")
            return
        del self.fields[row]
        self._refresh_fields()

    def _build_rule(self) -> ReceiveRule:
        """把当前未保存表单转换为可执行规则。"""
        specs = [
            ReceiveFieldSpec(
                str(field["name"]),
                int(field["offset"]),
                int(field["length"]),
                CodecType(str(field["codec_type"])),
                field.get("expected_value"),
                bool(field.get("required", True)),
            )
            for field in self.fields
        ]
        return ReceiveRule(
            self.name.text().strip() or "未命名规则",
            MatchType(self.match_type.currentText()),
            self.pattern.text().strip(),
            specs,
        )

    def test_match(self) -> None:
        """使用当前表单即时测试，不要求先保存。"""
        self.parsed_table.setRowCount(0)
        try:
            data = bytes.fromhex(self.test_input.toPlainText().replace("\n", " "))
            rule = self._build_rule()
            matched = rule.matches(data)
            if not matched:
                self.result.setObjectName("ResultError")
                self.result.setText("未匹配：测试报文不满足当前规则")
            else:
                parsed = rule.parse(data).parsed_fields if self.fields else {}
                self.result.setObjectName("ResultSuccess")
                self.result.setText(f"匹配成功 · 共解析 {len(parsed)} 个字段")
                self.parsed_table.setRowCount(len(parsed))
                for row, (name, value) in enumerate(parsed.items()):
                    for column, text in enumerate((name, str(value))):
                        item = QTableWidgetItem(text)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.parsed_table.setItem(row, column, item)
            # 动态 objectName 后重新应用样式，确保结果状态立即变色。
            self.result.style().unpolish(self.result)
            self.result.style().polish(self.result)
        except Exception as exc:
            self.result.setObjectName("ResultError")
            self.result.setText(f"输入或规则错误：{exc}")
            self.result.style().unpolish(self.result)
            self.result.style().polish(self.result)

    def save_rule(self) -> None:
        """校验并一次性保存规则与解析字段。"""
        if not self.name.text().strip() or not self.pattern.text().strip():
            QMessageBox.warning(self, "输入错误", "规则名称和匹配内容不能为空")
            return
        try:
            self.services.save_receive_rule(
                self.rule_id,
                name=self.name.text().strip(),
                match_type=self.match_type.currentText(),
                pattern=self.pattern.text().strip(),
                enabled=self.enabled.isChecked(),
                fields=self.fields,
            )
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", str(exc))


class ReceiveRulesPage(QWidget):
    """接收规则列表页；新增、编辑和测试在独立窗口完成。"""

    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)
        header = PageHeader("接收规则", "集中管理帧匹配条件与字段解析方案")
        header.add_action("＋ 新建规则", self.add_rule, True)
        header.add_action("编辑", self.edit_rule)
        header.add_action("删除", self.delete_rule)
        root.addWidget(header)
        card = Card()
        card.layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        configure_table(
            self.table,
            ["规则名称", "匹配方式", "匹配内容", "解析字段", "状态", "更新时间", "操作"],
        )
        table_header = self.table.horizontalHeader()
        for column in (1, 3):
            table_header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        table_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        table_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(6, 176)
        self.table.doubleClicked.connect(self.edit_rule)
        card.layout.addWidget(self.table)
        root.addWidget(card, 1)
        self.refresh()

    def refresh(self) -> None:
        """将每条接收规则展示为一行清晰摘要。"""
        rules = self.services.receive_rules.list_all()
        self.table.setRowCount(0)
        self.table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            detailed = self.services.get_receive_rule(rule.id)
            values = [
                rule.name,
                rule.match_type,
                rule.pattern,
                f"{len(detailed.fields) if detailed else 0} 个字段",
                rule.updated_at.strftime("%Y-%m-%d %H:%M"),
            ]
            for column, value in enumerate(values[:4]):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, rule.id)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    if column in (0, 2)
                    else Qt.AlignmentFlag.AlignCenter
                )
                self.table.setItem(row, column, item)
            self.table.setCellWidget(
                row, 4, badge_cell("已启用" if rule.enabled else "已停用", "success" if rule.enabled else "neutral")
            )
            updated = QTableWidgetItem(values[4])
            updated.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, updated)
            edit = QPushButton("编辑")
            edit.clicked.connect(lambda _=False, current=row: self._run_for_row(current, self.edit_rule))
            test = QPushButton("测试")
            test.clicked.connect(lambda _=False, current=row: self._run_for_row(current, self.test_rule))
            self.table.setCellWidget(row, 6, action_cell(edit, test))
        if rules and self.table.currentRow() < 0:
            self.table.selectRow(0)

    def _run_for_row(self, row: int, callback: object) -> None:
        """先选择行，再执行行内操作。"""
        self.table.selectRow(row)
        callback()

    def selected(self) -> ReceiveRuleModel | None:
        """返回当前列表所选规则。"""
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return self.services.receive_rules.get(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def add_rule(self) -> None:
        """打开空白规则编辑器。"""
        if ReceiveRuleEditorDialog(self.services, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit_rule(self) -> None:
        """打开当前规则的完整编辑器。"""
        entity = self.selected()
        if not entity:
            QMessageBox.information(self, "请选择规则", "请先选择要编辑的接收规则")
            return
        if ReceiveRuleEditorDialog(self.services, self, entity).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def test_rule(self) -> None:
        """直接打开当前规则并将焦点放到测试报文。"""
        entity = self.selected()
        if entity:
            ReceiveRuleEditorDialog(self.services, self, entity, focus_test=True).exec()

    def delete_rule(self) -> None:
        """确认后删除当前规则。"""
        entity = self.selected()
        if not entity:
            QMessageBox.information(self, "请选择规则", "请先选择要删除的接收规则")
            return
        if QMessageBox.question(self, "删除接收规则", "确定删除当前规则吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.services.receive_rules.delete(entity.id)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "无法删除", str(exc))
