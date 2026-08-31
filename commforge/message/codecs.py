"""输出编码注册表；字段生成与二进制编码完全分离。"""

import re
import struct
from collections.abc import Callable
from typing import Any

from commforge.core.enums import CodecType
from commforge.core.exceptions import ValidationError

Encoder = Callable[[Any], bytes]
Decoder = Callable[[bytes], Any]


def normalize_hex(value: str) -> str:
    """移除 HEX 分隔空白并校验字符及偶数长度。"""
    normalized = re.sub(r"\s+", "", value).upper()
    if not normalized or len(normalized) % 2 or not re.fullmatch(r"[0-9A-F]+", normalized):
        raise ValidationError("HEX 输入必须由偶数个十六进制字符组成")
    return normalized


def _int_encoder(length: int, signed: bool, byteorder: str) -> Encoder:
    def encode(value: Any) -> bytes:
        try:
            return int(value).to_bytes(length, byteorder=byteorder, signed=signed)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError(f"数值 {value!r} 无法编码为 {length * 8} 位整数") from exc

    return encode


def _int_decoder(signed: bool, byteorder: str) -> Decoder:
    return lambda data: int.from_bytes(data, byteorder=byteorder, signed=signed)


class CodecRegistry:
    """集中注册编码器和解码器，新增 Codec 不需要修改字段生成器。"""

    _encoders: dict[CodecType, Encoder] = {}
    _decoders: dict[CodecType, Decoder] = {}

    @classmethod
    def register(cls, codec: CodecType, encoder: Encoder, decoder: Decoder) -> None:
        cls._encoders[codec] = encoder
        cls._decoders[codec] = decoder

    @classmethod
    def encode(cls, codec: CodecType | str, value: Any) -> bytes:
        try:
            return cls._encoders[CodecType(codec)](value)
        except KeyError as exc:
            raise ValidationError(f"未注册输出编码：{codec}") from exc

    @classmethod
    def decode(cls, codec: CodecType | str, data: bytes) -> Any:
        try:
            return cls._decoders[CodecType(codec)](data)
        except KeyError as exc:
            raise ValidationError(f"未注册输入编码：{codec}") from exc


def _register_builtins() -> None:
    CodecRegistry.register(
        CodecType.ASCII,
        lambda value: str(value).encode("ascii"),
        lambda data: data.decode("ascii"),
    )
    CodecRegistry.register(
        CodecType.UTF8,
        lambda value: str(value).encode("utf-8"),
        lambda data: data.decode("utf-8"),
    )
    CodecRegistry.register(
        CodecType.HEX_BYTES,
        lambda value: bytes.fromhex(normalize_hex(str(value))),
        lambda data: data.hex(" ").upper(),
    )
    CodecRegistry.register(
        CodecType.RAW_BYTES,
        lambda value: value if isinstance(value, bytes) else bytes(value),
        lambda data: data,
    )
    integer_specs = {
        CodecType.UINT8: (1, False, "big"),
        CodecType.INT8: (1, True, "big"),
        CodecType.UINT16_BE: (2, False, "big"),
        CodecType.UINT16_LE: (2, False, "little"),
        CodecType.INT16_BE: (2, True, "big"),
        CodecType.INT16_LE: (2, True, "little"),
        CodecType.UINT32_BE: (4, False, "big"),
        CodecType.UINT32_LE: (4, False, "little"),
        CodecType.INT32_BE: (4, True, "big"),
        CodecType.INT32_LE: (4, True, "little"),
    }
    for codec, (length, signed, byteorder) in integer_specs.items():
        CodecRegistry.register(
            codec, _int_encoder(length, signed, byteorder), _int_decoder(signed, byteorder)
        )
    float_specs = {
        CodecType.FLOAT32_BE: ">f",
        CodecType.FLOAT32_LE: "<f",
        CodecType.FLOAT64_BE: ">d",
        CodecType.FLOAT64_LE: "<d",
    }
    for codec, fmt in float_specs.items():
        CodecRegistry.register(
            codec,
            lambda value, fmt=fmt: struct.pack(fmt, float(value)),
            lambda data, fmt=fmt: struct.unpack(fmt, data)[0],
        )


_register_builtins()
