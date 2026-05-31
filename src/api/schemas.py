# -*- coding: utf-8 -*-
"""API 数据模型

定义 API 请求和响应的 Pydantic 数据模型。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==================== 通用响应模型 ====================

class APIResponse(BaseModel):
    """通用 API 响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(default="", description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")


# ==================== 数据库连接相关模型 ====================

class ConnectionRequest(BaseModel):
    """数据库连接请求"""
    db_type: str = Field(..., description="数据库类型: mysql, postgresql, sqlite")
    host: str = Field(default="localhost", description="数据库主机地址")
    port: Optional[int] = Field(default=None, description="数据库端口")
    database: str = Field(..., description="数据库名称或文件路径")
    username: str = Field(default="", description="用户名")
    password: str = Field(default="", description="密码")
    pool_size: int = Field(default=5, description="连接池大小")
    max_overflow: int = Field(default=10, description="连接池最大溢出数")

    class Config:
        json_schema_extra = {
            "example": {
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "test_db",
                "username": "root",
                "password": "password",
                "pool_size": 5,
                "max_overflow": 10
            }
        }


class ConnectionResponse(BaseModel):
    """数据库连接响应"""
    connected: bool = Field(..., description="是否已连接")
    db_type: str = Field(..., description="数据库类型")
    database: str = Field(..., description="数据库名称")
    pool_status: Optional[Dict[str, Any]] = Field(default=None, description="连接池状态")


class ConnectionStatus(BaseModel):
    """连接状态"""
    connected: bool = Field(..., description="是否已连接")
    db_type: Optional[str] = Field(default=None, description="数据库类型")
    database: Optional[str] = Field(default=None, description="数据库名称")
    pool_status: Optional[Dict[str, Any]] = Field(default=None, description="连接池状态")


# ==================== 表结构相关模型 ====================

class ColumnInfo(BaseModel):
    """字段信息"""
    name: str = Field(..., description="字段名")
    data_type: str = Field(..., description="数据类型")
    is_nullable: bool = Field(default=True, description="是否允许为空")
    default: Optional[Any] = Field(default=None, description="默认值")
    is_primary_key: bool = Field(default=False, description="是否为主键")
    is_unique: bool = Field(default=False, description="是否唯一")
    length: Optional[int] = Field(default=None, description="字段长度")
    precision: Optional[int] = Field(default=None, description="精度")
    scale: Optional[int] = Field(default=None, description="小数位数")
    comment: Optional[str] = Field(default=None, description="字段注释")
    autoincrement: bool = Field(default=False, description="是否自增")


class ForeignKeyInfo(BaseModel):
    """外键信息"""
    name: str = Field(..., description="外键名称")
    constrained_columns: List[str] = Field(..., description="当前表字段")
    referred_table: str = Field(..., description="关联表名")
    referred_columns: List[str] = Field(..., description="关联表字段")
    on_update: Optional[str] = Field(default=None, description="更新行为")
    on_delete: Optional[str] = Field(default=None, description="删除行为")


class IndexInfo(BaseModel):
    """索引信息"""
    name: str = Field(..., description="索引名称")
    columns: List[str] = Field(..., description="索引字段")
    is_unique: bool = Field(default=False, description="是否唯一索引")
    is_primary: bool = Field(default=False, description="是否主键索引")


class TableInfo(BaseModel):
    """表基本信息"""
    table_name: str = Field(..., description="表名")
    columns_count: int = Field(..., description="字段数量")
    primary_keys: List[str] = Field(default_factory=list, description="主键字段")
    foreign_keys_count: int = Field(default=0, description="外键数量")
    indexes_count: int = Field(default=0, description="索引数量")
    comment: Optional[str] = Field(default=None, description="表注释")


class TableDetail(BaseModel):
    """表详细信息"""
    table_name: str = Field(..., description="表名")
    schema: Optional[str] = Field(default=None, description="Schema 名称")
    columns: List[ColumnInfo] = Field(default_factory=list, description="字段列表")
    primary_keys: List[str] = Field(default_factory=list, description="主键字段")
    foreign_keys: List[ForeignKeyInfo] = Field(default_factory=list, description="外键列表")
    indexes: List[IndexInfo] = Field(default_factory=list, description="索引列表")
    comment: Optional[str] = Field(default=None, description="表注释")


class TableDependencies(BaseModel):
    """表依赖关系"""
    table_name: str = Field(..., description="表名")
    depends_on: List[str] = Field(default_factory=list, description="依赖的表")
    depended_by: List[str] = Field(default_factory=list, description="被依赖的表")


# ==================== 数据生成相关模型 ====================

class ColumnRuleConfig(BaseModel):
    """字段生成规则配置"""
    column_name: str = Field(..., description="字段名")
    strategy: Optional[str] = Field(default=None, description="生成策略")
    generator_params: Optional[Dict[str, Any]] = Field(default=None, description="生成器参数")
    custom_values: Optional[List[Any]] = Field(default=None, description="自定义值列表")


class GenerateRequest(BaseModel):
    """数据生成请求"""
    table_name: str = Field(..., description="表名")
    count: int = Field(default=10, ge=1, le=10000, description="生成行数")
    strategy: str = Field(default="normal", description="生成策略: normal, boundary, abnormal, mixed")
    column_rules: Optional[List[ColumnRuleConfig]] = Field(default=None, description="字段规则配置")
    locale: str = Field(default="zh_CN", description="语言区域")

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "users",
                "count": 100,
                "strategy": "normal",
                "column_rules": [
                    {
                        "column_name": "status",
                        "custom_values": ["active", "inactive", "pending"]
                    }
                ],
                "locale": "zh_CN"
            }
        }


class GenerateResponse(BaseModel):
    """数据生成响应"""
    table_name: str = Field(..., description="表名")
    strategy: str = Field(..., description="使用的策略")
    total_rows: int = Field(..., description="总行数")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="生成的数据")


class GeneratePreviewRequest(BaseModel):
    """数据预览请求"""
    table_name: str = Field(..., description="表名")
    count: int = Field(default=5, ge=1, le=20, description="预览行数")
    strategy: str = Field(default="normal", description="生成策略")


class GenerateBatchRequest(BaseModel):
    """批量生成请求"""
    tables: List[str] = Field(..., description="表名列表")
    count_per_table: int = Field(default=10, ge=1, le=10000, description="每表生成行数")
    strategy: str = Field(default="normal", description="生成策略")
    respect_dependencies: bool = Field(default=True, description="是否按依赖顺序生成")
    locale: str = Field(default="zh_CN", description="语言区域")


class GenerateBatchResponse(BaseModel):
    """批量生成响应"""
    total_tables: int = Field(..., description="总表数")
    processed_tables: int = Field(..., description="已处理表数")
    results: Dict[str, GenerateResponse] = Field(default_factory=dict, description="各表生成结果")
    generation_order: List[str] = Field(default_factory=list, description="生成顺序")
    errors: List[str] = Field(default_factory=list, description="错误信息")


# ==================== SQL 导出相关模型 ====================

class ExportRequest(BaseModel):
    """SQL 导出请求"""
    table_name: str = Field(..., description="表名")
    data: List[Dict[str, Any]] = Field(..., description="要导出的数据")
    batch_size: int = Field(default=100, ge=1, le=1000, description="批量插入大小")

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "users",
                "data": [
                    {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
                    {"id": 2, "name": "李四", "email": "lisi@example.com"}
                ],
                "batch_size": 100
            }
        }


class ExportResponse(BaseModel):
    """SQL 导出响应"""
    table_name: str = Field(..., description="表名")
    total_rows: int = Field(..., description="总行数")
    sql_statements: List[str] = Field(default_factory=list, description="SQL 语句列表")
    file_size: int = Field(default=0, description="文件大小(字节)")


class ExportBatchRequest(BaseModel):
    """批量导出请求"""
    tables_data: Dict[str, List[Dict[str, Any]]] = Field(..., description="表名到数据的映射")
    batch_size: int = Field(default=100, ge=1, le=1000, description="批量插入大小")
    include_create_table: bool = Field(default=False, description="是否包含建表语句")


class ExportBatchResponse(BaseModel):
    """批量导出响应"""
    total_tables: int = Field(..., description="总表数")
    total_rows: int = Field(..., description="总行数")
    sql_statements: List[str] = Field(default_factory=list, description="SQL 语句列表")
    file_size: int = Field(default=0, description="文件大小(字节)")


# ==================== 错误响应模型 ====================

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="操作是否成功")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
