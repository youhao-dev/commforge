"""面向字节流的可配置拆包器。"""

from dataclasses import dataclass, field

from commforge.core.enums import FrameDecoderType
from commforge.core.exceptions import ValidationError


@dataclass
class FrameDecoder:
    decoder_type: FrameDecoderType = FrameDecoderType.RAW
    config: dict[str, object] = field(default_factory=dict)
    _buffer: bytearray = field(default_factory=bytearray, init=False)

    def feed(self, data: bytes) -> list[bytes]:
        """追加数据并尽可能拆出全部完整帧。"""
        if not data:
            return []
        mode = FrameDecoderType(self.decoder_type)
        if mode == FrameDecoderType.RAW:
            return [bytes(data)]
        self._buffer.extend(data)
        if mode == FrameDecoderType.DELIMITER:
            return self._delimiter_frames()
        if mode == FrameDecoderType.FIXED_LENGTH:
            return self._fixed_frames()
        if mode == FrameDecoderType.LENGTH_FIELD:
            return self._length_frames()
        return []  # IDLE_TIMEOUT 由通信通道的定时器调用 flush。

    def flush(self) -> list[bytes]:
        if not self._buffer:
            return []
        frame = bytes(self._buffer)
        self._buffer.clear()
        return [frame]

    def _delimiter_frames(self) -> list[bytes]:
        delimiter = self.config.get("delimiter", b"\r\n")
        if isinstance(delimiter, str):
            delimiter = bytes.fromhex(delimiter.replace(" ", ""))
        if not delimiter:
            raise ValidationError("结束符不能为空")
        frames: list[bytes] = []
        while True:
            index = self._buffer.find(delimiter)
            if index < 0:
                break
            end = index + len(delimiter)
            include = bool(self.config.get("include_delimiter", True))
            frames.append(bytes(self._buffer[:end] if include else self._buffer[:index]))
            del self._buffer[:end]
        return frames

    def _fixed_frames(self) -> list[bytes]:
        length = int(self.config.get("length", 1))
        if length <= 0:
            raise ValidationError("固定帧长度必须大于 0")
        frames: list[bytes] = []
        while len(self._buffer) >= length:
            frames.append(bytes(self._buffer[:length]))
            del self._buffer[:length]
        return frames

    def _length_frames(self) -> list[bytes]:
        offset = int(self.config.get("offset", 0))
        size = int(self.config.get("length", 1))
        additional = int(self.config.get("additional_length", offset + size))
        byteorder = str(self.config.get("endianness", "big"))
        frames: list[bytes] = []
        header_size = offset + size
        while len(self._buffer) >= header_size:
            payload_size = int.from_bytes(self._buffer[offset:header_size], byteorder)
            frame_size = payload_size + additional
            if frame_size <= 0:
                raise ValidationError("长度字段计算出的帧长不合法")
            if len(self._buffer) < frame_size:
                break
            frames.append(bytes(self._buffer[:frame_size]))
            del self._buffer[:frame_size]
        return frames
