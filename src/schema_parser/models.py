# -*- coding: utf-8 -*-
"""表结构信息数据模型

定义用于存储表结构信息的数据类，包括字段、外键、索引等信息。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class ColumnInfo:
    """字段信息数据类
    
    存储数据库表字段的详细信息。
    
    Attributes:
        name: 字段名
        data_type: 数据类型（如 VARCHAR, INTEGER, TIMESTAMP 等）
        is_nullable: 是否允许为空
        default: 默认值
        is_primary_key: 是否为主键
        is_unique: 是否唯一
        length: 字段长度（适用于字符串类型）
        precision: 数字精度（适用于数值类型）
        scale: 小数位数（适用于浮点数类型）
        comment: 字段注释
        autoincrement: 是否自增
    """
    name: str
    data_type: str
    is_nullable: bool = True
    default: Optional[Any] = None
    is_primary_key: bool = False
    is_unique: bool = False
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    comment: Optional[str] = None
    autoincrement: bool = False
    
    def __repr__(self) -> str:
        return (
            f"ColumnInfo(name='{self.name}', data_type='{self.data_type}', "
            f"nullable={self.is_nullable}, pk={self.is_primary_key}, "
            f"unique={self.is_unique})"
        )
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'data_type': self.data_type,
            'is_nullable': self.is_nullable,
            'default': self.default,
            'is_primary_key': self.is_primary_key,
            'is_unique': self.is_unique,
            'length': self.length,
            'precision': self.precision,
            'scale': self.scale,
            'comment': self.comment,
            'autoincrement': self.autoincrement
        }


@dataclass
class ForeignKeyInfo:
    """外键信息数据类
    
    存储外键约束的详细信息。
    
    Attributes:
        name: 外键约束名称
        constrained_table: 当前表名（包含外键的表）
        constrained_columns: 当前表中受约束的字段列表
        referred_table: 关联的表名
        referred_columns: 关联表中的字段列表
        on_update: UPDATE 时的行为（如 CASCADE, SET NULL, RESTRICT 等）
        on_delete: DELETE 时的行为
    """
    name: str
    constrained_table: str
    constrained_columns: List[str]
    referred_table: str
    referred_columns: List[str]
    on_update: Optional[str] = None
    on_delete: Optional[str] = None
    
    def __repr__(self) -> str:
        cols = ', '.join(self.constrained_columns)
        ref_cols = ', '.join(self.referred_columns)
        return (
            f"ForeignKeyInfo(name='{self.name}', "
            f"{self.constrained_table}({cols}) -> "
            f"{self.referred_table}({ref_cols}))"
        )
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'constrained_table': self.constrained_table,
            'constrained_columns': self.constrained_columns,
            'referred_table': self.referred_table,
            'referred_columns': self.referred_columns,
            'on_update': self.on_update,
            'on_delete': self.on_delete
        }


@dataclass
class IndexInfo:
    """索引信息数据类
    
    存储索引的详细信息。
    
    Attributes:
        name: 索引名称
        table_name: 表名
        columns: 索引包含的字段列表
        is_unique: 是否为唯一索引
        is_primary: 是否为主键索引
        index_type: 索引类型（如 BTREE, HASH 等）
    """
    name: str
    table_name: str
    columns: List[str]
    is_unique: bool = False
    is_primary: bool = False
    index_type: Optional[str] = None
    
    def __repr__(self) -> str:
        cols = ', '.join(self.columns)
        return (
            f"IndexInfo(name='{self.name}', table='{self.table_name}', "
            f"columns=[{cols}], unique={self.is_unique})"
        )
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'table_name': self.table_name,
            'columns': self.columns,
            'is_unique': self.is_unique,
            'is_primary': self.is_primary,
            'index_type': self.index_type
        }


@dataclass
class CheckConstraintInfo:
    """CHECK 约束信息数据类
    
    存储CHECK约束的详细信息。
    
    Attributes:
        name: 约束名称
        table_name: 表名
        columns: 涉及的字段列表
        condition: 约束条件表达式
    """
    name: str
    table_name: str
    columns: List[str]
    condition: str
    
    def __repr__(self) -> str:
        return (
            f"CheckConstraintInfo(name='{self.name}', "
            f"table='{self.table_name}', condition='{self.condition}')"
        )
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'table_name': self.table_name,
            'columns': self.columns,
            'condition': self.condition
        }


@dataclass
class TableSchema:
    """表结构信息数据类
    
    存储完整的表结构信息。
    
    Attributes:
        table_name: 表名
        schema: 表所属的 schema（PostgreSQL）
        columns: 字段列表
        primary_keys: 主键字段列表
        foreign_keys: 外键列表
        indexes: 索引列表
        check_constraints: CHECK 约束列表
        comment: 表注释
    """
    table_name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    check_constraints: List[CheckConstraintInfo] = field(default_factory=list)
    schema: Optional[str] = None
    comment: Optional[str] = None
    
    def __repr__(self) -> str:
        return (
            f"TableSchema(table='{self.table_name}', "
            f"columns={len(self.columns)}, "
            f"pks={len(self.primary_keys)}, "
            f"fks={len(self.foreign_keys)}, "
            f"indexes={len(self.indexes)})"
        )
    
    def get_column(self, column_name: str) -> Optional[ColumnInfo]:
        """根据字段名获取字段信息
        
        Args:
            column_name: 字段名
            
        Returns:
            字段信息，如果不存在则返回 None
        """
        for col in self.columns:
            if col.name == column_name:
                return col
        return None
    
    def get_primary_key_columns(self) -> List[ColumnInfo]:
        """获取所有主键字段的详细信息
        
        Returns:
            主键字段列表
        """
        return [col for col in self.columns if col.is_primary_key]
    
    def get_foreign_keys_by_column(self, column_name: str) -> List[ForeignKeyInfo]:
        """根据字段名获取相关的外键信息
        
        Args:
            column_name: 字段名
            
        Returns:
            外键信息列表
        """
        return [
            fk for fk in self.foreign_keys 
            if column_name in fk.constrained_columns
        ]
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'table_name': self.table_name,
            'schema': self.schema,
            'columns': [col.to_dict() for col in self.columns],
            'primary_keys': self.primary_keys,
            'foreign_keys': [fk.to_dict() for fk in self.foreign_keys],
            'indexes': [idx.to_dict() for idx in self.indexes],
            'check_constraints': [cc.to_dict() for cc in self.check_constraints],
            'comment': self.comment
        }
