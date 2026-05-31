# -*- coding: utf-8 -*-
"""数据库连接配置模块

提供数据库连接配置的数据类和配置加载功能。
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from .exceptions import DatabaseConfigError, DatabaseTypeError

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库连接配置数据类

    支持多种数据库类型的连接配置，包括 MySQL、PostgreSQL 和 SQLite。

    Attributes:
        host: 数据库主机地址
        port: 数据库端口
        database: 数据库名称（或 SQLite 文件路径）
        username: 数据库用户名
        password: 数据库密码
        db_type: 数据库类型 (mysql/postgresql/sqlite)
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出数
        pool_timeout: 连接池超时时间（秒）
        pool_recycle: 连接回收时间（秒）
        echo: 是否输出 SQL 日志
    """

    host: str = "localhost"
    port: int = 3306
    database: str = ""
    username: str = ""
    password: str = ""
    db_type: str = "mysql"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False

    # 默认端口映射
    DEFAULT_PORTS: Dict[str, int] = field(default_factory=lambda: {
        'mysql': 3306,
        'postgresql': 5432,
        'sqlite': 0
    }, repr=False)

    def __post_init__(self):
        """初始化后验证配置"""
        self._validate()
        self._set_default_port()
        logger.debug(f"数据库配置已创建: type={self.db_type}, host={self.host}, database={self.database}")

    def _validate(self):
        """验证配置参数"""
        # 验证数据库类型
        self.db_type = self.db_type.lower()
        if self.db_type not in ['mysql', 'postgresql', 'sqlite']:
            raise DatabaseTypeError(
                message=f"不支持的数据库类型: {self.db_type}",
                db_type=self.db_type
            )

        # SQLite 不需要验证 host、port、username、password
        if self.db_type != 'sqlite':
            if not self.host:
                raise DatabaseConfigError(
                    message="数据库主机地址不能为空",
                    config_key='host',
                    expected_type='str'
                )
            if not self.database:
                raise DatabaseConfigError(
                    message="数据库名称不能为空",
                    config_key='database',
                    expected_type='str'
                )
        else:
            # SQLite 需要数据库文件路径
            if not self.database:
                raise DatabaseConfigError(
                    message="SQLite 数据库文件路径不能为空",
                    config_key='database',
                    expected_type='str'
                )

        # 验证连接池参数
        if self.pool_size < 1:
            raise DatabaseConfigError(
                message="连接池大小必须大于 0",
                config_key='pool_size',
                config_value=self.pool_size,
                expected_type='positive integer'
            )

        if self.max_overflow < 0:
            raise DatabaseConfigError(
                message="连接池最大溢出数不能为负数",
                config_key='max_overflow',
                config_value=self.max_overflow,
                expected_type='non-negative integer'
            )

    def _set_default_port(self):
        """设置默认端口"""
        if self.port is None or self.port == 0:
            self.port = self.DEFAULT_PORTS.get(self.db_type, 3306)

    def get_connection_url(self) -> str:
        """生成 SQLAlchemy 连接字符串

        Returns:
            SQLAlchemy 格式的数据库连接 URL

        Raises:
            DatabaseConfigError: 配置无效时抛出
        """
        try:
            import urllib.parse
            
            if self.db_type == 'mysql':
                encoded_username = urllib.parse.quote_plus(self.username)
                encoded_password = urllib.parse.quote_plus(self.password)
                return (
                    f"mysql+pymysql://{encoded_username}:{encoded_password}"
                    f"@{self.host}:{self.port}/{self.database}"
                    f"?charset=utf8mb4&use_unicode=True"
                )
            elif self.db_type == 'postgresql':
                # 对用户名和密码进行 URL 编码
                encoded_username = urllib.parse.quote_plus(self.username)
                encoded_password = urllib.parse.quote_plus(self.password)
                # PostgreSQL 连接字符串: postgresql://user:password@host:port/database
                return (
                    f"postgresql://{encoded_username}:{encoded_password}"
                    f"@{self.host}:{self.port}/{self.database}"
                )
            elif self.db_type == 'sqlite':
                # SQLite 连接字符串: sqlite:///path/to/database.db
                # 使用四个斜杠表示绝对路径
                if self.database.startswith('/'):
                    return f"sqlite:///{self.database}"
                else:
                    return f"sqlite:///{self.database}"
            else:
                raise DatabaseTypeError(db_type=self.db_type)
        except Exception as e:
            logger.error("Failed to generate connection string: %s", e)
            raise DatabaseConfigError(
                message="Failed to generate connection string",
                original_error=e
            )

    def get_pool_config(self) -> Dict[str, Any]:
        """获取连接池配置

        Returns:
            连接池配置字典
        """
        config = {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'pool_pre_ping': True,  # 启用连接健康检查
            'echo': self.echo
        }
        
        # 为 SQLite 添加线程安全配置
        if self.db_type == 'sqlite':
            config['connect_args'] = {'check_same_thread': False}
        
        return config

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DatabaseConfig':
        """从字典创建配置实例

        Args:
            config_dict: 配置字典

        Returns:
            DatabaseConfig 实例

        Raises:
            DatabaseConfigError: 配置无效时抛出
        """
        try:
            return cls(
                host=config_dict.get('host', 'localhost'),
                port=config_dict.get('port'),
                database=config_dict.get('database', ''),
                username=config_dict.get('username', ''),
                password=config_dict.get('password', ''),
                db_type=config_dict.get('db_type', 'mysql'),
                pool_size=config_dict.get('pool_size', 5),
                max_overflow=config_dict.get('max_overflow', 10),
                pool_timeout=config_dict.get('pool_timeout', 30),
                pool_recycle=config_dict.get('pool_recycle', 3600),
                echo=config_dict.get('echo', False)
            )
        except Exception as e:
            logger.error(f"从字典创建配置失败: {e}")
            raise DatabaseConfigError(
                message="从字典创建配置失败",
                original_error=e
            )

    @classmethod
    def from_env(cls, prefix: str = 'DB') -> 'DatabaseConfig':
        """从环境变量创建配置实例

        环境变量命名规则:
        - {PREFIX}_HOST: 数据库主机
        - {PREFIX}_PORT: 数据库端口
        - {PREFIX}_DATABASE: 数据库名称
        - {PREFIX}_USERNAME: 用户名
        - {PREFIX}_PASSWORD: 密码
        - {PREFIX}_TYPE: 数据库类型
        - {PREFIX}_POOL_SIZE: 连接池大小
        - {PREFIX}_MAX_OVERFLOW: 最大溢出数
        - {PREFIX}_POOL_TIMEOUT: 连接池超时
        - {PREFIX}_POOL_RECYCLE: 连接回收时间
        - {PREFIX}_ECHO: SQL 日志开关

        Args:
            prefix: 环境变量前缀，默认为 'DB'

        Returns:
            DatabaseConfig 实例

        Raises:
            DatabaseConfigError: 配置无效时抛出
        """
        def get_env(key: str, default: Any = None, value_type: type = str) -> Any:
            """获取环境变量并转换类型"""
            value = os.getenv(f"{prefix}_{key}", default)
            if value is None:
                return None
            try:
                if value_type == bool:
                    return str(value).lower() in ('true', '1', 'yes', 'on')
                return value_type(value)
            except (ValueError, TypeError):
                return default

        try:
            return cls(
                host=get_env('HOST', 'localhost'),
                port=get_env('PORT', None, int),
                database=get_env('DATABASE', ''),
                username=get_env('USERNAME', ''),
                password=get_env('PASSWORD', ''),
                db_type=get_env('TYPE', 'mysql'),
                pool_size=get_env('POOL_SIZE', 5, int),
                max_overflow=get_env('MAX_OVERFLOW', 10, int),
                pool_timeout=get_env('POOL_TIMEOUT', 30, int),
                pool_recycle=get_env('POOL_RECYCLE', 3600, int),
                echo=get_env('ECHO', False, bool)
            )
        except Exception as e:
            logger.error(f"从环境变量创建配置失败: {e}")
            raise DatabaseConfigError(
                message="从环境变量创建配置失败",
                original_error=e
            )

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典

        Returns:
            配置字典（不包含密码）
        """
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': '******',  # 安全考虑，不返回明文密码
            'db_type': self.db_type,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'echo': self.echo
        }

    def __repr__(self) -> str:
        """安全的字符串表示，不暴露密码"""
        return (
            f"DatabaseConfig(db_type='{self.db_type}', "
            f"host='{self.host}', port={self.port}, "
            f"database='{self.database}', username='{self.username}', "
            f"password='******', pool_size={self.pool_size})"
        )
