# -*- coding: utf-8 -*-
"""SQL 导出 API 路由"""

import logging
from io import BytesIO
from typing import Dict, List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..schemas import (
    ExportRequest,
    ExportResponse,
    ExportBatchRequest,
    ExportBatchResponse,
    APIResponse,
    ErrorResponse
)
from .sql_utils import generate_insert_sql
from .generate import get_generated_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["SQL 导出"])

@router.post("/sql", response_model=ExportResponse, summary="导出 SQL INSERT 语句")
async def export_sql(request: ExportRequest):
    """导出 SQL INSERT 语句"""
    if not request.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="数据不能为空")

    sql_statements = generate_insert_sql(table_name=request.table_name, data=request.data, batch_size=request.batch_size)
    sql_content = "\n\n".join(sql_statements)
    file_size = len(sql_content.encode('utf-8'))

    logger.info(f"导出 SQL 成功: 表 '{request.table_name}'，{len(request.data)} 行数据")

    return ExportResponse(
        table_name=request.table_name,
        total_rows=len(request.data),
        sql_statements=sql_statements,
        file_size=file_size
    )

@router.post("/download", summary="下载 SQL 文件")
async def download_sql(request: ExportRequest):
    """下载 SQL 文件"""
    if not request.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="数据不能为空")

    sql_statements = generate_insert_sql(table_name=request.table_name, data=request.data, batch_size=request.batch_size)
    header = f"-- 数据导出\n-- 表名: {request.table_name}\n-- 行数: {len(request.data)}\n\n"
    sql_content = header + "\n\n".join(sql_statements)
    buffer = BytesIO(sql_content.encode('utf-8'))

    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={request.table_name}_data.sql"}
    )

@router.post("/batch", response_model=ExportBatchResponse, summary="批量导出 SQL")
async def export_batch_sql(request: ExportBatchRequest):
    """批量导出 SQL"""
    if not request.tables_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="数据不能为空")

    all_sql = []
    total_rows = 0

    for table_name, data in request.tables_data.items():
        if not data:
            continue
        all_sql.extend([f"-- 表: {table_name}", f"-- 行数: {len(data)}"])
        sqls = generate_insert_sql(table_name=table_name, data=data, batch_size=request.batch_size)
        all_sql.extend(sqls)
        all_sql.append("")
        total_rows += len(data)

    sql_content = "\n".join(all_sql)

    return ExportBatchResponse(
        total_tables=len(request.tables_data),
        total_rows=total_rows,
        sql_statements=all_sql,
        file_size=len(sql_content.encode('utf-8'))
    )

@router.post("/batch/download", summary="下载批量 SQL 文件")
async def download_batch_sql(request: ExportBatchRequest):
    """下载批量 SQL 文件"""
    if not request.tables_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="数据不能为空")

    all_sql = [f"-- 批量数据导出\n-- 表数量: {len(request.tables_data)}\n"]
    total_rows = 0

    for table_name, data in request.tables_data.items():
        if not data:
            continue
        all_sql.extend([f"-- 表: {table_name}", f"-- 行数: {len(data)}"])
        sqls = generate_insert_sql(table_name=table_name, data=data, batch_size=request.batch_size)
        all_sql.extend(sqls)
        all_sql.append("")
        total_rows += len(data)

    buffer = BytesIO("\n".join(all_sql).encode('utf-8'))

    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=batch_export.sql"}
    )

@router.get("/data/{table_name}", response_model=APIResponse, summary="获取已生成的数据")
async def get_stored_data(table_name: str):
    """获取已生成的数据"""
    data = get_generated_data(table_name)
    if data is None:
        return APIResponse(success=False, message=f"表 '{table_name}' 没有已生成的数据")
    return APIResponse(success=True, message=f"获取表 '{table_name}' 的数据成功", data=data)
