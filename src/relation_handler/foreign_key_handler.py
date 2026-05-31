# -*- coding: utf-8 -*-
"""外键值关联填充模块

存储已生成的数据，并为外键字段填充正确的关联值。
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
import random

from ..schema_parser.models import TableSchema, ForeignKeyInfo, ColumnInfo


class ForeignKeyHandler:
    """外键值关联填充器
    
    管理已生成的数据，并为外键字段填充正确的关联值。
    
    Example:
        >>> handler = ForeignKeyHandler()
        >>> handler.store_generated_data('users', [{'id': 1, 'name': 'Alice'}])
        >>> values = handler.get_referenced_values('users', 'id')
        >>> print(values)  # [1]
    """
    
    def __init__(self, seed: Optional[int] = None):
        """初始化外键处理器
        
        Args:
            seed: 随机种子，用于可重复的数据生成
        """
        self._generated_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._column_values: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))
        self._primary_keys: Dict[str, List[str]] = {}
        self._random = random.Random(seed)
    
    def store_generated_data(
        self, 
        table_name: str, 
        data: List[Dict[str, Any]],
        primary_keys: Optional[List[str]] = None
    ) -> None:
        """存储已生成的数据
        
        Args:
            table_name: 表名
            data: 生成的数据列表
            primary_keys: 主键字段列表
        """
        self._generated_data[table_name].extend(data)
        
        # 存储每个字段的值
        for row in data:
            for column_name, value in row.items():
                if value is not None:
                    self._column_values[table_name][column_name].append(value)
        
        # 存储主键信息
        if primary_keys:
            self._primary_keys[table_name] = primary_keys
    
    def get_referenced_values(
        self, 
        table_name: str, 
        column_name: str
    ) -> List[Any]:
        """获取被引用表的值
        
        Args:
            table_name: 被引用的表名
            column_name: 被引用的字段名
            
        Returns:
            可用的值列表
        """
        return self._column_values[table_name][column_name].copy()
    
    def get_random_referenced_value(
        self, 
        table_name: str, 
        column_name: str
    ) -> Optional[Any]:
        """随机获取一个被引用表的值
        
        Args:
            table_name: 被引用的表名
            column_name: 被引用的字段名
            
        Returns:
            随机选择的值，如果没有可用值则返回 None
        """
        values = self.get_referenced_values(table_name, column_name)
        if values:
            return self._random.choice(values)
        return None
    
    def fill_foreign_keys(
        self, 
        table_data: List[Dict[str, Any]], 
        foreign_keys: List[ForeignKeyInfo],
        table_schema: Optional[TableSchema] = None
    ) -> List[Dict[str, Any]]:
        """填充外键值
        
        为数据行中的外键字段填充正确的关联值。
        
        Args:
            table_data: 待填充的数据列表
            foreign_keys: 外键信息列表
            table_schema: 可选的表结构信息
            
        Returns:
            填充后的数据列表
        """
        if not foreign_keys:
            return table_data
        
        filled_data = []
        
        for row in table_data:
            filled_row = row.copy()
            
            for fk in foreign_keys:
                # 跳过自引用外键（由 SelfReferenceHandler 处理）
                if fk.referred_table == table_schema.table_name if table_schema else '':
                    continue
                
                # 填充外键字段
                self._fill_single_foreign_key(filled_row, fk)
            
            filled_data.append(filled_row)
        
        return filled_data
    
    def _fill_single_foreign_key(
        self, 
        row: Dict[str, Any], 
        foreign_key: ForeignKeyInfo
    ) -> None:
        """填充单个外键
        
        Args:
            row: 数据行
            foreign_key: 外键信息
        """
        referred_table = foreign_key.referred_table
        
        for i, constrained_col in enumerate(foreign_key.constrained_columns):
            # 如果字段已有值且不为空，跳过
            if constrained_col in row and row[constrained_col] is not None:
                continue
            
            # 获取被引用字段的值
            if i < len(foreign_key.referred_columns):
                referred_col = foreign_key.referred_columns[i]
                value = self.get_random_referenced_value(referred_table, referred_col)
                
                if value is not None:
                    row[constrained_col] = value
    
    def fill_foreign_keys_batch(
        self,
        table_data: List[Dict[str, Any]],
        foreign_keys: List[ForeignKeyInfo],
        table_schema: Optional[TableSchema] = None,
        distribution: str = 'random'
    ) -> List[Dict[str, Any]]:
        """批量填充外键值
        
        支持不同的分布策略。
        
        Args:
            table_data: 待填充的数据列表
            foreign_keys: 外键信息列表
            table_schema: 可选的表结构信息
            distribution: 分布策略 ('random', 'uniform', 'sequential')
            
        Returns:
            填充后的数据列表
        """
        if not foreign_keys:
            return table_data
        
        # 过滤非自引用外键
        non_self_fks = [
            fk for fk in foreign_keys
            if fk.referred_table != (table_schema.table_name if table_schema else '')
        ]
        
        if not non_self_fks:
            return table_data
        
        # 为每个外键准备值池
        fk_value_pools: Dict[str, List[Any]] = {}
        for fk in non_self_fks:
            for i, constrained_col in enumerate(fk.constrained_columns):
                if i < len(fk.referred_columns):
                    referred_col = fk.referred_columns[i]
                    pool_key = f"{fk.referred_table}.{referred_col}"
                    if pool_key not in fk_value_pools:
                        values = self.get_referenced_values(fk.referred_table, referred_col)
                        if values:
                            fk_value_pools[pool_key] = values
        
        filled_data = []
        
        for idx, row in enumerate(table_data):
            filled_row = row.copy()
            
            for fk in non_self_fks:
                for i, constrained_col in enumerate(fk.constrained_columns):
                    if constrained_col in filled_row and filled_row[constrained_col] is not None:
                        continue
                    
                    if i < len(fk.referred_columns):
                        referred_col = fk.referred_columns[i]
                        pool_key = f"{fk.referred_table}.{referred_col}"
                        
                        if pool_key in fk_value_pools:
                            pool = fk_value_pools[pool_key]
                            
                            if distribution == 'random':
                                value = self._random.choice(pool)
                            elif distribution == 'uniform':
                                value = pool[idx % len(pool)]
                            elif distribution == 'sequential':
                                value = pool[idx % len(pool)]
                            else:
                                value = self._random.choice(pool)
                            
                            filled_row[constrained_col] = value
            
            filled_data.append(filled_row)
        
        return filled_data
    
    def get_generated_data(self, table_name: str) -> List[Dict[str, Any]]:
        """获取已生成的数据
        
        Args:
            table_name: 表名
            
        Returns:
            已生成的数据列表
        """
        return self._generated_data[table_name].copy()
    
    def get_generated_count(self, table_name: str) -> int:
        """获取已生成数据的数量
        
        Args:
            table_name: 表名
            
        Returns:
            数据数量
        """
        return len(self._generated_data[table_name])
    
    def has_available_values(
        self, 
        table_name: str, 
        column_name: str
    ) -> bool:
        """检查是否有可用的引用值
        
        Args:
            table_name: 表名
            column_name: 字段名
            
        Returns:
            是否有可用值
        """
        return bool(self._column_values[table_name][column_name])
    
    def get_available_value_count(
        self, 
        table_name: str, 
        column_name: str
    ) -> int:
        """获取可用值的数量
        
        Args:
            table_name: 表名
            column_name: 字段名
            
        Returns:
            可用值数量
        """
        return len(self._column_values[table_name][column_name])
    
    def clear_table_data(self, table_name: str) -> None:
        """清除指定表的数据
        
        Args:
            table_name: 表名
        """
        if table_name in self._generated_data:
            del self._generated_data[table_name]
        if table_name in self._column_values:
            del self._column_values[table_name]
        if table_name in self._primary_keys:
            del self._primary_keys[table_name]
    
    def clear_all_data(self) -> None:
        """清除所有数据"""
        self._generated_data.clear()
        self._column_values.clear()
        self._primary_keys.clear()
    
    def get_table_names(self) -> List[str]:
        """获取所有已存储数据的表名
        
        Returns:
            表名列表
        """
        return list(self._generated_data.keys())
    
    def get_foreign_key_status(
        self, 
        foreign_key: ForeignKeyInfo
    ) -> Dict[str, Any]:
        """获取外键状态信息
        
        Args:
            foreign_key: 外键信息
            
        Returns:
            状态信息字典
        """
        status = {
            'constrained_table': foreign_key.constrained_table,
            'constrained_columns': foreign_key.constrained_columns,
            'referred_table': foreign_key.referred_table,
            'referred_columns': foreign_key.referred_columns,
            'available_values': {},
            'can_fill': True
        }
        
        for col in foreign_key.referred_columns:
            values = self.get_referenced_values(foreign_key.referred_table, col)
            status['available_values'][col] = {
                'count': len(values),
                'sample': values[:5] if values else []
            }
            if not values:
                status['can_fill'] = False
        
        return status
    
    def validate_foreign_key_values(
        self, 
        data: List[Dict[str, Any]], 
        foreign_key: ForeignKeyInfo
    ) -> Tuple[bool, List[str]]:
        """验证外键值的有效性
        
        检查数据中的外键值是否都存在于被引用表中。
        
        Args:
            data: 数据列表
            foreign_key: 外键信息
            
        Returns:
            元组：(是否有效, 错误信息列表)
        """
        errors = []
        
        for i, constrained_col in enumerate(foreign_key.constrained_columns):
            if i >= len(foreign_key.referred_columns):
                break
            
            referred_col = foreign_key.referred_columns[i]
            valid_values = set(self.get_referenced_values(
                foreign_key.referred_table, referred_col
            ))
            
            for row_idx, row in enumerate(data):
                value = row.get(constrained_col)
                if value is not None and value not in valid_values:
                    errors.append(
                        f"行 {row_idx}: 外键 '{constrained_col}' 的值 '{value}' "
                        f"在被引用表 '{foreign_key.referred_table}' 的字段 '{referred_col}' 中不存在"
                    )
        
        return len(errors) == 0, errors
    
    def set_seed(self, seed: int) -> None:
        """设置随机种子
        
        Args:
            seed: 随机种子
        """
        self._random = random.Random(seed)
