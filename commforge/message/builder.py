"""两遍式报文构建器，处理普通字段、长度和校验之间的依赖。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from commforge.core.context import ReceiveContext, RuntimeContext
from commforge.core.enums import CodecType, FieldType
from commforge.core.exceptions import ValidationError
from commforge.message.checksums import ChecksumRegistry
from commforge.message.codecs import CodecRegistry
from commforge.message.fields import FieldGeneratorRegistry


@dataclass(slots=True)
class MessageFieldSpec:
    id: str | int
    name: str
    field_type: FieldType
    codec: CodecType
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass(slots=True)
class BuildContext:
    task_id: str | int = "preview"
    runtime: RuntimeContext = field(default_factory=RuntimeContext)
    receive: ReceiveContext | None = None
    now: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class BuildResult:
    data: bytes
    field_bytes: list[bytes]

    @property
    def hex_text(self) -> str:
        return self.data.hex(" ").upper()

    @property
    def ascii_text(self) -> str:
        return "".join(chr(item) if 32 <= item < 127 else "." for item in self.data)


class MessageBuilder:
    def build(
        self, fields: list[MessageFieldSpec], context: BuildContext | None = None
    ) -> BuildResult:
        """先生成普通字段，再回填 LENGTH 与 CHECKSUM 字段。"""
        context = context or BuildContext()
        active_fields = [item for item in fields if item.enabled]
        pieces: list[bytes] = []
        deferred: list[int] = []

        for index, field_spec in enumerate(active_fields):
            if field_spec.field_type in (FieldType.LENGTH, FieldType.CHECKSUM):
                pieces.append(b"")
                deferred.append(index)
                continue
            generator = FieldGeneratorRegistry.get(field_spec.field_type)
            value = generator.generate(field_spec, context)
            pieces.append(CodecRegistry.encode(field_spec.codec, value))

        # LENGTH 先回填，校验字段才能覆盖最终长度字节。
        for index in deferred:
            field_spec = active_fields[index]
            if field_spec.field_type != FieldType.LENGTH:
                continue
            start, end = self._range(field_spec, len(pieces))
            total = sum(len(part) for part in pieces[start : end + 1])
            if field_spec.config.get("include_self"):
                placeholder_size = int(field_spec.config.get("self_size", 1))
                total += placeholder_size
            pieces[index] = CodecRegistry.encode(field_spec.codec, total)

        for index in deferred:
            field_spec = active_fields[index]
            if field_spec.field_type != FieldType.CHECKSUM:
                continue
            start, end = self._range(field_spec, len(pieces))
            payload = b"".join(pieces[start : end + 1])
            checksum = ChecksumRegistry.calculate(
                field_spec.config.get("algorithm", "SUM8"), payload
            )
            pieces[index] = CodecRegistry.encode(field_spec.codec, checksum)

        return BuildResult(b"".join(pieces), pieces)

    @staticmethod
    def _range(field_spec: MessageFieldSpec, count: int) -> tuple[int, int]:
        start = int(field_spec.config.get("start", 0))
        end = int(field_spec.config.get("end", count - 1))
        if start < 0 or end >= count or start > end:
            raise ValidationError(f"字段 {field_spec.name} 的计算范围不合法")
        return start, end
