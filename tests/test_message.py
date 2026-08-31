from datetime import datetime

from commforge.core.context import RuntimeContext
from commforge.core.enums import CodecType, FieldType
from commforge.message.builder import BuildContext, MessageBuilder, MessageFieldSpec
from commforge.message.checksums import ChecksumRegistry


def test_checksum_algorithms() -> None:
    data = b"123456789"
    assert ChecksumRegistry.calculate("XOR", b"\x01\x02\x03") == 0
    assert ChecksumRegistry.calculate("SUM8", b"\xff\x02") == 1
    assert ChecksumRegistry.calculate("CRC16_MODBUS", data) == 0x4B37
    assert ChecksumRegistry.calculate("CRC16_CCITT", data) == 0x29B1


def test_fixed_time_and_message_builder() -> None:
    fields = [
        MessageFieldSpec("head", "帧头", FieldType.FIXED, CodecType.HEX_BYTES, {"value": "AA55"}),
        MessageFieldSpec("time", "时间", FieldType.TIME, CodecType.ASCII, {"format": "yyyyMMddHHmmss"}),
    ]
    result = MessageBuilder().build(
        fields,
        BuildContext(now=datetime(2026, 8, 29, 14, 38, 25)),
    )
    assert result.data == b"\xaa\x5520260829143825"


def test_length_and_checksum_two_pass() -> None:
    fields = [
        MessageFieldSpec(1, "数据", FieldType.FIXED, CodecType.HEX_BYTES, {"value": "010203"}),
        MessageFieldSpec(2, "长度", FieldType.LENGTH, CodecType.UINT8, {"start": 0, "end": 0}),
        MessageFieldSpec(3, "校验", FieldType.CHECKSUM, CodecType.UINT8, {"algorithm": "SUM8", "start": 0, "end": 1}),
    ]
    result = MessageBuilder().build(fields)
    assert result.data == b"\x01\x02\x03\x03\x09"


def test_change_range_and_task_isolation() -> None:
    runtime = RuntimeContext()
    field = MessageFieldSpec(
        7, "变化值", FieldType.CHANGE, CodecType.INT16_BE,
        {"initial": 25, "mode": "RANDOM_WALK", "step_min": -3, "step_max": 3,
         "min": -40, "max": 60, "scale": 10, "precision": 1, "boundary": "BOUNCE"},
    )
    builder = MessageBuilder()
    for _ in range(200):
        builder.build([field], BuildContext(task_id="tcp", runtime=runtime))
        assert -40 <= runtime.get("tcp", 7) <= 60
    assert runtime.get("udp", 7) is None


def test_sequence_wrap() -> None:
    runtime = RuntimeContext()
    field = MessageFieldSpec(
        1, "序号", FieldType.SEQUENCE, CodecType.UINT8,
        {"initial": 254, "step": 1, "min": 0, "max": 255, "boundary": "WRAP"},
    )
    builder = MessageBuilder()
    values = [
        builder.build([field], BuildContext(task_id="task", runtime=runtime)).data[0]
        for _ in range(3)
    ]
    assert values == [254, 255, 0]
