"""独立于自动化任务的接收规则。"""

import re
from dataclasses import dataclass, field
from typing import Any

from commforge.core.context import ReceiveContext
from commforge.core.enums import CodecType, MatchType
from commforge.core.exceptions import ValidationError
from commforge.message.codecs import CodecRegistry, normalize_hex


@dataclass(slots=True)
class ReceiveFieldSpec:
    name: str
    offset: int
    length: int
    codec: CodecType
    expected_value: Any | None = None
    required: bool = True


@dataclass(slots=True)
class ReceiveRule:
    name: str
    match_type: MatchType
    pattern: str
    fields: list[ReceiveFieldSpec] = field(default_factory=list)

    def matches(self, data: bytes) -> bool:
        """按配置执行文本或 HEX 匹配。"""
        mode = MatchType(self.match_type)
        if mode in (MatchType.HEX_EXACT, MatchType.HEX_PATTERN):
            if mode == MatchType.HEX_EXACT:
                return data == bytes.fromhex(normalize_hex(self.pattern))
            tokens = self.pattern.upper().split()
            if len(tokens) == 1:
                compact = self.pattern.replace(" ", "")
                tokens = [compact[i : i + 2] for i in range(0, len(compact), 2)]
            if len(tokens) != len(data):
                return False
            return all(token == "??" or int(token, 16) == value for token, value in zip(tokens, data))

        text = data.decode("utf-8", errors="replace")
        if mode == MatchType.EXACT:
            return text == self.pattern
        if mode == MatchType.CONTAINS:
            return self.pattern in text
        if mode == MatchType.STARTS_WITH:
            return text.startswith(self.pattern)
        if mode == MatchType.ENDS_WITH:
            return text.endswith(self.pattern)
        return re.search(self.pattern, text) is not None

    def parse(self, data: bytes, **metadata: Any) -> ReceiveContext:
        """解析命名字段并验证长度和期望值。"""
        parsed: dict[str, Any] = {}
        for spec in self.fields:
            segment = data[spec.offset : spec.offset + spec.length]
            if len(segment) < spec.length:
                if spec.required:
                    raise ValidationError(f"接收字段 {spec.name} 数据不足")
                continue
            value = CodecRegistry.decode(spec.codec, segment)
            if spec.expected_value is not None and str(value) != str(spec.expected_value):
                raise ValidationError(f"接收字段 {spec.name} 与期望值不一致")
            parsed[spec.name] = value
        return ReceiveContext(raw_data=data, parsed_fields=parsed, **metadata)
