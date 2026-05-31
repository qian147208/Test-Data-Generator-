# -*- coding: utf-8 -*-
"""自引用关联处理模块

处理表的自引用外键关系，支持分批生成策略。
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import random

from ..schema_parser.models import TableSchema, ForeignKeyInfo, ColumnInfo


@dataclass
class SelfReferenceConfig:
    """自引用处理配置
    
    Attributes:
        null_ratio: 自引用字段为 NULL 的比例
        self_reference_ratio: 自引用字段引用已有记录的比例
        max_depth: 自引用的最大深度
        batch_size: 分批处理的批次大小
    """
    null_ratio: float = 0.2
    self_reference_ratio: float = 0.8
    max_depth: int = 5
    batch_size: int = 100


@dataclass
class SelfReferenceResult:
    """自引用处理结果
    
    Attributes:
        data: 处理后的数据
        null_count: NULL 值数量
        referenced_count: 引用已有记录的数量
        total_records: 总记录数
    """
    data: List[Dict[str, Any]]
    null_count: int = 0
    referenced_count: int = 0
    total_records: int = 0


class SelfReferenceHandler:
    """自引用关联处理器
    
    处理表的自引用外键关系。采用分批生成策略：
    1. 第一批：生成自引用字段为 NULL 的记录
    2. 后续批次：自引用字段引用已存在的记录
    
    Example:
        >>> handler = SelfReferenceHandler()
        >>> result = handler.handle_self_reference(table_schema, data, foreign_key)
    """
    
    def __init__(
        self, 
        config: Optional[SelfReferenceConfig] = None,
        seed: Optional[int] = None
    ):
        """初始化自引用处理器
        
        Args:
            config: 处理配置
            seed: 随机种子
        """
        self.config = config or SelfReferenceConfig()
        self._random = random.Random(seed)
        self._generated_ids: Dict[str, List[Any]] = {}
    
    def handle_self_reference(
        self, 
        table_schema: TableSchema, 
        data: List[Dict[str, Any]], 
        foreign_key: ForeignKeyInfo
    ) -> SelfReferenceResult:
        """处理自引用关联
        
        为数据中的自引用字段填充值。采用分批策略：
        - 部分记录的自引用字段设为 NULL
        - 其余记录引用已存在的记录
        
        Args:
            table_schema: 表结构信息
            data: 待处理的数据列表
            foreign_key: 自引用外键信息
            
        Returns:
            SelfReferenceResult 对象
        """
        if not data:
            return SelfReferenceResult(data=[])
        
        # 验证是否为自引用
        if foreign_key.referred_table != table_schema.table_name:
            raise ValueError(
                f"外键 '{foreign_key.name}' 不是自引用外键: "
                f"引用表 '{foreign_key.referred_table}' != 当前表 '{table_schema.table_name}'"
            )
        
        # 获取主键字段
        pk_columns = table_schema.primary_keys
        if not pk_columns:
            raise ValueError(f"表 '{table_schema.table_name}' 没有主键，无法处理自引用")
        
        # 获取自引用字段和被引用字段
        constrained_cols = foreign_key.constrained_columns
        referred_cols = foreign_key.referred_columns
        
        # 初始化已生成的 ID 列表
        table_name = table_schema.table_name
        if table_name not in self._generated_ids:
            self._generated_ids[table_name] = []
        
        processed_data = []
        null_count = 0
        referenced_count = 0
        
        for row in data:
            processed_row = row.copy()
            
            # 获取当前记录的主键值
            pk_values = [row.get(pk) for pk in pk_columns]
            
            # 决定自引用字段的值
            if self._should_be_null():
                # 设置为 NULL
                for col in constrained_cols:
                    processed_row[col] = None
                null_count += 1
            elif self._generated_ids[table_name]:
                # 引用已存在的记录
                ref_values = self._select_reference(
                    self._generated_ids[table_name],
                    pk_values
                )
                for i, col in enumerate(constrained_cols):
                    if i < len(ref_values):
                        processed_row[col] = ref_values[i]
                referenced_count += 1
            else:
                # 没有可引用的记录，设为 NULL
                for col in constrained_cols:
                    processed_row[col] = None
                null_count += 1
            
            processed_data.append(processed_row)
            
            # 将当前记录的主键添加到已生成列表
            self._generated_ids[table_name].append(pk_values)
        
        return SelfReferenceResult(
            data=processed_data,
            null_count=null_count,
            referenced_count=referenced_count,
            total_records=len(processed_data)
        )
    
    def _should_be_null(self) -> bool:
        """决定自引用字段是否应为 NULL
        
        Returns:
            是否应为 NULL
        """
        return self._random.random() < self.config.null_ratio
    
    def _select_reference(
        self, 
        available_refs: List[List[Any]], 
        current_pk: List[Any]
    ) -> List[Any]:
        """选择一个引用值
        
        Args:
            available_refs: 可用的引用值列表
            current_pk: 当前记录的主键值
            
        Returns:
            选中的引用值
        """
        # 过滤掉当前记录本身（避免自引用到自身）
        valid_refs = [
            ref for ref in available_refs 
            if ref != current_pk
        ]
        
        if not valid_refs:
            # 如果没有有效的引用（只有当前记录），返回 None
            return [None] * len(current_pk)
        
        return self._random.choice(valid_refs)
    
    def generate_in_batches(
        self,
        table_schema: TableSchema,
        foreign_key: ForeignKeyInfo,
        total_count: int,
        data_generator: callable
    ) -> List[Dict[str, Any]]:
        """分批生成数据
        
        分批生成数据以正确处理自引用关系。
        
        Args:
            table_schema: 表结构信息
            foreign_key: 自引用外键信息
            total_count: 总记录数
            data_generator: 数据生成函数，接受 count 参数
            
        Returns:
            生成的数据列表
        """
        all_data = []
        remaining = total_count
        batch_num = 0
        
        # 获取自引用字段
        constrained_cols = foreign_key.constrained_columns
        pk_columns = table_schema.primary_keys
        
        while remaining > 0:
            batch_size = min(self.config.batch_size, remaining)
            
            # 生成批次数据
            batch_data = data_generator(batch_size)
            
            # 处理自引用
            if batch_num == 0:
                # 第一批：所有自引用字段设为 NULL
                for row in batch_data:
                    for col in constrained_cols:
                        row[col] = None
            else:
                # 后续批次：引用已有记录
                result = self.handle_self_reference(
                    table_schema, batch_data, foreign_key
                )
                batch_data = result.data
            
            all_data.extend(batch_data)
            
            # 更新已生成的 ID
            for row in batch_data:
                pk_values = [row.get(pk) for pk in pk_columns]
                if table_schema.table_name not in self._generated_ids:
                    self._generated_ids[table_schema.table_name] = []
                self._generated_ids[table_schema.table_name].append(pk_values)
            
            remaining -= batch_size
            batch_num += 1
        
        return all_data
    
    def handle_multiple_self_references(
        self,
        table_schema: TableSchema,
        data: List[Dict[str, Any]],
        foreign_keys: List[ForeignKeyInfo]
    ) -> SelfReferenceResult:
        """处理多个自引用外键
        
        当一个表有多个自引用外键时，需要分别处理每个外键。
        
        Args:
            table_schema: 表结构信息
            data: 待处理的数据列表
            foreign_keys: 自引用外键列表
            
        Returns:
            SelfReferenceResult 对象
        """
        if not foreign_keys:
            return SelfReferenceResult(data=data, total_records=len(data))
        
        processed_data = data.copy()
        total_null = 0
        total_ref = 0
        
        for fk in foreign_keys:
            result = self.handle_self_reference(
                table_schema, processed_data, fk
            )
            processed_data = result.data
            total_null += result.null_count
            total_ref += result.referenced_count
        
        return SelfReferenceResult(
            data=processed_data,
            null_count=total_null,
            referenced_count=total_ref,
            total_records=len(processed_data)
        )
    
    def update_self_references(
        self,
        table_schema: TableSchema,
        data: List[Dict[str, Any]],
        foreign_key: ForeignKeyInfo
    ) -> List[Dict[str, Any]]:
        """更新自引用值
        
        在所有数据生成完成后，更新之前设为 NULL 的自引用字段。
        这允许创建更复杂的自引用结构。
        
        Args:
            table_schema: 表结构信息
            data: 已生成的数据列表
            foreign_key: 自引用外键信息
            
        Returns:
            更新后的数据列表
        """
        if not data:
            return data
        
        constrained_cols = foreign_key.constrained_columns
        pk_columns = table_schema.primary_keys
        
        # 收集所有主键值
        all_pk_values = [
            [row.get(pk) for pk in pk_columns]
            for row in data
        ]
        
        updated_data = []
        
        for i, row in enumerate(data):
            updated_row = row.copy()
            
            # 检查自引用字段是否为 NULL
            all_null = all(
                row.get(col) is None 
                for col in constrained_cols
            )
            
            if all_null and self._random.random() > self.config.null_ratio:
                # 随机选择一个引用（排除自身）
                available_refs = [
                    pk for j, pk in enumerate(all_pk_values) 
                    if j != i
                ]
                
                if available_refs:
                    ref = self._random.choice(available_refs)
                    for j, col in enumerate(constrained_cols):
                        if j < len(ref):
                            updated_row[col] = ref[j]
            
            updated_data.append(updated_row)
        
        return updated_data
    
    def get_self_reference_stats(
        self,
        data: List[Dict[str, Any]],
        foreign_key: ForeignKeyInfo
    ) -> Dict[str, Any]:
        """获取自引用统计信息
        
        Args:
            data: 数据列表
            foreign_key: 自引用外键信息
            
        Returns:
            统计信息字典
        """
        if not data:
            return {
                'total': 0,
                'null_count': 0,
                'referenced_count': 0,
                'null_ratio': 0.0
            }
        
        constrained_cols = foreign_key.constrained_columns
        null_count = 0
        referenced_count = 0
        
        for row in data:
            if all(row.get(col) is None for col in constrained_cols):
                null_count += 1
            else:
                referenced_count += 1
        
        return {
            'total': len(data),
            'null_count': null_count,
            'referenced_count': referenced_count,
            'null_ratio': null_count / len(data) if data else 0.0
        }
    
    def clear_generated_ids(self, table_name: Optional[str] = None) -> None:
        """清除已生成的 ID 缓存
        
        Args:
            table_name: 表名，如果为 None 则清除所有
        """
        if table_name:
            if table_name in self._generated_ids:
                del self._generated_ids[table_name]
        else:
            self._generated_ids.clear()
    
    def set_seed(self, seed: int) -> None:
        """设置随机种子
        
        Args:
            seed: 随机种子
        """
        self._random = random.Random(seed)
    
    def set_config(self, config: SelfReferenceConfig) -> None:
        """设置处理配置
        
        Args:
            config: 新的配置
        """
        self.config = config
