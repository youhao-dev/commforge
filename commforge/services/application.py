"""组合数据库、规则引擎、通信管理器和运行状态。"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from commforge.communication.manager import CommunicationManager
from commforge.core.context import RuntimeContext
from commforge.core.enums import (
    CodecType,
    CommunicationType,
    FieldType,
    TaskTargetType,
    TriggerType,
)
from commforge.database.database import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from commforge.database.models import (
    AutomationTaskModel,
    CommunicationModel,
    MessageFieldModel,
    MessageRuleModel,
    ReceiveRuleModel,
    ReceiveFieldModel,
)
from commforge.message.builder import BuildContext, MessageBuilder, MessageFieldSpec
from commforge.repositories.repositories import (
    AutomationRepository,
    CommunicationRepository,
    MessageRuleRepository,
    ReceiveRuleRepository,
)


@dataclass(slots=True)
class ApplicationServices:
    session_factory: sessionmaker[Session]
    communications: CommunicationRepository
    message_rules: MessageRuleRepository
    receive_rules: ReceiveRuleRepository
    automations: AutomationRepository
    manager: CommunicationManager
    runtime: RuntimeContext
    builder: MessageBuilder

    @classmethod
    def create(cls) -> "ApplicationServices":
        """初始化数据库并组装应用级服务。"""
        engine = create_database_engine()
        initialize_database(engine)
        factory = create_session_factory(engine)
        instance = cls(
            factory,
            CommunicationRepository(factory),
            MessageRuleRepository(factory),
            ReceiveRuleRepository(factory),
            AutomationRepository(factory),
            CommunicationManager(),
            RuntimeContext(),
            MessageBuilder(),
        )
        instance.manager.error_occurred.connect(
            lambda message: logging.getLogger("commforge.communication").error(message)
        )
        instance.seed_examples()
        instance.load_channels()
        return instance

    def seed_examples(self) -> None:
        """为各空配置分类创建少量可删除的通用示例。"""
        with self.session_factory() as session:
            count = session.scalar(select(func.count(CommunicationModel.id))) or 0
            if not count:
                session.add_all([
                    CommunicationModel(
                        name="TCP Client A", communication_type=CommunicationType.TCP_CLIENT,
                        config_json=json.dumps({"host": "127.0.0.1", "port": 9000})
                    ),
                    CommunicationModel(
                        name="TCP Server 01", communication_type=CommunicationType.TCP_SERVER,
                        config_json=json.dumps({"host": "0.0.0.0", "port": 9001})
                    ),
                    CommunicationModel(
                        name="UDP 01", communication_type=CommunicationType.UDP,
                        config_json=json.dumps({
                            "local_host": "0.0.0.0", "local_port": 9002,
                            "remote_host": "127.0.0.1", "remote_port": 9002
                        })
                    ),
                    CommunicationModel(
                        name="Serial COM3", communication_type=CommunicationType.SERIAL,
                        config_json=json.dumps({"port_name": "COM3", "baud_rate": 115200})
                    ),
                ])
                session.flush()

            rule = session.scalar(select(MessageRuleModel).limit(1))
            if not rule:
                rule = MessageRuleModel(name="Random Sensor Demo", description="变化值报文演示")
                rule.fields = [
                    MessageFieldModel(
                        name="帧头", field_type=FieldType.FIXED, codec_type=CodecType.HEX_BYTES,
                        sort_no=1, config_json=json.dumps({"value": "AA55"})
                    ),
                    MessageFieldModel(
                        name="设备地址", field_type=FieldType.FIXED, codec_type=CodecType.UINT8,
                        sort_no=2, config_json=json.dumps({"value": 1})
                    ),
                    MessageFieldModel(
                        name="时间", field_type=FieldType.TIME, codec_type=CodecType.ASCII,
                        sort_no=3, config_json=json.dumps({"format": "HHmmss"})
                    ),
                    MessageFieldModel(
                        name="模拟值", field_type=FieldType.CHANGE, codec_type=CodecType.INT16_BE,
                        sort_no=4, config_json=json.dumps({
                            "initial": 25.0, "mode": "RANDOM_WALK", "step_min": -3,
                            "step_max": 3, "min": -40, "max": 60, "scale": 10,
                            "precision": 1, "boundary": "BOUNCE"
                        })
                    ),
                    MessageFieldModel(
                        name="序号", field_type=FieldType.SEQUENCE, codec_type=CodecType.UINT8,
                        sort_no=5, config_json=json.dumps({"initial": 0, "step": 1, "min": 0, "max": 255})
                    ),
                    MessageFieldModel(
                        name="校验", field_type=FieldType.CHECKSUM, codec_type=CodecType.UINT16_LE,
                        sort_no=6, config_json=json.dumps({"algorithm": "CRC16_MODBUS", "start": 0, "end": 4})
                    ),
                ]
                session.add(rule)
                session.flush()

            receive = session.scalar(select(ReceiveRuleModel).limit(1))
            if not receive:
                receive = ReceiveRuleModel(
                    name="Echo Demo 请求", match_type="HEX_PATTERN", pattern="AA 55 ?? 03"
                )
                receive.fields = [
                    ReceiveFieldModel(name="address", offset=2, length=1, codec_type=CodecType.UINT8)
                ]
                session.add(receive)
                session.flush()

            task_count = session.scalar(select(func.count(AutomationTaskModel.id))) or 0
            if not task_count:
                communications = list(session.scalars(select(CommunicationModel).order_by(CommunicationModel.id)))
                if communications:
                    source = communications[min(1, len(communications) - 1)]
                    target = communications[0]
                    session.add_all([
                        AutomationTaskModel(
                            name="TCP01_心跳包", enabled=False, trigger_type=TriggerType.TIMER,
                            communication_id=target.id, message_rule_id=rule.id,
                            target_type=TaskTargetType.COMMUNICATION,
                            target_communication_id=target.id,
                            config_json=json.dumps({"interval_ms": 1000, "delay_ms": 0}),
                        ),
                        AutomationTaskModel(
                            name="读取命令自动回复", enabled=False, trigger_type=TriggerType.RECEIVE,
                            communication_id=source.id, receive_rule_id=receive.id,
                            message_rule_id=rule.id, target_type=TaskTargetType.TCP_CURRENT_SESSION,
                            target_communication_id=source.id,
                            config_json=json.dumps({"delay_ms": 100}),
                        ),
                    ])
            session.commit()

    def load_channels(self) -> None:
        """从配置创建通道；auto_start 通道随后自动打开。"""
        for item in self.communications.list_all():
            config = json.loads(item.config_json or "{}")
            self.manager.create_channel(item.id, item.name, item.communication_type, config)
            if item.enabled and item.auto_start:
                self.manager.open(item.id)

    def list_rules_with_fields(self) -> list[MessageRuleModel]:
        with self.session_factory() as session:
            statement = select(MessageRuleModel).options(selectinload(MessageRuleModel.fields)).order_by(MessageRuleModel.id)
            return list(session.scalars(statement))

    def copy_message_rule(self, rule_id: int, new_name: str) -> MessageRuleModel | None:
        """深复制报文规则及其全部字段配置。"""
        source = self.get_rule(rule_id)
        if not source:
            return None
        with self.session_factory() as session:
            copied = MessageRuleModel(name=new_name, description=source.description)
            copied.fields = [
                MessageFieldModel(
                    name=item.name,
                    field_type=item.field_type,
                    codec_type=item.codec_type,
                    sort_no=item.sort_no,
                    enabled=item.enabled,
                    config_json=item.config_json,
                )
                for item in source.fields
            ]
            session.add(copied)
            session.commit()
            session.refresh(copied)
            return copied

    def get_rule(self, rule_id: int) -> MessageRuleModel | None:
        with self.session_factory() as session:
            statement = (
                select(MessageRuleModel)
                .where(MessageRuleModel.id == rule_id)
                .options(selectinload(MessageRuleModel.fields))
            )
            return session.scalar(statement)

    def get_receive_rule(self, rule_id: int) -> ReceiveRuleModel | None:
        """读取接收规则及其字段解析配置。"""
        with self.session_factory() as session:
            statement = (
                select(ReceiveRuleModel)
                .where(ReceiveRuleModel.id == rule_id)
                .options(selectinload(ReceiveRuleModel.fields))
            )
            return session.scalar(statement)

    @staticmethod
    def to_field_specs(rule: MessageRuleModel) -> list[MessageFieldSpec]:
        """把 ORM 配置转换为不依赖数据库的构建规格。"""
        return [
            MessageFieldSpec(
                item.id, item.name, FieldType(item.field_type), CodecType(item.codec_type),
                json.loads(item.config_json or "{}"), item.enabled
            )
            for item in sorted(rule.fields, key=lambda row: row.sort_no)
        ]

    def preview_rule(self, rule_id: int, task_id: object = "preview") -> bytes:
        rule = self.get_rule(rule_id)
        if not rule:
            return b""
        return self.builder.build(
            self.to_field_specs(rule), BuildContext(task_id=task_id, runtime=self.runtime)
        ).data

    def add_message_field(
        self,
        rule_id: int,
        name: str,
        field_type: str,
        codec_type: str,
        config: dict[str, Any],
    ) -> MessageFieldModel:
        """新增规则字段并自动放到列表末尾。"""
        with self.session_factory() as session:
            maximum = session.scalar(
                select(func.max(MessageFieldModel.sort_no)).where(MessageFieldModel.rule_id == rule_id)
            ) or 0
            item = MessageFieldModel(
                rule_id=rule_id, name=name, field_type=field_type, codec_type=codec_type,
                sort_no=maximum + 1, config_json=json.dumps(config, ensure_ascii=False)
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def update_message_field(
        self,
        field_id: int,
        *,
        name: str,
        codec_type: str,
        config: dict[str, Any],
        enabled: bool = True,
    ) -> None:
        """保存字段编辑器中的配置。"""
        with self.session_factory() as session:
            item = session.get(MessageFieldModel, field_id)
            if not item:
                return
            item.name = name
            item.codec_type = codec_type
            item.enabled = enabled
            item.config_json = json.dumps(config, ensure_ascii=False)
            session.commit()

    def delete_message_field(self, field_id: int) -> None:
        with self.session_factory() as session:
            item = session.get(MessageFieldModel, field_id)
            if item:
                session.delete(item)
                session.commit()

    def get_message_field(self, field_id: int) -> MessageFieldModel | None:
        with self.session_factory() as session:
            return session.get(MessageFieldModel, field_id)

    def save_field_order(self, rule_id: int, ordered_ids: list[int]) -> None:
        """持久化拖拽排序后的字段顺序。"""
        with self.session_factory() as session:
            for index, field_id in enumerate(ordered_ids, 1):
                item = session.get(MessageFieldModel, field_id)
                if item and item.rule_id == rule_id:
                    item.sort_no = index
            session.commit()

    def add_receive_field(
        self,
        rule_id: int,
        name: str,
        offset: int,
        length: int,
        codec_type: str,
        expected_value: str | None,
        required: bool,
    ) -> ReceiveFieldModel:
        """向接收规则添加一个固定位置解析字段。"""
        with self.session_factory() as session:
            item = ReceiveFieldModel(
                rule_id=rule_id, name=name, offset=offset, length=length,
                codec_type=codec_type, expected_value=expected_value, required=required,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def save_receive_rule(
        self,
        rule_id: int | None,
        *,
        name: str,
        match_type: str,
        pattern: str,
        enabled: bool,
        fields: list[dict[str, Any]],
    ) -> ReceiveRuleModel:
        """在一次事务中保存接收规则和完整字段列表。"""
        with self.session_factory() as session:
            item = session.get(ReceiveRuleModel, rule_id) if rule_id else None
            if item is None:
                item = ReceiveRuleModel(name=name, match_type=match_type, pattern=pattern)
                session.add(item)
            item.name = name
            item.match_type = match_type
            item.pattern = pattern
            item.enabled = enabled
            # 编辑器提交的是完整快照，替换关系可避免残留已删除字段。
            item.fields.clear()
            item.fields.extend(
                ReceiveFieldModel(
                    name=str(field["name"]),
                    offset=int(field["offset"]),
                    length=int(field["length"]),
                    codec_type=str(field["codec_type"]),
                    expected_value=field.get("expected_value") or None,
                    required=bool(field.get("required", True)),
                )
                for field in fields
            )
            session.commit()
            session.refresh(item)
            return item

    def delete_receive_field(self, field_id: int) -> None:
        with self.session_factory() as session:
            item = session.get(ReceiveFieldModel, field_id)
            if item:
                session.delete(item)
                session.commit()

    def shutdown(self) -> None:
        self.manager.close_all()
