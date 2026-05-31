# -*- coding: utf-8 -*-
"""数据库连接模块

负责管理不同数据库类型的连接，支持:
- PostgreSQL
- MySQL
- SQLite
"""

from .config import DatabaseConfig
from .connector import DatabaseConnector, Base
from .exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseConfigError,
    DatabaseTypeError,
    DatabaseSessionError
)

__all__ = [
    # 配置类
    'DatabaseConfig',
    # 连接管理器
    'DatabaseConnector',
    # 声明基类
    'Base',
    # 异常类
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseConfigError',
    'DatabaseTypeError',
    'DatabaseSessionError'
]
