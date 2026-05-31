# -*- coding: utf-8 -*-
"""表结构查询 API 路由"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    TableInfo, TableDetail, TableDependencies, ColumnInfo,
    ForeignKeyInfo, IndexInfo, APIResponse, ErrorResponse
)
from .connection import get_schema_parser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tables", tags=["表结构查询"])

@router.get("", response_model=List[TableInfo], summary="获取所有表列表")
async def get_all_tables(schema: Optional[str] = None):
    """获取所有表列表"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    all_tables = await parser.parse_all_tables_async(schema=schema)
    return [
        TableInfo(
            table_name=name,
            columns_count=len(schema.columns),
            primary_keys=schema.primary_keys,
            foreign_keys_count=len(schema.foreign_keys),
            indexes_count=len(schema.indexes),
            comment=schema.comment
        )
        for name, schema in all_tables.items()
    ]

@router.get("/{table_name}", response_model=TableDetail, summary="获取表详情")
async def get_table_detail(table_name: str, schema: Optional[str] = None):
    """获取表详情"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    table_schema = await parser.parse_table_async(table_name, schema=schema)
    if not table_schema.columns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"表 '{table_name}' 不存在")

    return TableDetail(
        table_name=table_schema.table_name,
        schema=table_schema.schema,
        columns=[ColumnInfo(
            name=c.name, data_type=c.data_type, is_nullable=c.is_nullable,
            default=c.default, is_primary_key=c.is_primary_key,
            is_unique=c.is_unique, length=c.length, precision=c.precision,
            scale=c.scale, comment=c.comment, autoincrement=c.autoincrement
        ) for c in table_schema.columns],
        primary_keys=table_schema.primary_keys,
        foreign_keys=[ForeignKeyInfo(
            name=fk.name, constrained_columns=fk.constrained_columns,
            referred_table=fk.referred_table, referred_columns=fk.referred_columns,
            on_update=fk.on_update, on_delete=fk.on_delete
        ) for fk in table_schema.foreign_keys],
        indexes=[IndexInfo(
            name=idx.name or 'unnamed_index', columns=idx.columns,
            is_unique=idx.is_unique, is_primary=idx.is_primary
        ) for idx in table_schema.indexes],
        comment=table_schema.comment
    )

@router.get("/{table_name}/dependencies", response_model=TableDependencies, summary="获取表依赖关系")
async def get_table_dependencies(table_name: str, schema: Optional[str] = None):
    """获取表依赖关系"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    deps = await parser.get_table_dependencies_async(table_name, schema=schema)
    return TableDependencies(table_name=table_name, depends_on=deps['depends_on'], depended_by=deps['depended_by'])

@router.get("/{table_name}/columns", response_model=List[ColumnInfo], summary="获取表字段列表")
async def get_table_columns(table_name: str, schema: Optional[str] = None):
    """获取表字段列表"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    table_schema = await parser.parse_table_async(table_name, schema=schema)
    if not table_schema.columns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"表 '{table_name}' 不存在")

    return [ColumnInfo(
        name=c.name, data_type=c.data_type, is_nullable=c.is_nullable,
        default=c.default, is_primary_key=c.is_primary_key,
        is_unique=c.is_unique, length=c.length, precision=c.precision,
        scale=c.scale, comment=c.comment, autoincrement=c.autoincrement
    ) for c in table_schema.columns]

@router.get("/dependencies/all", response_model=APIResponse, summary="获取所有表的依赖关系")
async def get_all_dependencies(schema: Optional[str] = None):
    """获取所有表的依赖关系"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    deps = await parser.get_all_dependencies_async(schema=schema)
    return APIResponse(success=True, message="获取所有依赖关系成功", data=deps)
