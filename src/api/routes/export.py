# -*- coding: utf-8 -*-
"""SQL 导出 API 路由

提供 SQL 导出的 RESTful API 接口。
"""

import logging
from io import BytesIO
from typing import List, Dict, Any, Optional

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
from .generate import get_generated_data


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["SQL 导出"])


def escape_value(value: Any) -> str:
    """转义 SQL 值
    
    Args:
        value: 要转义的值
        
    Returns:
        转义后的 SQL 值字符串
    """
    if value is None:
        return "NULL"
    elif isinstance(value, bool):
        return "1" if value else "0"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # 转义单引号和特殊字符
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    elif isinstance(value, bytes):
        # 处理二进制数据
        return f"X'{value.hex()}'"
    else:
        # 其他类型转为字符串
        escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"


def generate_insert_sql(
    table_name: str,
    data: List[Dict[str, Any]],
    batch_size: int = 100
) -> List[str]:
    """生成 INSERT SQL 语句
    
    Args:
        table_name: 表名
        data: 数据列表
        batch_size: 批量插入大小
        
    Returns:
        SQL 语句列表
    """
    if not data:
        return []
    
    sql_statements = []
    columns = list(data[0].keys())
    columns_str = ", ".join(f"`{col}`" for col in columns)
    
    # 分批处理
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        values_list = []
        
        for row in batch:
            values = ", ".join(escape_value(row.get(col)) for col in columns)
            values_list.append(f"({values})")
        
        values_str = ",\n".join(values_list)
        sql = f"INSERT INTO `{table_name}` ({columns_str})\nVALUES\n{values_str};"
        sql_statements.append(sql)
    
    return sql_statements


def generate_create_table_sql(
    table_name: str,
    columns_info: List[Dict[str, Any]],
    primary_keys: List[str] = None,
    foreign_keys: List[Dict[str, Any]] = None
) -> str:
    """生成 CREATE TABLE SQL 语句
    
    Args:
        table_name: 表名
        columns_info: 字段信息列表
        primary_keys: 主键字段列表
        foreign_keys: 外键信息列表
        
    Returns:
        CREATE TABLE SQL 语句
    """
    column_defs = []
    
    for col in columns_info:
        col_def = f"  `{col['name']}` {col['data_type']}"
        
        if col.get('length'):
            if col.get('scale'):
                col_def += f"({col['length']}, {col['scale']})"
            else:
                col_def += f"({col['length']})"
        
        if not col.get('is_nullable', True):
            col_def += " NOT NULL"
        
        if col.get('autoincrement'):
            col_def += " AUTO_INCREMENT"
        
        if col.get('default') is not None:
            col_def += f" DEFAULT {escape_value(col['default'])}"
        
        column_defs.append(col_def)
    
    # 添加主键约束
    if primary_keys:
        pk_str = ", ".join(f"`{pk}`" for pk in primary_keys)
        column_defs.append(f"  PRIMARY KEY ({pk_str})")
    
    # 添加外键约束
    if foreign_keys:
        for fk in foreign_keys:
            fk_cols = ", ".join(f"`{col}`" for col in fk['constrained_columns'])
            ref_cols = ", ".join(f"`{col}`" for col in fk['referred_columns'])
            fk_def = f"  FOREIGN KEY ({fk_cols}) REFERENCES `{fk['referred_table']}`({ref_cols})"
            if fk.get('on_delete'):
                fk_def += f" ON DELETE {fk['on_delete']}"
            if fk.get('on_update'):
                fk_def += f" ON UPDATE {fk['on_update']}"
            column_defs.append(fk_def)
    
    sql = f"CREATE TABLE `{table_name}` (\n"
    sql += ",\n".join(column_defs)
    sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    
    return sql


@router.post(
    "/sql",
    response_model=ExportResponse,
    responses={
        200: {"description": "导出成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"}
    },
    summary="导出 SQL INSERT 语句",
    description="将数据导出为 SQL INSERT 语句"
)
async def export_sql(request: ExportRequest):
    """导出 SQL INSERT 语句"""
    try:
        if not request.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据不能为空"
            )
        
        # 生成 SQL 语句
        sql_statements = generate_insert_sql(
            table_name=request.table_name,
            data=request.data,
            batch_size=request.batch_size
        )
        
        # 计算文件大小
        sql_content = "\n\n".join(sql_statements)
        file_size = len(sql_content.encode('utf-8'))
        
        logger.info(f"导出 SQL 成功: 表 '{request.table_name}'，{len(request.data)} 行数据")
        
        return ExportResponse(
            table_name=request.table_name,
            total_rows=len(request.data),
            sql_statements=sql_statements,
            file_size=file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出 SQL 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出 SQL 失败: {str(e)}"
        )


@router.post(
    "/download",
    responses={
        200: {
            "description": "下载 SQL 文件",
            "content": {"application/octet-stream": {}}
        },
        400: {"model": ErrorResponse, "description": "请求参数错误"}
    },
    summary="下载 SQL 文件",
    description="将数据导出为 SQL 文件并下载"
)
async def download_sql(request: ExportRequest):
    """下载 SQL 文件"""
    try:
        if not request.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据不能为空"
            )
        
        # 生成 SQL 语句
        sql_statements = generate_insert_sql(
            table_name=request.table_name,
            data=request.data,
            batch_size=request.batch_size
        )
        
        # 添加文件头注释
        header = f"-- 数据导出\n"
        header += f"-- 表名: {request.table_name}\n"
        header += f"-- 行数: {len(request.data)}\n"
        header += f"-- 批量大小: {request.batch_size}\n\n"
        
        # 组合 SQL 内容
        sql_content = header + "\n\n".join(sql_statements)
        
        # 创建字节流
        buffer = BytesIO(sql_content.encode('utf-8'))
        
        logger.info(f"下载 SQL 文件: 表 '{request.table_name}'，{len(request.data)} 行数据")
        
        return StreamingResponse(
            buffer,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={request.table_name}_data.sql"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载 SQL 文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载 SQL 文件失败: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=ExportBatchResponse,
    responses={
        200: {"description": "批量导出成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"}
    },
    summary="批量导出 SQL",
    description="批量导出多个表的数据为 SQL 语句"
)
async def export_batch_sql(request: ExportBatchRequest):
    """批量导出 SQL"""
    try:
        if not request.tables_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据不能为空"
            )
        
        all_sql_statements = []
        total_rows = 0
        total_tables = len(request.tables_data)
        
        for table_name, data in request.tables_data.items():
            if not data:
                continue
            
            # 添加表注释
            all_sql_statements.append(f"-- 表: {table_name}")
            all_sql_statements.append(f"-- 行数: {len(data)}")
            
            # 生成 INSERT 语句
            sql_statements = generate_insert_sql(
                table_name=table_name,
                data=data,
                batch_size=request.batch_size
            )
            
            all_sql_statements.extend(sql_statements)
            all_sql_statements.append("")  # 空行分隔
            
            total_rows += len(data)
        
        # 计算文件大小
        sql_content = "\n".join(all_sql_statements)
        file_size = len(sql_content.encode('utf-8'))
        
        logger.info(f"批量导出 SQL 成功: {total_tables} 个表，{total_rows} 行数据")
        
        return ExportBatchResponse(
            total_tables=total_tables,
            total_rows=total_rows,
            sql_statements=all_sql_statements,
            file_size=file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导出 SQL 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导出 SQL 失败: {str(e)}"
        )


@router.post(
    "/batch/download",
    responses={
        200: {
            "description": "下载批量导出的 SQL 文件",
            "content": {"application/octet-stream": {}}
        },
        400: {"model": ErrorResponse, "description": "请求参数错误"}
    },
    summary="下载批量导出的 SQL 文件",
    description="批量导出多个表的数据为 SQL 文件并下载"
)
async def download_batch_sql(request: ExportBatchRequest):
    """下载批量导出的 SQL 文件"""
    try:
        if not request.tables_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据不能为空"
            )
        
        all_sql_statements = []
        total_rows = 0
        
        # 添加文件头
        header = "-- 批量数据导出\n"
        header += f"-- 表数量: {len(request.tables_data)}\n\n"
        all_sql_statements.append(header)
        
        for table_name, data in request.tables_data.items():
            if not data:
                continue
            
            # 添加表注释
            all_sql_statements.append(f"-- 表: {table_name}")
            all_sql_statements.append(f"-- 行数: {len(data)}")
            
            # 生成 INSERT 语句
            sql_statements = generate_insert_sql(
                table_name=table_name,
                data=data,
                batch_size=request.batch_size
            )
            
            all_sql_statements.extend(sql_statements)
            all_sql_statements.append("")
            
            total_rows += len(data)
        
        # 组合 SQL 内容
        sql_content = "\n".join(all_sql_statements)
        
        # 创建字节流
        buffer = BytesIO(sql_content.encode('utf-8'))
        
        logger.info(f"下载批量 SQL 文件: {len(request.tables_data)} 个表，{total_rows} 行数据")
        
        return StreamingResponse(
            buffer,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=batch_export.sql"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载批量 SQL 文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载批量 SQL 文件失败: {str(e)}"
        )


@router.get(
    "/data/{table_name}",
    response_model=APIResponse,
    summary="获取已生成的数据",
    description="获取指定表的已生成数据"
)
async def get_stored_data(table_name: str):
    """获取已生成的数据"""
    data = get_generated_data(table_name)
    
    if data is None:
        return APIResponse(
            success=False,
            message=f"表 '{table_name}' 没有已生成的数据"
        )
    
    return APIResponse(
        success=True,
        message=f"获取表 '{table_name}' 的数据成功",
        data=data
    )
