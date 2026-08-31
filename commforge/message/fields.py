"""字段生成器及注册表。"""

import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

from commforge.core.context import RuntimeContext
from commforge.core.enums import BoundaryPolicy, ChangeMode, FieldType
from commforge.core.exceptions import ValidationError

if TYPE_CHECKING:
    from commforge.message.builder import BuildContext, MessageFieldSpec


class FieldGenerator(ABC):
    @abstractmethod
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        """生成字段逻辑值；二进制编码由 CodecRegistry 负责。"""


class FixedGenerator(FieldGenerator):
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        return field.config.get("value", "")


class TimeGenerator(FieldGenerator):
    FORMAT_MAP = {
        "yyyyMMddHHmmss": "%Y%m%d%H%M%S",
        "yyyyMMddHHmmssSSS": "%Y%m%d%H%M%S%f",
        "yyyy-MM-dd HH:mm:ss": "%Y-%m-%d %H:%M:%S",
        "yyyyMMddHHmm": "%Y%m%d%H%M",
        "HHmmss": "%H%M%S",
        "HH:mm:ss": "%H:%M:%S",
        "yyyy-MM-dd": "%Y-%m-%d",
    }

    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        config = field.config
        now = context.now + timedelta(**{config.get("offset_unit", "seconds"): config.get("offset", 0)})
        fmt = config.get("format", "yyyyMMddHHmmss")
        if fmt == "Unix秒时间戳":
            return int(now.timestamp())
        if fmt == "Unix毫秒时间戳":
            return int(now.timestamp() * 1000)
        python_format = self.FORMAT_MAP.get(fmt, fmt)
        result = now.strftime(python_format)
        return result[:-3] if fmt == "yyyyMMddHHmmssSSS" else result


class ChangeGenerator(FieldGenerator):
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        cfg = field.config
        initial = float(cfg.get("initial", 0))
        current = float(context.runtime.get(context.task_id, field.id, initial))
        minimum = float(cfg.get("min", 0))
        maximum = float(cfg.get("max", 100))
        mode = ChangeMode(cfg.get("mode", ChangeMode.RANDOM_WALK))
        step_min = float(cfg.get("step_min", -1))
        step_max = float(cfg.get("step_max", 1))
        direction_key = f"{field.id}:direction"
        direction = int(context.runtime.get(context.task_id, direction_key, 1))

        if mode == ChangeMode.RANDOM_WALK:
            next_value = current + random.uniform(step_min, step_max)
        elif mode in (ChangeMode.INCREMENT, ChangeMode.LOOP):
            next_value = current + abs(step_max)
        elif mode == ChangeMode.DECREMENT:
            next_value = current - abs(step_max)
        else:
            next_value = current + direction * abs(step_max)

        policy = BoundaryPolicy(cfg.get("boundary", BoundaryPolicy.BOUNCE))
        if next_value > maximum or next_value < minimum:
            if mode == ChangeMode.LOOP or policy == BoundaryPolicy.WRAP:
                next_value = minimum if next_value > maximum else maximum
            elif policy == BoundaryPolicy.BOUNCE or mode == ChangeMode.BOUNCE:
                direction *= -1
                context.runtime.set(context.task_id, direction_key, direction)
                next_value = max(minimum, min(maximum, current + direction * abs(step_max)))
            else:
                next_value = max(minimum, min(maximum, next_value))

        precision = int(cfg.get("precision", 0))
        next_value = round(next_value, precision)
        context.runtime.set(context.task_id, field.id, next_value)
        scale = float(cfg.get("scale", 1))
        scaled = next_value * scale
        if cfg.get("text_decimal", False):
            return f"{next_value:.{precision}f}"
        return int(round(scaled)) if float(scaled).is_integer() else scaled


class RandomGenerator(FieldGenerator):
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        cfg = field.config
        minimum, maximum = float(cfg.get("min", 0)), float(cfg.get("max", 100))
        precision = int(cfg.get("precision", 0))
        value = random.uniform(minimum, maximum)
        value = round(value, precision)
        scaled = value * float(cfg.get("scale", 1))
        return int(round(scaled)) if precision == 0 else scaled


class SequenceGenerator(FieldGenerator):
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        cfg = field.config
        initial = int(cfg.get("initial", 0))
        current = int(context.runtime.get(context.task_id, field.id, initial))
        step = int(cfg.get("step", 1))
        minimum, maximum = int(cfg.get("min", 0)), int(cfg.get("max", 255))
        next_value = current + step
        if next_value > maximum:
            next_value = minimum if cfg.get("boundary", "WRAP") == "WRAP" else maximum
        elif next_value < minimum:
            next_value = maximum if cfg.get("boundary", "WRAP") == "WRAP" else minimum
        context.runtime.set(context.task_id, field.id, next_value)
        return current


class ReceivedValueGenerator(FieldGenerator):
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        cfg = field.config
        key = cfg.get("source", "")
        if context.receive and key in context.receive.parsed_fields:
            return context.receive.parsed_fields[key] * float(cfg.get("scale", 1))
        if cfg.get("missing", "DEFAULT") == "ERROR":
            raise ValidationError(f"接收字段 {key!r} 不存在")
        return cfg.get("default", 0)


class ReceivedBytesGenerator(FieldGenerator):
    def generate(self, field: "MessageFieldSpec", context: "BuildContext") -> Any:
        if not context.receive:
            return b""
        start = int(field.config.get("start", 0))
        length = int(field.config.get("length", 1))
        return context.receive.raw_data[start : start + length]


class FieldGeneratorRegistry:
    _generators: dict[FieldType, FieldGenerator] = {}

    @classmethod
    def register(cls, field_type: FieldType, generator: FieldGenerator) -> None:
        cls._generators[field_type] = generator

    @classmethod
    def get(cls, field_type: FieldType | str) -> FieldGenerator:
        try:
            return cls._generators[FieldType(field_type)]
        except KeyError as exc:
            raise ValidationError(f"未注册字段生成器：{field_type}") from exc


for _field_type, _generator in {
    FieldType.FIXED: FixedGenerator(),
    FieldType.TIME: TimeGenerator(),
    FieldType.CHANGE: ChangeGenerator(),
    FieldType.RANDOM: RandomGenerator(),
    FieldType.SEQUENCE: SequenceGenerator(),
    FieldType.RECEIVED_VALUE: ReceivedValueGenerator(),
    FieldType.RECEIVED_BYTES: ReceivedBytesGenerator(),
}.items():
    FieldGeneratorRegistry.register(_field_type, _generator)
