"""SQLAlchemy 数据模型，仅保存静态配置。"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class CommunicationModel(TimestampMixin, Base):
    __tablename__ = "communications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    communication_type: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_start: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}")


class MessageRuleModel(TimestampMixin, Base):
    __tablename__ = "message_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    fields: Mapped[list["MessageFieldModel"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan", order_by="MessageFieldModel.sort_no"
    )


class MessageFieldModel(TimestampMixin, Base):
    __tablename__ = "message_rule_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("message_rules.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    field_type: Mapped[str] = mapped_column(String(32))
    codec_type: Mapped[str] = mapped_column(String(32))
    sort_no: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    rule: Mapped[MessageRuleModel] = relationship(back_populates="fields")


class ReceiveRuleModel(TimestampMixin, Base):
    __tablename__ = "receive_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    match_type: Mapped[str] = mapped_column(String(32))
    pattern: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    fields: Mapped[list["ReceiveFieldModel"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class ReceiveFieldModel(TimestampMixin, Base):
    __tablename__ = "receive_rule_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("receive_rules.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    offset: Mapped[int] = mapped_column(Integer, default=0)
    length: Mapped[int] = mapped_column(Integer, default=1)
    codec_type: Mapped[str] = mapped_column(String(32))
    expected_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    rule: Mapped[ReceiveRuleModel] = relationship(back_populates="fields")


class AutomationTaskModel(TimestampMixin, Base):
    __tablename__ = "automation_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(32))
    communication_id: Mapped[int | None] = mapped_column(
        ForeignKey("communications.id", ondelete="RESTRICT"), nullable=True
    )
    receive_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("receive_rules.id", ondelete="RESTRICT"), nullable=True
    )
    message_rule_id: Mapped[int] = mapped_column(
        ForeignKey("message_rules.id", ondelete="RESTRICT")
    )
    target_type: Mapped[str] = mapped_column(String(40), default="COMMUNICATION")
    target_communication_id: Mapped[int | None] = mapped_column(
        ForeignKey("communications.id", ondelete="RESTRICT"), nullable=True
    )
    config_json: Mapped[str] = mapped_column(Text, default="{}")
