# -*- coding: utf-8 -*-
"""数据库连接管理器模块

提供数据库连接的创建、管理和销毁功能。
"""

import logging
from contextlib import contextmanager
from typing import Optional, Generator

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig
from .exceptions import (
    DatabaseConnectionError,
    DatabaseSessionError,
    DatabaseConfigError
)

logger = logging.getLogger(__name__)

# 声明基类
Base = declarative_base()


class DatabaseConnector:
    """数据库连接管理器

    管理数据库连接的生命周期，提供连接池、会话管理等功能。

    Attributes:
        config: 数据库配置
        _engine: SQLAlchemy 引擎实例
        _session_factory: 会话工厂
        _is_connected: 连接状态标志
    """

    def __init__(self, config: DatabaseConfig):
        """初始化数据库连接管理器

        Args:
            config: 数据库配置实例

        Raises:
            DatabaseConfigError: 配置无效时抛出
        """
        if not isinstance(config, DatabaseConfig):
            raise DatabaseConfigError(
                message="配置必须是 DatabaseConfig 实例",
                config_value=type(config).__name__,
                expected_type='DatabaseConfig'
            )

        self.config = config
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._is_connected: bool = False

        logger.info(f"数据库连接管理器已初始化: {config.db_type} - {config.database}")

    def connect(self) -> Engine:
        """建立数据库连接

        创建 SQLAlchemy 引擎和连接池，初始化会话工厂。

        Returns:
            SQLAlchemy Engine 实例

        Raises:
            DatabaseConnectionError: 连接失败时抛出
        """
        if self._is_connected and self._engine is not None:
            logger.debug("数据库已连接，返回现有引擎")
            return self._engine

        try:
            # 获取连接 URL 和连接池配置
            connection_url = self.config.get_connection_url()
            pool_config = self.config.get_pool_config()

            logger.info(f"正在连接数据库: {self.config.db_type} - {self.config.host}:{self.config.port}")

            # 创建引擎
            self._engine = create_engine(
                connection_url,
                poolclass=QueuePool,
                **pool_config
            )

            # 为 SQLite 添加特殊配置
            if self.config.db_type == 'sqlite':
                @event.listens_for(self._engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    try:
                        cursor.execute("PRAGMA foreign_keys=ON")
                    finally:
                        cursor.close()

            # 创建会话工厂
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )

            # 测试连接
            self.test_connection()

            self._is_connected = True
            logger.info("数据库连接成功")

            return self._engine

        except SQLAlchemyError as e:
            logger.error("Database connection failed: %s", repr(e))
            self._is_connected = False
            raise DatabaseConnectionError(
                message="Database connection failed",
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                original_error=e
            )
        except Exception as e:
            logger.error("Database connection unexpected error: %s", repr(e))
            self._is_connected = False
            raise DatabaseConnectionError(
                message="Database connection unexpected error",
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                original_error=e
            )

    def disconnect(self) -> None:
        """关闭数据库连接

        释放连接池资源，关闭所有连接。

        Raises:
            DatabaseSessionError: 关闭连接失败时抛出
        """
        if not self._is_connected or self._engine is None:
            logger.debug("数据库未连接，无需断开")
            return

        try:
            logger.info("正在关闭数据库连接...")

            # 释放连接池
            self._engine.dispose()

            self._engine = None
            self._session_factory = None
            self._is_connected = False

            logger.info("Database connection closed")

        except Exception as e:
            logger.error("Failed to close connection: %s", e)
            raise DatabaseSessionError(
                message="Failed to close connection",
                operation='disconnect',
                original_error=e
            )

    def get_engine(self) -> Engine:
        """获取 SQLAlchemy 引擎

        如果未连接则自动建立连接。

        Returns:
            SQLAlchemy Engine 实例

        Raises:
            DatabaseConnectionError: 获取引擎失败时抛出
        """
        if self._engine is None:
            return self.connect()
        return self._engine

    def get_session(self) -> Session:
        """获取数据库会话

        创建新的数据库会话实例。

        Returns:
            SQLAlchemy Session 实例

        Raises:
            DatabaseSessionError: 创建会话失败时抛出
        """
        if not self._is_connected or self._session_factory is None:
            self.connect()

        try:
            session = self._session_factory()
            logger.debug("New session created: %s", id(session))
            return session
        except Exception as e:
            logger.error("Failed to create session: %s", e)
            raise DatabaseSessionError(
                message="Failed to create database session",
                operation='get_session',
                original_error=e
            )

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """会话上下文管理器

        提供自动提交和回滚的会话管理。

        Yields:
            SQLAlchemy Session 实例

        Example:
            >>> with connector.session_scope() as session:
            ...     session.execute(text("SELECT 1"))
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
            logger.debug("Session committed: %s", id(session))
        except Exception as e:
            session.rollback()
            logger.error("Session rolled back: %s", e)
            raise DatabaseSessionError(
                message="Session failed, rolled back",
                operation='session_scope',
                original_error=e
            )
        finally:
            session.close()
            logger.debug("Session closed: %s", id(session))

    def test_connection(self) -> bool:
        """测试数据库连接

        执行简单查询验证连接是否正常。

        Returns:
            连接成功返回 True

        Raises:
            DatabaseConnectionError: 连接测试失败时抛出
        """
        if self._engine is None:
            raise DatabaseConnectionError(
                message="数据库引擎未初始化",
                database=self.config.database
            )

        try:
            # 执行简单查询测试连接
            with self._engine.connect() as connection:
                if self.config.db_type == 'sqlite':
                    connection.execute(text("SELECT 1"))
                else:
                    connection.execute(text("SELECT 1"))

            logger.debug("数据库连接测试成功")
            return True

        except SQLAlchemyError as e:
            logger.error("Database connection test failed: %s", repr(e))
            raise DatabaseConnectionError(
                message="Database connection test failed",
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                original_error=e
            )

    def create_tables(self, base: Optional[type] = None) -> None:
        """创建数据表

        根据模型创建数据库表结构。

        Args:
            base: SQLAlchemy 声明基类，默认使用模块内的 Base

        Raises:
            DatabaseSessionError: 创建表失败时抛出
        """
        if base is None:
            base = Base

        try:
            engine = self.get_engine()
            base.metadata.create_all(engine)
            logger.info("数据表创建成功")
        except Exception as e:
            logger.error(f"创建数据表失败: {e}")
            raise DatabaseSessionError(
                message="创建数据表失败",
                operation='create_tables',
                original_error=e
            )

    def drop_tables(self, base: Optional[type] = None) -> None:
        """删除数据表

        删除所有表结构（谨慎使用）。

        Args:
            base: SQLAlchemy 声明基类，默认使用模块内的 Base

        Raises:
            DatabaseSessionError: 删除表失败时抛出
        """
        if base is None:
            base = Base

        try:
            engine = self.get_engine()
            base.metadata.drop_all(engine)
            logger.warning("所有数据表已删除")
        except Exception as e:
            logger.error(f"删除数据表失败: {e}")
            raise DatabaseSessionError(
                message="删除数据表失败",
                operation='drop_tables',
                original_error=e
            )

    def execute_raw_sql(self, sql: str, params: Optional[dict] = None) -> None:
        """执行原生 SQL

        执行原生 SQL 语句，用于特殊场景。

        Args:
            sql: SQL 语句
            params: SQL 参数

        Raises:
            DatabaseSessionError: 执行失败时抛出
        """
        try:
            with self.session_scope() as session:
                session.execute(text(sql), params or {})
            logger.debug(f"执行原生 SQL 成功: {sql[:50]}...")
        except Exception as e:
            logger.error(f"执行原生 SQL 失败: {e}")
            raise DatabaseSessionError(
                message="执行原生 SQL 失败",
                operation='execute_raw_sql',
                original_error=e
            )

    @property
    def is_connected(self) -> bool:
        """获取连接状态

        Returns:
            已连接返回 True
        """
        return self._is_connected

    @property
    def pool_status(self) -> dict:
        """获取连接池状态

        Returns:
            连接池状态信息字典
        """
        if self._engine is None:
            return {
                'status': 'disconnected',
                'pool_size': 0,
                'checked_in': 0,
                'checked_out': 0,
                'overflow': 0
            }

        pool = self._engine.pool
        return {
            'status': 'connected',
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'max_overflow': self.config.max_overflow
        }

    def __enter__(self) -> 'DatabaseConnector':
        """上下文管理器入口

        Returns:
            DatabaseConnector 实例
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口

        自动关闭连接。
        """
        self.disconnect()

    def __repr__(self) -> str:
        """字符串表示"""
        status = "已连接" if self._is_connected else "未连接"
        return (
            f"DatabaseConnector(db_type='{self.config.db_type}', "
            f"database='{self.config.database}', status='{status}')"
        )
