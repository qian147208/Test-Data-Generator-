# -*- coding: utf-8 -*-
"""数据库连接 API 路由"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..schemas import ConnectionRequest, ConnectionResponse, ConnectionStatus, APIResponse, ErrorResponse
from ...db_connector import DatabaseConnector, DatabaseConfig
from ...db_connector.exceptions import DatabaseConnectionError, DatabaseConfigError
from ...schema_parser import SchemaParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["连接管理"])

_connection_manager: Optional[DatabaseConnector] = None
_schema_parser = None

def get_connection_manager() -> DatabaseConnector:
    """获取连接管理器实例"""
    if _connection_manager is None or not _connection_manager.is_connected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")
    return _connection_manager

def get_schema_parser():
    return _schema_parser

@router.post("/connect", response_model=ConnectionResponse, summary="连接数据库")
async def connect_database(request: ConnectionRequest):
    """连接数据库"""
    global _connection_manager, _schema_parser

    try:
        if _connection_manager and _connection_manager.is_connected:
            _connection_manager.disconnect()

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

        _connection_manager = DatabaseConnector(config)
        _connection_manager.connect()
        _schema_parser = SchemaParser(_connection_manager.get_engine())

        logger.info(f"数据库连接成功: {request.db_type} - {request.database}")

        return ConnectionResponse(
            connected=True,
            db_type=request.db_type,
            database=request.database,
            pool_status=_connection_manager.pool_status
        )

    except (DatabaseConfigError, DatabaseConnectionError) as e:
        logger.error(f"连接错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(e, DatabaseConfigError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/disconnect", response_model=APIResponse, summary="断开连接")
async def disconnect_database():
    """断开数据库连接"""
    global _connection_manager, _schema_parser

    try:
        if _connection_manager is None or not _connection_manager.is_connected:
            return APIResponse(success=True, message="数据库未连接")

        _connection_manager.disconnect()
        _connection_manager = None
        _schema_parser = None
        logger.info("数据库连接已断开")

        return APIResponse(success=True, message="数据库连接已断开")
    except Exception as e:
        logger.error(f"Disconnect failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/status", response_model=ConnectionStatus, summary="获取连接状态")
async def get_connection_status():
    """获取数据库连接状态"""
    if _connection_manager is None or not _connection_manager.is_connected:
        return ConnectionStatus(connected=False, db_type=None, database=None, pool_status=None)

    return ConnectionStatus(
        connected=True,
        db_type=_connection_manager.config.db_type,
        database=_connection_manager.config.database,
        pool_status=_connection_manager.pool_status
    )

@router.post("/test", response_model=APIResponse, summary="测试连接")
async def test_connection(request: ConnectionRequest):
    """测试数据库连接"""
    try:
        config = DatabaseConfig(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            pool_size=5,
            max_overflow=10
        )

        temp_connector = DatabaseConnector(config)
        temp_connector.connect()
        temp_connector.test_connection()
        temp_connector.disconnect()

        logger.info(f"数据库连接测试成功: {request.db_type} - {request.database}")
        return APIResponse(success=True, message="数据库连接测试成功")

    except (DatabaseConfigError, DatabaseConnectionError) as e:
        logger.error(f"Test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(e, DatabaseConfigError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Test error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
