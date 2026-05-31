# -*- coding: utf-8 -*-
"""约束条件解析模块

解析数据库表的各种约束条件，包括：
- NOT NULL 约束
- UNIQUE 约束
- CHECK 约束
- DEFAULT 值
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from .models import ColumnInfo, CheckConstraintInfo


class ConstraintParser:
    """约束条件解析器
    
    解析数据库字段和表级别的各种约束条件。
    支持 MySQL 和 PostgreSQL 数据库。
    """
    
    def __init__(self, dialect: str = 'mysql'):
        """初始化约束解析器
        
        Args:
            dialect: 数据库类型（'mysql' 或 'postgresql'）
        """
        self.dialect = dialect.lower()
    
    def parse_column_constraints(
        self, 
        column_info: Dict[str, Any]
    ) -> Tuple[bool, bool, Optional[Any], bool]:
        """解析字段级别的约束
        
        从 SQLAlchemy 的列信息字典中提取约束信息。
        
        Args:
            column_info: SQLAlchemy inspect 返回的列信息字典
            
        Returns:
            元组：(is_nullable, is_unique, default_value, autoincrement)
        """
        is_nullable = column_info.get('nullable', True)
        is_unique = column_info.get('unique', False)
        default = column_info.get('default')
        autoincrement = column_info.get('autoincrement', False)
        
        # 处理默认值
        if default is not None:
            default = self._parse_default_value(default)
        
        return is_nullable, is_unique, default, autoincrement
    
    def _parse_default_value(self, default: Any) -> Any:
        """解析默认值
        
        处理不同格式的默认值，包括：
        - 字符串形式的 SQL 表达式
        - Python 值
        - SQLAlchemy 的 default 对象
        
        Args:
            default: 默认值（可能是各种格式）
            
        Returns:
            解析后的默认值
        """
        if default is None:
            return None
        
        # 如果是字符串，尝试解析
        if isinstance(default, str):
            return self._parse_default_string(default)
        
        # 如果有 arg 属性（SQLAlchemy DefaultClause）
        if hasattr(default, 'arg'):
            arg = default.arg
            if isinstance(arg, str):
                return self._parse_default_string(arg)
            return arg
        
        return default
    
    def _parse_default_string(self, default_str: str) -> Any:
        """解析字符串形式的默认值
        
        将 SQL 默认值字符串转换为 Python 值。
        
        Args:
            default_str: 默认值字符串
            
        Returns:
            解析后的 Python 值
        """
        if not default_str:
            return None
        
        # 去除引号
        stripped = default_str.strip()
        
        # NULL
        if stripped.upper() == 'NULL':
            return None
        
        # 布尔值（PostgreSQL）
        if stripped.lower() in ('true', 'false'):
            return stripped.lower() == 'true'
        
        # 当前时间函数
        current_time_funcs = [
            'CURRENT_TIMESTAMP', 'NOW()', 'CURRENT_DATE', 
            'CURRENT_TIME', 'LOCALTIMESTAMP', 'LOCALTIME'
        ]
        if stripped.upper() in current_time_funcs:
            return stripped.upper()  # 保留函数名
        
        # UUID 函数
        if 'uuid_generate' in stripped.lower() or stripped.lower() == 'uuid()':
            return 'UUID_GENERATE'
        
        # 字符串（带引号）
        if (stripped.startswith("'") and stripped.endswith("'")) or \
           (stripped.startswith('"') and stripped.endswith('"')):
            return stripped[1:-1]
        
        # 数字
        try:
            if '.' in stripped:
                return float(stripped)
            return int(stripped)
        except ValueError:
            pass
        
        # 其他情况返回原始字符串
        return stripped
    
    def parse_check_constraint(
        self, 
        constraint_info: Dict[str, Any],
        table_name: str
    ) -> Optional[CheckConstraintInfo]:
        """解析 CHECK 约束
        
        Args:
            constraint_info: 约束信息字典
            table_name: 表名
            
        Returns:
            CheckConstraintInfo 对象，解析失败返回 None
        """
        name = constraint_info.get('name', '')
        condition = constraint_info.get('sqltext', '')
        
        if not condition:
            return None
        
        # 提取涉及的字段
        columns = self._extract_columns_from_condition(str(condition))
        
        return CheckConstraintInfo(
            name=name,
            table_name=table_name,
            columns=columns,
            condition=str(condition)
        )
    
    def _extract_columns_from_condition(self, condition: str) -> List[str]:
        """从条件表达式中提取字段名
        
        Args:
            condition: SQL 条件表达式
            
        Returns:
            字段名列表
        """
        # 简单的字段名提取（匹配标识符）
        # 这个正则表达式匹配可能的字段名
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, condition)
        
        # 过滤掉 SQL 关键字
        sql_keywords = {
            'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'LIKE', 'IS', 'NULL',
            'TRUE', 'FALSE', 'CHECK', 'CONSTRAINT', 'WHERE'
        }
        
        columns = []
        for match in matches:
            if match.upper() not in sql_keywords:
                columns.append(match)
        
        # 去重并保持顺序
        seen = set()
        unique_columns = []
        for col in columns:
            if col not in seen:
                seen.add(col)
                unique_columns.append(col)
        
        return unique_columns
    
    def parse_unique_constraint(
        self,
        constraint_info: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """解析 UNIQUE 约束
        
        Args:
            constraint_info: 约束信息字典
            
        Returns:
            元组：(约束名称, 字段列表)
        """
        name = constraint_info.get('name', '')
        columns = constraint_info.get('column_keys', [])
        
        if not columns:
            # 尝试其他可能的键名
            columns = constraint_info.get('columns', [])
        
        return name, columns
    
    def parse_not_null_constraint(
        self,
        column_info: Dict[str, Any]
    ) -> bool:
        """解析 NOT NULL 约束
        
        Args:
            column_info: 列信息字典
            
        Returns:
            是否为 NOT NULL（即不允许为空）
        """
        return not column_info.get('nullable', True)
    
    def get_constraint_type(self, constraint_info: Dict[str, Any]) -> str:
        """获取约束类型
        
        Args:
            constraint_info: 约束信息字典
            
        Returns:
            约束类型字符串：'primary_key', 'foreign_key', 'unique', 'check', 'unknown'
        """
        # 根据约束信息的键来判断类型
        if 'referred_table' in constraint_info or 'referred_columns' in constraint_info:
            return 'foreign_key'
        
        if 'column_keys' in constraint_info or 'columns' in constraint_info:
            # 可能是 unique 或 primary_key
            if constraint_info.get('primary_key', False):
                return 'primary_key'
            return 'unique'
        
        if 'sqltext' in constraint_info:
            return 'check'
        
        return 'unknown'
    
    def parse_enum_values(self, column_type: Any) -> Optional[List[str]]:
        """解析 ENUM 类型的可选值
        
        Args:
            column_type: SQLAlchemy 列类型对象
            
        Returns:
            ENUM 值列表，如果不是 ENUM 类型则返回 None
        """
        type_str = str(column_type).upper()
        
        # 检查是否是 ENUM 类型
        if 'ENUM' in type_str:
            # 尝试从类型字符串中提取值
            # MySQL: ENUM('value1','value2')
            # PostgreSQL: VARCHAR 或自定义 ENUM TYPE
            match = re.search(r"ENUM\((.*?)\)", type_str, re.IGNORECASE)
            if match:
                values_str = match.group(1)
                # 提取引号中的值
                values = re.findall(r"'([^']*)'", values_str)
                return values
        
        # SQLAlchemy ENUM 类型对象
        if hasattr(column_type, 'enums'):
            return list(column_type.enums)
        
        return None
    
    def is_autoincrement(
        self,
        column_info: Dict[str, Any],
        column_type: str
    ) -> bool:
        """判断字段是否为自增字段
        
        Args:
            column_info: 列信息字典
            column_type: 列数据类型
            
        Returns:
            是否为自增字段
        """
        # 直接从列信息获取
        if column_info.get('autoincrement', False):
            return True
        
        # MySQL: AUTO_INCREMENT
        # PostgreSQL: SERIAL, BIGSERIAL, SMALLSERIAL
        type_upper = column_type.upper()
        if 'SERIAL' in type_upper or 'AUTO_INCREMENT' in type_upper:
            return True
        
        return False
