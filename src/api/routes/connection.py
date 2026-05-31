# -*- coding: utf-8 -*-
"""数据库连接 API 路由

提供数据库连接管理的 RESTful API 接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    ConnectionRequest,
    ConnectionResponse,
    ConnectionStatus,
    APIResponse,
    ErrorResponse
)
from ...db_connector import DatabaseConnector, DatabaseConfig
from ...db_connector.exceptions import (
    DatabaseConnectionError,
    DatabaseConfigError
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["连接管理"])

# 全局连接管理器实例
_connection_manager: Optional[DatabaseConnector] = None
_schema_parser = None


def get_connection_manager() -> DatabaseConnector:
    """获取连接管理器实例"""
    global _connection_manager
    if _connection_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="数据库未连接，请先调用 /api/connect 接口建立连接"
        )
    return _connection_manager


def set_connection_manager(connector: DatabaseConnector):
    """设置连接管理器实例"""
    global _connection_manager
    _connection_manager = connector


def get_schema_parser():
    """获取 SchemaParser 实例"""
    global _schema_parser
    return _schema_parser


def set_schema_parser(parser):
    """设置 SchemaParser 实例"""
    global _schema_parser
    _schema_parser = parser


@router.post(
    "/connect",
    response_model=ConnectionResponse,
    responses={
        200: {"description": "连接成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "连接失败"}
    },
    summary="连接数据库",
    description="建立与指定数据库的连接"
)
async def connect_database(request: ConnectionRequest):
    """连接数据库
    
    建立与指定数据库的连接，支持 MySQL、PostgreSQL 和 SQLite。
    """
    global _connection_manager, _schema_parser
    
    try:
        # 如果已有连接，先断开
        if _connection_manager is not None and _connection_manager.is_connected:
            _connection_manager.disconnect()
        
        # 创建配置
        config = DatabaseConfig(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            pool_size=request.pool_size,
            max_overflow=request.max_overflow
        )
        
        # 创建连接管理器
        _connection_manager = DatabaseConnector(config)
        
        # 建立连接
        _connection_manager.connect()
        
        # 创建 SchemaParser
        from ...schema_parser import SchemaParser
        _schema_parser = SchemaParser(_connection_manager.get_engine())
        
        logger.info(f"数据库连接成功: {request.db_type} - {request.database}")
        
        return ConnectionResponse(
            connected=True,
            db_type=request.db_type,
            database=request.database,
            pool_status=_connection_manager.pool_status
        )
        
    except DatabaseConfigError as e:
        logger.error("Database config error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseConnectionError as e:
        logger.error("Database connection error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Unexpected connection error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/disconnect",
    response_model=APIResponse,
    responses={
        200: {"description": "断开连接成功"},
        500: {"model": ErrorResponse, "description": "断开连接失败"}
    },
    summary="断开数据库连接",
    description="关闭当前数据库连接"
)
async def disconnect_database():
    """断开数据库连接"""
    global _connection_manager, _schema_parser
    
    try:
        if _connection_manager is None or not _connection_manager.is_connected:
            return APIResponse(
                success=True,
                message="数据库未连接，无需断开"
            )
        
        _connection_manager.disconnect()
        _connection_manager = None
        _schema_parser = None
        
        logger.info("数据库连接已断开")
        
        return APIResponse(
            success=True,
            message="数据库连接已断开"
        )
        
    except Exception as e:
        logger.error("Disconnect failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/status",
    response_model=ConnectionStatus,
    responses={
        200: {"description": "获取状态成功"}
    },
    summary="获取连接状态",
    description="获取当前数据库连接状态"
)
async def get_connection_status():
    """获取数据库连接状态"""
    global _connection_manager
    
    if _connection_manager is None or not _connection_manager.is_connected:
        return ConnectionStatus(
            connected=False,
            db_type=None,
            database=None,
            pool_status=None
        )
    
    return ConnectionStatus(
        connected=True,
        db_type=_connection_manager.config.db_type,
        database=_connection_manager.config.database,
        pool_status=_connection_manager.pool_status
    )


@router.post(
    "/test",
    response_model=APIResponse,
    responses={
        200: {"description": "连接测试成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "连接测试失败"}
    },
    summary="测试连接",
    description="测试数据库连接配置是否正确"
)
async def test_connection(request: ConnectionRequest):
    """测试数据库连接
    
    测试指定的数据库连接配置是否正确，不会建立持久连接。
    """
    try:
        # 创建配置
        config = DatabaseConfig(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            pool_size=request.pool_size or 5,
            max_overflow=request.max_overflow or 10
        )
        
        # 创建临时连接管理器
        temp_connector = DatabaseConnector(config)
        
        # 建立连接并测试
        temp_connector.connect()
        temp_connector.test_connection()
        
        # 断开临时连接
        temp_connector.disconnect()
        
        logger.info(f"数据库连接测试成功: {request.db_type} - {request.database}")
        
        return APIResponse(
            success=True,
            message="数据库连接测试成功"
        )
        
    except DatabaseConfigError as e:
        logger.error("Database config error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseConnectionError as e:
        logger.error("Connection test failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Connection test unexpected error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
