from commforge.communication.frame_decoder import FrameDecoder
from commforge.core.enums import CodecType, FrameDecoderType, MatchType
from commforge.receive.rules import ReceiveFieldSpec, ReceiveRule


def test_hex_pattern_match() -> None:
    rule = ReceiveRule("请求", MatchType.HEX_PATTERN, "AA 55 ?? 03")
    assert rule.matches(bytes.fromhex("AA550103"))
    assert rule.matches(bytes.fromhex("AA55FF03"))
    assert not rule.matches(bytes.fromhex("AA55FF04"))


def test_receive_rule_parse() -> None:
    rule = ReceiveRule(
        "解析请求", MatchType.HEX_PATTERN, "AA 55 ?? ?? ?? ??",
        [
            ReceiveFieldSpec("address", 2, 1, CodecType.UINT8),
            ReceiveFieldSpec("command", 3, 1, CodecType.UINT8),
            ReceiveFieldSpec("length", 4, 2, CodecType.UINT16_BE),
        ],
    )
    context = rule.parse(bytes.fromhex("AA5505030002"), communication_id=1)
    assert context.parsed_fields == {"address": 5, "command": 3, "length": 2}


def test_delimiter_decoder_handles_sticky_packets() -> None:
    decoder = FrameDecoder(FrameDecoderType.DELIMITER, {"delimiter": "0D0A"})
    assert decoder.feed(b"ABC\r") == []
    assert decoder.feed(b"\nDEF\r\n") == [b"ABC\r\n", b"DEF\r\n"]


def test_fixed_length_decoder_handles_partial_packets() -> None:
    decoder = FrameDecoder(FrameDecoderType.FIXED_LENGTH, {"length": 3})
    assert decoder.feed(b"12") == []
    assert decoder.feed(b"34567") == [b"123", b"456"]
    assert decoder.flush() == [b"7"]


def test_length_field_decoder_handles_partial_and_sticky_packets() -> None:
    # 帧格式：AA + payload_length + payload，additional_length 包含两字节头。
    decoder = FrameDecoder(
        FrameDecoderType.LENGTH_FIELD,
        {"offset": 1, "length": 1, "endianness": "big", "additional_length": 2},
    )
    first = bytes.fromhex("AA03010203")
    second = bytes.fromhex("AA020405")
    assert decoder.feed(first[:3]) == []
    assert decoder.feed(first[3:] + second) == [first, second]


def test_idle_timeout_decoder_buffers_until_flush() -> None:
    decoder = FrameDecoder(FrameDecoderType.IDLE_TIMEOUT, {"idle_ms": 50})
    assert decoder.feed(b"ABC") == []
    assert decoder.feed(b"DEF") == []
    assert decoder.flush() == [b"ABCDEF"]
