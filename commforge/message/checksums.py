"""校验算法注册表。"""

import binascii
from collections.abc import Callable

from commforge.core.enums import ChecksumType
from commforge.core.exceptions import ValidationError

ChecksumAlgorithm = Callable[[bytes], int]


def xor_checksum(data: bytes) -> int:
    value = 0
    for item in data:
        value ^= item
    return value


def crc16_modbus(data: bytes) -> int:
    """计算标准 Modbus CRC16，多项式 0xA001。"""
    crc = 0xFFFF
    for item in data:
        crc ^= item
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for item in data:
        crc ^= item << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


class ChecksumRegistry:
    _algorithms: dict[ChecksumType, ChecksumAlgorithm] = {
        ChecksumType.XOR: xor_checksum,
        ChecksumType.SUM8: lambda data: sum(data) & 0xFF,
        ChecksumType.SUM16: lambda data: sum(data) & 0xFFFF,
        ChecksumType.CRC16_MODBUS: crc16_modbus,
        ChecksumType.CRC16_CCITT: crc16_ccitt,
        ChecksumType.CRC32: lambda data: binascii.crc32(data) & 0xFFFFFFFF,
    }

    @classmethod
    def register(cls, checksum_type: ChecksumType, algorithm: ChecksumAlgorithm) -> None:
        cls._algorithms[checksum_type] = algorithm

    @classmethod
    def calculate(cls, checksum_type: ChecksumType | str, data: bytes) -> int:
        try:
            return cls._algorithms[ChecksumType(checksum_type)](data)
        except KeyError as exc:
            raise ValidationError(f"未注册校验算法：{checksum_type}") from exc
