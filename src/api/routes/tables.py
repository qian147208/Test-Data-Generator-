# -*- coding: utf-8 -*-
"""表结构查询 API 路由

提供表结构查询的 RESTful API 接口。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    TableInfo,
    TableDetail,
    TableDependencies,
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    APIResponse,
    ErrorResponse
)
from .connection import get_connection_manager, get_schema_parser


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tables", tags=["表结构查询"])


@router.get(
    "",
    response_model=List[TableInfo],
    responses={
        200: {"description": "获取表列表成功"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="获取所有表列表",
    description="获取数据库中所有表的列表"
)
async def get_all_tables(schema: Optional[str] = None):
    """获取所有表列表"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 使用异步方法解析所有表
        all_tables = await parser.parse_all_tables_async(schema=schema)
        tables = []
        
        for table_name, table_schema in all_tables.items():
            tables.append(TableInfo(
                table_name=table_name,
                columns_count=len(table_schema.columns),
                primary_keys=table_schema.primary_keys,
                foreign_keys_count=len(table_schema.foreign_keys),
                indexes_count=len(table_schema.indexes),
                comment=table_schema.comment
            ))
        
        return tables
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表列表失败: {str(e)}"
        )


@router.get(
    "/{table_name}",
    response_model=TableDetail,
    responses={
        200: {"description": "获取表详情成功"},
        404: {"model": ErrorResponse, "description": "表不存在"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="获取表详情",
    description="获取指定表的详细结构信息"
)
async def get_table_detail(table_name: str, schema: Optional[str] = None):
    """获取表详情"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 使用异步方法解析表
        table_schema = await parser.parse_table_async(table_name, schema=schema)
        
        if not table_schema.columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"表 '{table_name}' 不存在"
            )
        
        # 转换字段信息
        columns = [
            ColumnInfo(
                name=col.name,
                data_type=col.data_type,
                is_nullable=col.is_nullable,
                default=col.default,
                is_primary_key=col.is_primary_key,
                is_unique=col.is_unique,
                length=col.length,
                precision=col.precision,
                scale=col.scale,
                comment=col.comment,
                autoincrement=col.autoincrement
            )
            for col in table_schema.columns
        ]
        
        # 转换外键信息
        foreign_keys = [
            ForeignKeyInfo(
                name=fk.name,
                constrained_columns=fk.constrained_columns,
                referred_table=fk.referred_table,
                referred_columns=fk.referred_columns,
                on_update=fk.on_update,
                on_delete=fk.on_delete
            )
            for fk in table_schema.foreign_keys
        ]
        
        # 转换索引信息
        indexes = [
            IndexInfo(
                name=idx.name or 'unnamed_index',
                columns=idx.columns,
                is_unique=idx.is_unique,
                is_primary=idx.is_primary
            )
            for idx in table_schema.indexes
        ]
        
        return TableDetail(
            table_name=table_schema.table_name,
            schema=table_schema.schema,
            columns=columns,
            primary_keys=table_schema.primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            comment=table_schema.comment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表详情失败: {str(e)}"
        )


@router.get(
    "/{table_name}/dependencies",
    response_model=TableDependencies,
    responses={
        200: {"description": "获取依赖关系成功"},
        404: {"model": ErrorResponse, "description": "表不存在"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="获取表依赖关系",
    description="获取指定表的依赖关系，包括依赖的表和被依赖的表"
)
async def get_table_dependencies(table_name: str, schema: Optional[str] = None):
    """获取表依赖关系"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 使用异步方法获取依赖关系
        dependencies = await parser.get_table_dependencies_async(table_name, schema=schema)
        
        return TableDependencies(
            table_name=table_name,
            depends_on=dependencies['depends_on'],
            depended_by=dependencies['depended_by']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表依赖关系失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表依赖关系失败: {str(e)}"
        )


@router.get(
    "/{table_name}/columns",
    response_model=List[ColumnInfo],
    responses={
        200: {"description": "获取字段列表成功"},
        404: {"model": ErrorResponse, "description": "表不存在"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="获取表字段列表",
    description="获取指定表的所有字段信息"
)
async def get_table_columns(table_name: str, schema: Optional[str] = None):
    """获取表字段列表"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 使用异步方法解析表
        table_schema = await parser.parse_table_async(table_name, schema=schema)
        
        if not table_schema.columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"表 '{table_name}' 不存在"
            )
        
        return [
            ColumnInfo(
                name=col.name,
                data_type=col.data_type,
                is_nullable=col.is_nullable,
                default=col.default,
                is_primary_key=col.is_primary_key,
                is_unique=col.is_unique,
                length=col.length,
                precision=col.precision,
                scale=col.scale,
                comment=col.comment,
                autoincrement=col.autoincrement
            )
            for col in table_schema.columns
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取表字段列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表字段列表失败: {str(e)}"
        )


@router.get(
    "/dependencies/all",
    response_model=APIResponse,
    responses={
        200: {"description": "获取所有依赖关系成功"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="获取所有表的依赖关系",
    description="获取数据库中所有表的依赖关系"
)
async def get_all_dependencies(schema: Optional[str] = None):
    """获取所有表的依赖关系"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 使用异步方法获取所有依赖关系
        dependencies = await parser.get_all_dependencies_async(schema=schema)
        
        return APIResponse(
            success=True,
            message="获取所有依赖关系成功",
            data=dependencies
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取所有依赖关系失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有依赖关系失败: {str(e)}"
        )
