"""项目内统一使用的枚举，避免业务层散落魔法字符串。"""

from enum import StrEnum


class CommunicationType(StrEnum):
    TCP_CLIENT = "TCP_CLIENT"
    TCP_SERVER = "TCP_SERVER"
    UDP = "UDP"
    SERIAL = "SERIAL"


class CommunicationStatus(StrEnum):
    STOPPED = "STOPPED"
    CONNECTING = "CONNECTING"
    OPEN = "OPEN"
    ERROR = "ERROR"


class FieldType(StrEnum):
    FIXED = "FIXED"
    TIME = "TIME"
    CHANGE = "CHANGE"
    RANDOM = "RANDOM"
    SEQUENCE = "SEQUENCE"
    LENGTH = "LENGTH"
    CHECKSUM = "CHECKSUM"
    RECEIVED_VALUE = "RECEIVED_VALUE"
    RECEIVED_BYTES = "RECEIVED_BYTES"
    VARIABLE = "VARIABLE"
    EXPRESSION = "EXPRESSION"


class CodecType(StrEnum):
    ASCII = "ASCII"
    UTF8 = "UTF8"
    HEX_BYTES = "HEX_BYTES"
    RAW_BYTES = "RAW_BYTES"
    UINT8 = "UINT8"
    INT8 = "INT8"
    UINT16_BE = "UINT16_BE"
    UINT16_LE = "UINT16_LE"
    INT16_BE = "INT16_BE"
    INT16_LE = "INT16_LE"
    UINT32_BE = "UINT32_BE"
    UINT32_LE = "UINT32_LE"
    INT32_BE = "INT32_BE"
    INT32_LE = "INT32_LE"
    FLOAT32_BE = "FLOAT32_BE"
    FLOAT32_LE = "FLOAT32_LE"
    FLOAT64_BE = "FLOAT64_BE"
    FLOAT64_LE = "FLOAT64_LE"


class TriggerType(StrEnum):
    TIMER = "TIMER"
    RECEIVE = "RECEIVE"
    MANUAL = "MANUAL"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


class MatchType(StrEnum):
    EXACT = "EXACT"
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    REGEX = "REGEX"
    HEX_EXACT = "HEX_EXACT"
    HEX_PATTERN = "HEX_PATTERN"


class FrameDecoderType(StrEnum):
    RAW = "RAW"
    DELIMITER = "DELIMITER"
    FIXED_LENGTH = "FIXED_LENGTH"
    LENGTH_FIELD = "LENGTH_FIELD"
    IDLE_TIMEOUT = "IDLE_TIMEOUT"


class ChecksumType(StrEnum):
    XOR = "XOR"
    SUM8 = "SUM8"
    SUM16 = "SUM16"
    CRC16_MODBUS = "CRC16_MODBUS"
    CRC16_CCITT = "CRC16_CCITT"
    CRC32 = "CRC32"


class TaskTargetType(StrEnum):
    CURRENT_SOURCE = "CURRENT_SOURCE"
    COMMUNICATION = "COMMUNICATION"
    TCP_CURRENT_SESSION = "TCP_CURRENT_SESSION"
    TCP_ALL_SESSIONS = "TCP_ALL_SESSIONS"
    UDP_CURRENT_REMOTE = "UDP_CURRENT_REMOTE"


class ChangeMode(StrEnum):
    RANDOM_WALK = "RANDOM_WALK"
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    LOOP = "LOOP"
    BOUNCE = "BOUNCE"


class BoundaryPolicy(StrEnum):
    CLAMP = "CLAMP"
    WRAP = "WRAP"
    BOUNCE = "BOUNCE"
    STOP = "STOP"


class LogDirection(StrEnum):
    TX = "TX"
    RX = "RX"
