# -*- coding: utf-8 -*-
"""表结构解析模块

负责解析数据库表结构，包括:
- 表字段信息
- 主键和外键关系
- 索引信息
- 约束条件
"""

from .models import (
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    CheckConstraintInfo,
    TableSchema
)
from .parser import SchemaParser
from .constraint_parser import ConstraintParser

__all__ = [
    'ColumnInfo',
    'ForeignKeyInfo',
    'IndexInfo',
    'CheckConstraintInfo',
    'TableSchema',
    'SchemaParser',
    'ConstraintParser'
]
