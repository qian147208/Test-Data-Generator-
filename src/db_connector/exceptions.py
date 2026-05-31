# -*- coding: utf-8 -*-
"""数据库连接异常处理模块

定义数据库连接相关的自定义异常类。
"""

from typing import Optional, Any


class DatabaseError(Exception):
    """数据库操作基础异常类"""

    def __init__(self, message: str, details: Optional[Any] = None):
        """
        初始化数据库异常

        Args:
            message: 异常消息
            details: 异常详细信息
        """
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class DatabaseConnectionError(DatabaseError):
    """数据库连接异常

    当数据库连接失败时抛出此异常。
    """

    def __init__(
        self,
        message: str = "数据库连接失败",
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        初始化连接异常

        Args:
            message: 异常消息
            host: 数据库主机
            port: 数据库端口
            database: 数据库名称
            original_error: 原始异常
        """
        details = {
            'host': host,
            'port': port,
            'database': database,
            'original_error': repr(original_error) if original_error else None
        }
        # 移除 None 值
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.host = host
        self.port = port
        self.database = database
        self.original_error = original_error


class DatabaseConfigError(DatabaseError):
    """数据库配置异常

    当数据库配置无效或缺失时抛出此异常。
    """

    def __init__(
        self,
        message: str = "数据库配置无效",
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        expected_type: Optional[str] = None
    ):
        """
        初始化配置异常

        Args:
            message: 异常消息
            config_key: 配置键名
            config_value: 无效的配置值
            expected_type: 期望的类型
        """
        details = {
            'config_key': config_key,
            'config_value': config_value,
            'expected_type': expected_type
        }
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.config_key = config_key
        self.config_value = config_value
        self.expected_type = expected_type


class DatabaseTypeError(DatabaseError):
    """数据库类型异常

    当使用了不支持的数据库类型时抛出此异常。
    """

    SUPPORTED_TYPES = ['mysql', 'postgresql', 'sqlite']

    def __init__(
        self,
        message: str = "不支持的数据库类型",
        db_type: Optional[str] = None,
        supported_types: Optional[list] = None
    ):
        """
        初始化类型异常

        Args:
            message: 异常消息
            db_type: 无效的数据库类型
            supported_types: 支持的数据库类型列表
        """
        supported = supported_types or self.SUPPORTED_TYPES
        details = {
            'provided_type': db_type,
            'supported_types': supported
        }
        super().__init__(message, details)
        self.db_type = db_type
        self.supported_types = supported


class DatabaseSessionError(DatabaseError):
    """数据库会话异常

    当数据库会话操作失败时抛出此异常。
    """

    def __init__(
        self,
        message: str = "数据库会话操作失败",
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """
        初始化会话异常

        Args:
            message: 异常消息
            operation: 执行的操作
            original_error: 原始异常
        """
        details = {
            'operation': operation,
            'original_error': repr(original_error) if original_error else None
        }
        details = {k: v for k, v in details.items() if v is not None}
        super().__init__(message, details)
        self.operation = operation
        self.original_error = original_error
