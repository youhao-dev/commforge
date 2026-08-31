"""业务异常。"""


class CommForgeError(Exception):
    """所有可向用户展示的业务异常基类。"""


class ValidationError(CommForgeError):
    """配置或输入不合法。"""


class DependencyError(CommForgeError):
    """删除对象时仍存在引用。"""


class CommunicationError(CommForgeError):
    """通信通道操作失败。"""
