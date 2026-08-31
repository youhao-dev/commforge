"""通信配置与启停页面。"""

import json

from PySide6.QtCore import Qt
from PySide6.QtSerialPort import QSerialPortInfo
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QHeaderView, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from commforge.core.enums import CommunicationStatus, CommunicationType, FrameDecoderType
from commforge.database.models import CommunicationModel
from commforge.services.application import ApplicationServices
from commforge.ui.widgets.common import Card, PageHeader, action_cell, badge_cell, configure_table


def _form_section(title: str) -> tuple[QFrame, QFormLayout]:
    """创建带标题的弹窗配置区。"""
    section = QFrame()
    section.setObjectName("DialogSection")
    layout = QFormLayout(section)
    layout.setContentsMargins(18, 15, 18, 16)
    layout.setHorizontalSpacing(18)
    layout.setVerticalSpacing(10)
    title_label = QLabel(title)
    title_label.setObjectName("ProtocolTitle")
    layout.addRow(title_label)
    return section, layout


class CommunicationDialog(QDialog):
    """只展示当前通信类型所需配置的动态弹窗。"""

    TYPE_INDEX = {
        CommunicationType.TCP_CLIENT: 0,
        CommunicationType.TCP_SERVER: 1,
        CommunicationType.UDP: 2,
        CommunicationType.SERIAL: 3,
    }

    def __init__(self, parent: QWidget | None = None, entity: CommunicationModel | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑通信" if entity else "新增通信")
        self.resize(570, 680)
        self.setMinimumSize(530, 620)
        config = json.loads(entity.config_json or "{}") if entity else {}

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)
        title = QLabel("编辑通信" if entity else "新建通信")
        title.setObjectName("DialogTitle")
        root.addWidget(title)
        subtitle = QLabel("仅显示所选通信协议需要的参数")
        subtitle.setObjectName("Muted")
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(11)

        common, common_form = _form_section("基本信息")
        self.name = QLineEdit(entity.name if entity else "")
        self.name.setPlaceholderText("例如：TCP Client A")
        self.kind = QComboBox()
        self.kind.addItems([item.value for item in CommunicationType])
        if entity:
            self.kind.setCurrentText(entity.communication_type)
        self.enabled = QCheckBox("启用该通信配置")
        self.enabled.setChecked(entity.enabled if entity else True)
        self.auto_start = QCheckBox("软件启动后自动打开")
        self.auto_start.setChecked(entity.auto_start if entity else False)
        common_form.addRow("名称", self.name)
        common_form.addRow("通信类型", self.kind)
        common_form.addRow("", self.enabled)
        common_form.addRow("", self.auto_start)
        content_layout.addWidget(common)

        self.protocol_stack = QStackedWidget()
        self.protocol_stack.addWidget(self._build_tcp_client(config))
        self.protocol_stack.addWidget(self._build_tcp_server(config))
        self.protocol_stack.addWidget(self._build_udp(config))
        self.protocol_stack.addWidget(self._build_serial(config))
        content_layout.addWidget(self.protocol_stack)

        framing, framing_form = _form_section("接收拆包")
        decoder_config = config.get("decoder_config", {})
        self.decoder_type = QComboBox()
        self.decoder_type.addItems([item.value for item in FrameDecoderType])
        self.decoder_type.setCurrentText(str(config.get("decoder_type", "RAW")))
        self.decoder_stack = QStackedWidget()
        raw_hint = QLabel("每次接收到的数据直接作为一帧")
        raw_hint.setObjectName("Muted")
        self.decoder_stack.addWidget(raw_hint)
        self.delimiter = QLineEdit(str(decoder_config.get("delimiter", "0D0A")))
        self.delimiter.setPlaceholderText("例如：0D0A")
        self.decoder_stack.addWidget(self.delimiter)
        self.fixed_length = QSpinBox()
        self.fixed_length.setRange(1, 10_000_000)
        self.fixed_length.setValue(int(decoder_config.get("length", 32)))
        self.decoder_stack.addWidget(self.fixed_length)
        length_page = QWidget()
        length_form = QFormLayout(length_page)
        length_form.setContentsMargins(0, 0, 0, 0)
        self.length_offset = QSpinBox()
        self.length_offset.setRange(0, 65535)
        self.length_offset.setValue(int(decoder_config.get("offset", 0)))
        self.length_size = QSpinBox()
        self.length_size.setRange(1, 4)
        self.length_size.setValue(int(decoder_config.get("length", 1)))
        self.length_endian = QComboBox()
        self.length_endian.addItems(["big", "little"])
        self.length_endian.setCurrentText(str(decoder_config.get("endianness", "big")))
        self.additional_length = QSpinBox()
        self.additional_length.setRange(0, 65535)
        self.additional_length.setValue(int(decoder_config.get("additional_length", 0)))
        length_form.addRow("长度字段偏移", self.length_offset)
        length_form.addRow("字段字节数", self.length_size)
        length_form.addRow("字节序", self.length_endian)
        length_form.addRow("额外长度", self.additional_length)
        self.decoder_stack.addWidget(length_page)
        self.idle_ms = QSpinBox()
        self.idle_ms.setRange(1, 60_000)
        self.idle_ms.setValue(int(decoder_config.get("idle_ms", 50)))
        self.idle_ms.setSuffix(" ms")
        self.decoder_stack.addWidget(self.idle_ms)
        framing_form.addRow("拆包方式", self.decoder_type)
        framing_form.addRow("拆包参数", self.decoder_stack)
        content_layout.addWidget(framing)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.kind.currentTextChanged.connect(self._sync_protocol_page)
        self.decoder_type.currentTextChanged.connect(self._sync_decoder_page)
        self._sync_protocol_page()
        self._sync_decoder_page()

    def _build_tcp_client(self, config: dict[str, object]) -> QWidget:
        section, form = _form_section("TCP Client 参数")
        self.client_host = QLineEdit(str(config.get("host", "127.0.0.1")))
        self.client_port = self._port_spin(int(config.get("port", 9000)))
        self.auto_reconnect = QCheckBox("断线后自动重连")
        self.auto_reconnect.setChecked(bool(config.get("auto_reconnect", True)))
        self.reconnect_interval = QSpinBox()
        self.reconnect_interval.setRange(100, 300_000)
        self.reconnect_interval.setValue(int(config.get("reconnect_interval", 3000)))
        self.reconnect_interval.setSuffix(" ms")
        self.connection_timeout = QSpinBox()
        self.connection_timeout.setRange(100, 300_000)
        self.connection_timeout.setValue(int(config.get("connection_timeout", 5000)))
        self.connection_timeout.setSuffix(" ms")
        form.addRow("目标地址", self.client_host)
        form.addRow("目标端口", self.client_port)
        form.addRow("", self.auto_reconnect)
        form.addRow("重连间隔", self.reconnect_interval)
        form.addRow("连接超时", self.connection_timeout)
        return section

    def _build_tcp_server(self, config: dict[str, object]) -> QWidget:
        section, form = _form_section("TCP Server 参数")
        self.server_host = QLineEdit(str(config.get("host", "0.0.0.0")))
        self.server_port = self._port_spin(int(config.get("port", 9001)))
        self.max_clients = QSpinBox()
        self.max_clients.setRange(1, 10_000)
        self.max_clients.setValue(int(config.get("max_clients", 32)))
        form.addRow("监听地址", self.server_host)
        form.addRow("监听端口", self.server_port)
        form.addRow("最大客户端数", self.max_clients)
        return section

    def _build_udp(self, config: dict[str, object]) -> QWidget:
        section, form = _form_section("UDP 参数")
        self.udp_local_host = QLineEdit(str(config.get("local_host", "0.0.0.0")))
        self.udp_local_port = self._port_spin(int(config.get("local_port", 9002)))
        self.udp_remote_host = QLineEdit(str(config.get("remote_host", "127.0.0.1")))
        self.udp_remote_port = self._port_spin(int(config.get("remote_port", 9002)))
        form.addRow("本地地址", self.udp_local_host)
        form.addRow("本地端口", self.udp_local_port)
        form.addRow("默认远程地址", self.udp_remote_host)
        form.addRow("默认远程端口", self.udp_remote_port)
        return section

    def _build_serial(self, config: dict[str, object]) -> QWidget:
        section, form = _form_section("Serial 参数")
        port_row = QWidget()
        port_layout = QHBoxLayout(port_row)
        port_layout.setContentsMargins(0, 0, 0, 0)
        port_layout.setSpacing(7)
        self.serial_port = QComboBox()
        self.serial_port.setEditable(True)
        refresh_button = QPushButton("刷新")
        refresh_button.setObjectName("TableAction")
        refresh_button.clicked.connect(lambda: self._refresh_serial_ports())
        port_layout.addWidget(self.serial_port, 1)
        port_layout.addWidget(refresh_button)
        self.baud = QComboBox()
        self.baud.setEditable(True)
        self.baud.addItems(["9600", "19200", "38400", "57600", "115200", "460800"])
        self.baud.setCurrentText(str(config.get("baud_rate", 115200)))
        self.data_bits = QComboBox()
        self.data_bits.addItems(["5", "6", "7", "8"])
        self.data_bits.setCurrentText(str(config.get("data_bits", 8)))
        self.stop_bits = QComboBox()
        self.stop_bits.addItems(["1", "1.5", "2"])
        self.stop_bits.setCurrentText(str(config.get("stop_bits", "1")))
        self.parity = QComboBox()
        self.parity.addItems(["NONE", "EVEN", "ODD", "MARK", "SPACE"])
        self.parity.setCurrentText(str(config.get("parity", "NONE")))
        self.flow_control = QComboBox()
        self.flow_control.addItems(["NONE", "HARDWARE", "SOFTWARE"])
        self.flow_control.setCurrentText(str(config.get("flow_control", "NONE")))
        self._refresh_serial_ports(str(config.get("port_name", "COM3")))
        form.addRow("串口号", port_row)
        form.addRow("波特率", self.baud)
        form.addRow("数据位", self.data_bits)
        form.addRow("停止位", self.stop_bits)
        form.addRow("校验位", self.parity)
        form.addRow("流控", self.flow_control)
        return section

    @staticmethod
    def _port_spin(value: int) -> QSpinBox:
        widget = QSpinBox()
        widget.setRange(1, 65535)
        widget.setValue(value)
        return widget

    def _refresh_serial_ports(self, selected: str | None = None) -> None:
        """刷新系统串口列表并保留当前选择。"""
        current = selected or self.serial_port.currentText() or "COM3"
        names = [info.portName() for info in QSerialPortInfo.availablePorts()]
        if current and current not in names:
            names.append(current)
        self.serial_port.clear()
        self.serial_port.addItems(names)
        self.serial_port.setCurrentText(current)

    def _sync_protocol_page(self) -> None:
        self.protocol_stack.setCurrentIndex(
            self.TYPE_INDEX[CommunicationType(self.kind.currentText())]
        )
        # QStackedWidget 默认按最高页面留白，按当前协议收紧高度。
        self.protocol_stack.setFixedHeight(self.protocol_stack.currentWidget().sizeHint().height())

    def _sync_decoder_page(self) -> None:
        decoder = FrameDecoderType(self.decoder_type.currentText())
        self.decoder_stack.setCurrentIndex({
            FrameDecoderType.RAW: 0, FrameDecoderType.DELIMITER: 1,
            FrameDecoderType.FIXED_LENGTH: 2, FrameDecoderType.LENGTH_FIELD: 3,
            FrameDecoderType.IDLE_TIMEOUT: 4,
        }[decoder])
        self.decoder_stack.setFixedHeight(self.decoder_stack.currentWidget().sizeHint().height())

    def _validate(self) -> None:
        """阻止空名称、地址和串口进入数据库。"""
        if not self.name.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入通信名称")
            return
        kind = CommunicationType(self.kind.currentText())
        if kind == CommunicationType.TCP_CLIENT and not self.client_host.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入目标地址")
            return
        if kind == CommunicationType.SERIAL and not self.serial_port.currentText().strip():
            QMessageBox.warning(self, "输入错误", "请选择串口号")
            return
        self.accept()

    def values(self) -> dict[str, object]:
        """只序列化当前协议的有效参数。"""
        kind = CommunicationType(self.kind.currentText())
        if kind == CommunicationType.TCP_CLIENT:
            config: dict[str, object] = {
                "host": self.client_host.text().strip(), "port": self.client_port.value(),
                "auto_reconnect": self.auto_reconnect.isChecked(),
                "reconnect_interval": self.reconnect_interval.value(),
                "connection_timeout": self.connection_timeout.value(),
            }
        elif kind == CommunicationType.TCP_SERVER:
            config = {"host": self.server_host.text().strip(), "port": self.server_port.value(),
                      "max_clients": self.max_clients.value()}
        elif kind == CommunicationType.UDP:
            config = {"local_host": self.udp_local_host.text().strip(),
                      "local_port": self.udp_local_port.value(),
                      "remote_host": self.udp_remote_host.text().strip(),
                      "remote_port": self.udp_remote_port.value()}
        else:
            config = {"port_name": self.serial_port.currentText().strip(),
                      "baud_rate": int(self.baud.currentText()),
                      "data_bits": int(self.data_bits.currentText()),
                      "stop_bits": self.stop_bits.currentText(),
                      "parity": self.parity.currentText(),
                      "flow_control": self.flow_control.currentText()}
        decoder = FrameDecoderType(self.decoder_type.currentText())
        decoder_config: dict[str, object] = {}
        if decoder == FrameDecoderType.DELIMITER:
            decoder_config = {"delimiter": self.delimiter.text().strip(), "include_delimiter": True}
        elif decoder == FrameDecoderType.FIXED_LENGTH:
            decoder_config = {"length": self.fixed_length.value()}
        elif decoder == FrameDecoderType.LENGTH_FIELD:
            decoder_config = {"offset": self.length_offset.value(), "length": self.length_size.value(),
                              "endianness": self.length_endian.currentText(),
                              "additional_length": self.additional_length.value()}
        elif decoder == FrameDecoderType.IDLE_TIMEOUT:
            decoder_config = {"idle_ms": self.idle_ms.value()}
        config["decoder_type"] = decoder.value
        config["decoder_config"] = decoder_config
        return {"name": self.name.text().strip(), "communication_type": kind.value,
                "enabled": self.enabled.isChecked(), "auto_start": self.auto_start.isChecked(),
                "config_json": json.dumps(config, ensure_ascii=False)}


class CommunicationsPage(QWidget):
    def __init__(self, services: ApplicationServices) -> None:
        super().__init__()
        self.services = services
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(14)
        header = PageHeader("通信管理", "创建并管理 TCP、UDP 与串口通信实例")
        header.add_action("＋ 新增通信", self.add_item, True)
        header.add_action("编辑", self.edit_item)
        header.add_action("复制", self.copy_item)
        header.add_action("删除", self.delete_item)
        layout.addWidget(header)
        card = Card()
        card.layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        configure_table(self.table, ["名称", "类型", "地址", "状态", "自动启动", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 96)
        self.table.setColumnWidth(4, 88)
        self.table.setColumnWidth(5, 176)
        self.table.setMinimumHeight(520)
        self.table.doubleClicked.connect(self.edit_item)
        card.layout.addWidget(self.table)
        layout.addWidget(card, 1)
        services.manager.status_changed.connect(lambda *_: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        """刷新列表，并使用状态标签和行内操作呈现每个通信。"""
        items = self.services.communications.list_all()
        self.table.setRowCount(0)
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            config = json.loads(item.config_json or "{}")
            channel = self.services.manager.get(item.id)
            status = channel.status if channel else CommunicationStatus.STOPPED
            values = [item.name, {"TCP_CLIENT": "TCP Client", "TCP_SERVER": "TCP Server",
                                  "UDP": "UDP", "SERIAL": "Serial"}.get(
                                      item.communication_type, item.communication_type),
                      self._address(item.communication_type, config)]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, item.id)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, cell)
            status_text, tone = {
                CommunicationStatus.OPEN: ("已打开", "success"),
                CommunicationStatus.CONNECTING: ("连接中", "warning"),
                CommunicationStatus.ERROR: ("异常", "danger"),
                CommunicationStatus.STOPPED: ("未启动", "neutral"),
            }[status]
            self.table.setCellWidget(row, 3, badge_cell(status_text, tone))
            self.table.setCellWidget(row, 4, badge_cell(
                "是" if item.auto_start else "否", "info" if item.auto_start else "neutral"
            ))
            self.table.setCellWidget(row, 5, self._action_cell(row, status == CommunicationStatus.OPEN))
        if items:
            self.table.selectRow(0)

    def _action_cell(self, row: int, is_open: bool) -> QWidget:
        toggle = QPushButton("停止" if is_open else "启动")
        toggle.clicked.connect(lambda: self._run_for_row(row, self.toggle_selected))
        edit = QPushButton("编辑")
        edit.clicked.connect(lambda: self._run_for_row(row, self.edit_item))
        return action_cell(toggle, edit)

    def _run_for_row(self, row: int, callback: object) -> None:
        """先选中操作所在行，再调用页面操作。"""
        self.table.selectRow(row)
        callback()

    def selected_id(self) -> int | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def add_item(self) -> None:
        dialog = CommunicationDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        entity = self.services.communications.add(CommunicationModel(**dialog.values()))
        self.services.manager.create_channel(
            entity.id, entity.name, entity.communication_type, json.loads(entity.config_json)
        )
        self.refresh()

    def edit_item(self) -> None:
        entity_id = self.selected_id()
        entity = self.services.communications.get(entity_id) if entity_id else None
        if not entity:
            return
        dialog = CommunicationDialog(self, entity)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.services.manager.close(entity.id)
            updated = self.services.communications.update(entity.id, **dialog.values())
            self.services.manager.create_channel(updated.id, updated.name, updated.communication_type,
                                                 json.loads(updated.config_json))
            self.refresh()

    def copy_item(self) -> None:
        entity_id = self.selected_id()
        entity = self.services.communications.get(entity_id) if entity_id else None
        if not entity:
            return
        copy = self.services.communications.add(CommunicationModel(
            name=f"{entity.name} 副本", communication_type=entity.communication_type,
            enabled=entity.enabled, auto_start=False, config_json=entity.config_json,
        ))
        self.services.manager.create_channel(copy.id, copy.name, copy.communication_type,
                                             json.loads(copy.config_json))
        self.refresh()

    def delete_item(self) -> None:
        entity_id = self.selected_id()
        if not entity_id:
            return
        if QMessageBox.question(self, "删除通信", "确定删除选中的通信配置吗？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.services.manager.close(entity_id)
            self.services.communications.delete(entity_id)
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "无法删除", str(exc))

    def toggle_selected(self) -> None:
        entity_id = self.selected_id()
        if not entity_id:
            return
        channel = self.services.manager.get(entity_id)
        try:
            if channel and channel.is_open():
                self.services.manager.close(entity_id)
            else:
                self.services.manager.open(entity_id)
        except Exception as exc:
            QMessageBox.warning(self, "通信错误", str(exc))

    @staticmethod
    def _address(kind: str, config: dict[str, object]) -> str:
        if kind == "UDP":
            return f"{config.get('local_host')}:{config.get('local_port')}"
        if kind == "SERIAL":
            return f"{config.get('port_name')} · {config.get('baud_rate')}"
        return f"{config.get('host')}:{config.get('port')}"
