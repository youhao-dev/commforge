import math

import pytest

from commforge.core.enums import CodecType
from commforge.core.exceptions import ValidationError
from commforge.message.codecs import CodecRegistry, normalize_hex


def test_ascii_and_utf8_codecs() -> None:
    assert CodecRegistry.encode(CodecType.ASCII, "ABC") == b"ABC"
    assert CodecRegistry.encode(CodecType.UTF8, "通信") == "通信".encode()


def test_hex_normalization_and_validation() -> None:
    assert normalize_hex("aa 55\n01") == "AA5501"
    assert CodecRegistry.encode(CodecType.HEX_BYTES, "AA55") == b"\xaa\x55"
    with pytest.raises(ValidationError):
        CodecRegistry.encode(CodecType.HEX_BYTES, "AAG5")


@pytest.mark.parametrize(
    ("codec", "value", "expected"),
    [
        (CodecType.UINT8, 255, b"\xff"),
        (CodecType.INT8, -1, b"\xff"),
        (CodecType.UINT16_BE, 0x1234, b"\x12\x34"),
        (CodecType.UINT16_LE, 0x1234, b"\x34\x12"),
        (CodecType.INT16_BE, -2, b"\xff\xfe"),
        (CodecType.UINT32_LE, 0x12345678, b"\x78\x56\x34\x12"),
    ],
)
def test_integer_codecs(codec: CodecType, value: int, expected: bytes) -> None:
    encoded = CodecRegistry.encode(codec, value)
    assert encoded == expected
    assert CodecRegistry.decode(codec, encoded) == value


@pytest.mark.parametrize(
    "codec", [CodecType.FLOAT32_BE, CodecType.FLOAT32_LE, CodecType.FLOAT64_BE, CodecType.FLOAT64_LE]
)
def test_float_codecs(codec: CodecType) -> None:
    encoded = CodecRegistry.encode(codec, 12.5)
    assert math.isclose(CodecRegistry.decode(codec, encoded), 12.5, rel_tol=1e-6)
