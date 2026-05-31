# -*- coding: utf-8 -*-
"""关联关系管理器

整合依赖分析、拓扑排序、外键填充和自引用处理功能。
提供统一的接口来处理复杂的表间关联关系。
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging

from ..schema_parser.models import TableSchema, ForeignKeyInfo
from .dependency_analyzer import DependencyAnalyzer, DependencyNode, CycleInfo
from .topological_sorter import TopologicalSorter, SortResult
from .foreign_key_handler import ForeignKeyHandler
from .self_reference_handler import (
    SelfReferenceHandler, 
    SelfReferenceConfig,
    SelfReferenceResult
)


logger = logging.getLogger(__name__)


@dataclass
class GenerationPlan:
    """数据生成计划
    
    Attributes:
        ordered_tables: 按顺序生成的表列表
        levels: 按层级分组的表列表
        cycles: 检测到的循环依赖
        self_reference_tables: 有自引用的表列表
        table_details: 每个表的详细计划信息
    """
    ordered_tables: List[str] = field(default_factory=list)
    levels: List[List[str]] = field(default_factory=list)
    cycles: List[CycleInfo] = field(default_factory=list)
    self_reference_tables: List[str] = field(default_factory=list)
    table_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ProcessResult:
    """数据处理结果
    
    Attributes:
        table_name: 表名
        data: 处理后的数据
        foreign_keys_filled: 填充的外键数量
        self_references_handled: 处理的自引用数量
        success: 是否成功
        errors: 错误信息列表
    """
    table_name: str
    data: List[Dict[str, Any]] = field(default_factory=list)
    foreign_keys_filled: int = 0
    self_references_handled: int = 0
    success: bool = True
    errors: List[str] = field(default_factory=list)


class RelationManager:
    """关联关系管理器
    
    整合所有关联关系处理功能，提供统一的接口。
    
    Example:
        >>> manager = RelationManager()
        >>> plan = manager.plan_generation_order(tables_schemas)
        >>> for table_name in plan.ordered_tables:
        ...     result = manager.process_table(table_name, data)
    """
    
    def __init__(
        self,
        self_ref_config: Optional[SelfReferenceConfig] = None,
        seed: Optional[int] = None
    ):
        """初始化关联关系管理器
        
        Args:
            self_ref_config: 自引用处理配置
            seed: 随机种子
        """
        self._dependency_analyzer = DependencyAnalyzer()
        self._topological_sorter = TopologicalSorter()
        self._foreign_key_handler = ForeignKeyHandler(seed=seed)
        self._self_reference_handler = SelfReferenceHandler(
            config=self_ref_config,
            seed=seed
        )
        
        self._tables_schemas: Dict[str, TableSchema] = {}
        self._generation_plan: Optional[GenerationPlan] = None
        self._processed_tables: Set[str] = set()
    
    def plan_generation_order(
        self, 
        tables_schemas: Dict[str, TableSchema]
    ) -> GenerationPlan:
        """规划数据生成顺序
        
        分析表之间的依赖关系，确定正确的生成顺序。
        
        Args:
            tables_schemas: 表名到表结构的映射字典
            
        Returns:
            GenerationPlan 对象
        """
        self._tables_schemas = tables_schemas
        self._processed_tables.clear()
        
        # 分析依赖关系
        dependency_graph = self._dependency_analyzer.analyze(tables_schemas)
        
        # 检测循环依赖
        cycles = self._dependency_analyzer.detect_cycles()
        
        # 拓扑排序
        sort_result = self._topological_sorter.sort(tables_schemas)
        
        # 获取有自引用的表
        self_ref_tables = self._dependency_analyzer.get_tables_with_self_reference()
        
        # 构建详细计划
        table_details = {}
        for table_name in sort_result.ordered_tables:
            node = dependency_graph.get(table_name)
            table_schema = tables_schemas.get(table_name)
            
            table_details[table_name] = {
                'level': self._get_table_level(table_name, sort_result.levels),
                'dependencies': sorted(list(node.depends_on)) if node else [],
                'dependents': sorted(list(node.depended_by)) if node else [],
                'foreign_keys': table_schema.foreign_keys if table_schema else [],
                'has_self_reference': table_name in self_ref_tables,
                'self_references': self._dependency_analyzer.get_self_references(table_name)
            }
        
        self._generation_plan = GenerationPlan(
            ordered_tables=sort_result.ordered_tables,
            levels=sort_result.levels,
            cycles=cycles,
            self_reference_tables=self_ref_tables,
            table_details=table_details
        )
        
        return self._generation_plan
    
    def _get_table_level(self, table_name: str, levels: List[List[str]]) -> int:
        """获取表所在的层级
        
        Args:
            table_name: 表名
            levels: 层级列表
            
        Returns:
            层级索引
        """
        for i, level in enumerate(levels):
            if table_name in level:
                return i
        return -1
    
    def process_table(
        self, 
        table_name: str, 
        data: List[Dict[str, Any]],
        fill_foreign_keys: bool = True,
        handle_self_references: bool = True
    ) -> ProcessResult:
        """处理表数据
        
        填充外键值，处理自引用关系。
        
        Args:
            table_name: 表名
            data: 待处理的数据列表
            fill_foreign_keys: 是否填充外键
            handle_self_references: 是否处理自引用
            
        Returns:
            ProcessResult 对象
        """
        result = ProcessResult(table_name=table_name, data=data)
        
        if table_name not in self._tables_schemas:
            result.success = False
            result.errors.append(f"表 '{table_name}' 的结构信息不存在")
            return result
        
        table_schema = self._tables_schemas[table_name]
        processed_data = data.copy()
        
        # 填充外键（非自引用）
        if fill_foreign_keys and table_schema.foreign_keys:
            non_self_fks = [
                fk for fk in table_schema.foreign_keys
                if fk.referred_table != table_name
            ]
            
            if non_self_fks:
                processed_data = self._foreign_key_handler.fill_foreign_keys(
                    processed_data, 
                    non_self_fks,
                    table_schema
                )
                result.foreign_keys_filled = len(non_self_fks)
        
        # 处理自引用
        if handle_self_references:
            self_refs = self._dependency_analyzer.get_self_references(table_name)
            
            if self_refs:
                try:
                    if len(self_refs) == 1:
                        ref_result = self._self_reference_handler.handle_self_reference(
                            table_schema, 
                            processed_data, 
                            self_refs[0]
                        )
                    else:
                        ref_result = self._self_reference_handler.handle_multiple_self_references(
                            table_schema,
                            processed_data,
                            self_refs
                        )
                    
                    processed_data = ref_result.data
                    result.self_references_handled = len(self_refs)
                    
                except Exception as e:
                    result.errors.append(f"处理自引用时出错: {str(e)}")
        
        result.data = processed_data
        result.success = len(result.errors) == 0
        
        # 存储处理后的数据
        self._foreign_key_handler.store_generated_data(
            table_name, 
            processed_data,
            table_schema.primary_keys
        )
        
        self._processed_tables.add(table_name)
        
        return result
    
    def store_data(
        self, 
        table_name: str, 
        data: List[Dict[str, Any]],
        primary_keys: Optional[List[str]] = None
    ) -> None:
        """存储已生成的数据
        
        Args:
            table_name: 表名
            data: 数据列表
            primary_keys: 主键字段列表
        """
        self._foreign_key_handler.store_generated_data(
            table_name, data, primary_keys
        )
        self._processed_tables.add(table_name)
    
    def get_available_references(
        self, 
        table_name: str, 
        column_name: str
    ) -> List[Any]:
        """获取可用的引用值
        
        Args:
            table_name: 表名
            column_name: 字段名
            
        Returns:
            可用的引用值列表
        """
        return self._foreign_key_handler.get_referenced_values(table_name, column_name)
    
    def get_generation_plan(self) -> Optional[GenerationPlan]:
        """获取当前的生成计划
        
        Returns:
            GenerationPlan 对象，如果未规划则返回 None
        """
        return self._generation_plan
    
    def get_table_dependencies(self, table_name: str) -> Optional[DependencyNode]:
        """获取表的依赖关系
        
        Args:
            table_name: 表名
            
        Returns:
            DependencyNode 对象
        """
        return self._dependency_analyzer.get_table_dependencies(table_name)
    
    def get_tables_by_level(self) -> List[List[str]]:
        """按层级获取表列表
        
        Returns:
            层级表列表
        """
        if self._generation_plan:
            return self._generation_plan.levels
        return []
    
    def is_table_processed(self, table_name: str) -> bool:
        """检查表是否已处理
        
        Args:
            table_name: 表名
            
        Returns:
            是否已处理
        """
        return table_name in self._processed_tables
    
    def can_process_table(self, table_name: str) -> Tuple[bool, List[str]]:
        """检查表是否可以处理
        
        检查所有依赖的表是否已处理。
        
        Args:
            table_name: 表名
            
        Returns:
            元组：(是否可以处理, 未处理的依赖表列表)
        """
        node = self._dependency_analyzer.get_table_dependencies(table_name)
        
        if not node:
            return True, []
        
        # 排除自引用
        external_deps = node.depends_on - {table_name}
        unprocessed = [
            dep for dep in external_deps 
            if dep not in self._processed_tables
        ]
        
        return len(unprocessed) == 0, unprocessed
    
    def get_processing_status(self) -> Dict[str, Any]:
        """获取处理状态
        
        Returns:
            状态信息字典
        """
        if not self._generation_plan:
            return {
                'planned': False,
                'total_tables': 0,
                'processed_tables': 0,
                'pending_tables': [],
                'progress': 0.0
            }
        
        total = len(self._generation_plan.ordered_tables)
        processed = len(self._processed_tables)
        pending = [
            t for t in self._generation_plan.ordered_tables 
            if t not in self._processed_tables
        ]
        
        return {
            'planned': True,
            'total_tables': total,
            'processed_tables': processed,
            'pending_tables': pending,
            'progress': processed / total if total > 0 else 0.0,
            'has_cycles': bool(self._generation_plan.cycles),
            'self_reference_tables': self._generation_plan.self_reference_tables
        }
    
    def validate_data_integrity(
        self, 
        table_name: str, 
        data: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """验证数据完整性
        
        检查数据中的外键值是否有效。
        
        Args:
            table_name: 表名
            data: 数据列表
            
        Returns:
            元组：(是否有效, 错误信息列表)
        """
        if table_name not in self._tables_schemas:
            return False, [f"表 '{table_name}' 的结构信息不存在"]
        
        table_schema = self._tables_schemas[table_name]
        errors = []
        
        for fk in table_schema.foreign_keys:
            # 跳过自引用
            if fk.referred_table == table_name:
                continue
            
            valid, fk_errors = self._foreign_key_handler.validate_foreign_key_values(
                data, fk
            )
            errors.extend(fk_errors)
        
        return len(errors) == 0, errors
    
    def get_foreign_key_status(
        self, 
        table_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """获取表的外键状态
        
        Args:
            table_name: 表名
            
        Returns:
            外键状态字典
        """
        if table_name not in self._tables_schemas:
            return {}
        
        table_schema = self._tables_schemas[table_name]
        status = {}
        
        for fk in table_schema.foreign_keys:
            status[fk.name] = self._foreign_key_handler.get_foreign_key_status(fk)
        
        return status
    
    def clear_processed_data(self, table_name: Optional[str] = None) -> None:
        """清除已处理的数据
        
        Args:
            table_name: 表名，如果为 None 则清除所有
        """
        if table_name:
            self._foreign_key_handler.clear_table_data(table_name)
            self._self_reference_handler.clear_generated_ids(table_name)
            self._processed_tables.discard(table_name)
        else:
            self._foreign_key_handler.clear_all_data()
            self._self_reference_handler.clear_generated_ids()
            self._processed_tables.clear()
    
    def reset(self) -> None:
        """重置管理器状态"""
        self._tables_schemas.clear()
        self._generation_plan = None
        self._processed_tables.clear()
        self._foreign_key_handler.clear_all_data()
        self._self_reference_handler.clear_generated_ids()
    
    def set_seed(self, seed: int) -> None:
        """设置随机种子
        
        Args:
            seed: 随机种子
        """
        self._foreign_key_handler.set_seed(seed)
        self._self_reference_handler.set_seed(seed)
    
    def get_dependency_summary(self) -> Dict[str, Dict]:
        """获取依赖关系摘要
        
        Returns:
            依赖关系摘要字典
        """
        return self._dependency_analyzer.get_dependency_summary()
    
    def get_generation_report(self) -> Dict[str, Any]:
        """获取生成报告
        
        Returns:
            生成报告字典
        """
        status = self.get_processing_status()
        
        report = {
            'status': status,
            'tables': {}
        }
        
        for table_name in self._processed_tables:
            table_schema = self._tables_schemas.get(table_name)
            data_count = self._foreign_key_handler.get_generated_count(table_name)
            
            report['tables'][table_name] = {
                'processed': True,
                'records_generated': data_count,
                'foreign_keys_count': len(table_schema.foreign_keys) if table_schema else 0,
                'has_self_reference': table_name in (self._generation_plan.self_reference_tables if self._generation_plan else [])
            }
        
        return report
