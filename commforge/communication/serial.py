"""串口通道。"""

from typing import Any

from PySide6.QtCore import QIODevice
from PySide6.QtSerialPort import QSerialPort

from commforge.communication.base import CommunicationChannel
from commforge.core.enums import CommunicationStatus
from commforge.core.exceptions import CommunicationError


class SerialChannel(CommunicationChannel):
    def __init__(self, communication_id: int | None, name: str, config: dict[str, Any]) -> None:
        super().__init__(communication_id, name, config)
        self.port = QSerialPort(self)
        self.port.readyRead.connect(lambda: self._on_data(bytes(self.port.readAll())))
        self.port.errorOccurred.connect(self._serial_error)

    def open(self) -> None:
        self.port.setPortName(str(self.config.get("port_name", "COM1")))
        self.port.setBaudRate(int(self.config.get("baud_rate", 115200)))
        data_bits = {
            5: QSerialPort.DataBits.Data5, 6: QSerialPort.DataBits.Data6,
            7: QSerialPort.DataBits.Data7, 8: QSerialPort.DataBits.Data8,
        }
        stop_bits = {
            "1": QSerialPort.StopBits.OneStop,
            "1.5": QSerialPort.StopBits.OneAndHalfStop,
            "2": QSerialPort.StopBits.TwoStop,
        }
        parity = {
            "NONE": QSerialPort.Parity.NoParity, "EVEN": QSerialPort.Parity.EvenParity,
            "ODD": QSerialPort.Parity.OddParity, "MARK": QSerialPort.Parity.MarkParity,
            "SPACE": QSerialPort.Parity.SpaceParity,
        }
        flow = {
            "NONE": QSerialPort.FlowControl.NoFlowControl,
            "HARDWARE": QSerialPort.FlowControl.HardwareControl,
            "SOFTWARE": QSerialPort.FlowControl.SoftwareControl,
        }
        self.port.setDataBits(data_bits.get(int(self.config.get("data_bits", 8)), QSerialPort.DataBits.Data8))
        self.port.setStopBits(stop_bits.get(str(self.config.get("stop_bits", "1")), QSerialPort.StopBits.OneStop))
        self.port.setParity(parity.get(str(self.config.get("parity", "NONE")), QSerialPort.Parity.NoParity))
        self.port.setFlowControl(flow.get(str(self.config.get("flow_control", "NONE")), QSerialPort.FlowControl.NoFlowControl))
        ok = self.port.open(QIODevice.OpenModeFlag.ReadWrite)
        self._set_status(CommunicationStatus.OPEN if ok else CommunicationStatus.ERROR)
        if not ok:
            self.error_occurred.emit(self.port.errorString())

    def close(self) -> None:
        self.port.close()
        self._set_status(CommunicationStatus.STOPPED)

    def _write(self, data: bytes, **target: Any) -> None:
        if not self.port.isOpen():
            raise CommunicationError("串口尚未打开")
        self.port.write(data)
        self._log_tx(data)

    def _serial_error(self, error: QSerialPort.SerialPortError) -> None:
        if error not in (
            QSerialPort.SerialPortError.NoError,
            QSerialPort.SerialPortError.NotOpenError,
        ):
            self._on_error(self.port.errorString())
