# -*- coding: utf-8 -*-
"""依赖关系分析器

分析表之间的依赖关系，构建依赖图，检测循环依赖。
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from ..schema_parser.models import TableSchema, ForeignKeyInfo


@dataclass
class DependencyNode:
    """依赖关系节点
    
    表示一个表及其依赖关系。
    
    Attributes:
        table_name: 表名
        depends_on: 该表依赖的表集合
        depended_by: 依赖该表的表集合
        foreign_keys: 该表的外键列表
        self_references: 自引用外键列表
    """
    table_name: str
    depends_on: Set[str] = field(default_factory=set)
    depended_by: Set[str] = field(default_factory=set)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    self_references: List[ForeignKeyInfo] = field(default_factory=list)


@dataclass
class CycleInfo:
    """循环依赖信息
    
    Attributes:
        tables: 参与循环的表列表
        foreign_keys: 参与循环的外键列表
    """
    tables: List[str]
    foreign_keys: List[ForeignKeyInfo]


class DependencyAnalyzer:
    """依赖关系分析器
    
    分析数据库表之间的依赖关系，构建依赖图，检测循环依赖。
    
    Example:
        >>> analyzer = DependencyAnalyzer()
        >>> analyzer.analyze(tables_schemas)
        >>> graph = analyzer.get_dependency_graph()
        >>> cycles = analyzer.detect_cycles()
    """
    
    def __init__(self):
        """初始化依赖关系分析器"""
        self._dependency_graph: Dict[str, DependencyNode] = {}
        self._all_tables: Set[str] = set()
        self._cycles: List[CycleInfo] = []
        self._analyzed: bool = False
    
    def analyze(self, tables_schemas: Dict[str, TableSchema]) -> Dict[str, DependencyNode]:
        """分析所有表的依赖关系
        
        Args:
            tables_schemas: 表名到表结构的映射字典
            
        Returns:
            依赖关系图字典
        """
        # 重置状态
        self._dependency_graph.clear()
        self._all_tables.clear()
        self._cycles.clear()
        
        # 收集所有表名
        self._all_tables = set(tables_schemas.keys())
        
        # 初始化所有节点
        for table_name in self._all_tables:
            self._dependency_graph[table_name] = DependencyNode(table_name=table_name)
        
        # 分析每个表的外键关系
        for table_name, table_schema in tables_schemas.items():
            node = self._dependency_graph[table_name]
            node.foreign_keys = table_schema.foreign_keys
            
            for fk in table_schema.foreign_keys:
                # 检查是否是自引用
                if fk.referred_table == table_name:
                    node.self_references.append(fk)
                else:
                    # 添加依赖关系
                    node.depends_on.add(fk.referred_table)
                    
                    # 更新被依赖关系
                    if fk.referred_table in self._dependency_graph:
                        self._dependency_graph[fk.referred_table].depended_by.add(table_name)
        
        self._analyzed = True
        return self._dependency_graph
    
    def get_dependency_graph(self) -> Dict[str, DependencyNode]:
        """获取依赖图
        
        Returns:
            依赖关系图字典
            
        Raises:
            RuntimeError: 如果尚未分析表结构
        """
        if not self._analyzed:
            raise RuntimeError("请先调用 analyze() 方法分析表结构")
        return self._dependency_graph
    
    def detect_cycles(self) -> List[CycleInfo]:
        """检测循环依赖
        
        使用深度优先搜索(DFS)检测图中的所有循环。
        
        Returns:
            循环依赖信息列表
        """
        if not self._analyzed:
            raise RuntimeError("请先调用 analyze() 方法分析表结构")
        
        self._cycles.clear()
        
        # 用于跟踪访问状态的集合
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        
        def dfs(table_name: str) -> bool:
            """深度优先搜索检测环"""
            visited.add(table_name)
            rec_stack.add(table_name)
            path.append(table_name)
            
            node = self._dependency_graph.get(table_name)
            if node:
                for dep_table in node.depends_on:
                    if dep_table not in visited:
                        if dfs(dep_table):
                            return True
                    elif dep_table in rec_stack:
                        # 找到循环
                        cycle_start_idx = path.index(dep_table)
                        cycle_tables = path[cycle_start_idx:]
                        
                        # 收集循环中的外键
                        cycle_fks = self._collect_cycle_foreign_keys(cycle_tables)
                        
                        self._cycles.append(CycleInfo(
                            tables=cycle_tables,
                            foreign_keys=cycle_fks
                        ))
                        return True
            
            path.pop()
            rec_stack.remove(table_name)
            return False
        
        # 从每个未访问的节点开始DFS
        for table_name in self._all_tables:
            if table_name not in visited:
                dfs(table_name)
        
        return self._cycles
    
    def _collect_cycle_foreign_keys(self, cycle_tables: List[str]) -> List[ForeignKeyInfo]:
        """收集循环中的外键
        
        Args:
            cycle_tables: 循环中的表列表
            
        Returns:
            循环中的外键列表
        """
        cycle_fks = []
        cycle_set = set(cycle_tables)
        
        for i, table_name in enumerate(cycle_tables):
            next_table = cycle_tables[(i + 1) % len(cycle_tables)]
            node = self._dependency_graph.get(table_name)
            
            if node:
                for fk in node.foreign_keys:
                    if fk.referred_table == next_table:
                        cycle_fks.append(fk)
                        break
        
        return cycle_fks
    
    def get_table_dependencies(self, table_name: str) -> Optional[DependencyNode]:
        """获取指定表的依赖关系
        
        Args:
            table_name: 表名
            
        Returns:
            依赖节点，如果表不存在则返回 None
        """
        return self._dependency_graph.get(table_name)
    
    def get_generation_order(self) -> List[str]:
        """获取表的生成顺序（拓扑排序）
        
        返回按照依赖关系排序的表列表，依赖的表排在前面。
        
        Returns:
            排序后的表名列表
        """
        if not self._analyzed:
            raise RuntimeError("请先调用 analyze() 方法分析表结构")
        
        # 使用 Kahn 算法进行拓扑排序
        in_degree: Dict[str, int] = {}
        queue: List[str] = []
        result: List[str] = []
        
        # 计算入度
        for table_name in self._all_tables:
            in_degree[table_name] = len(self._dependency_graph[table_name].depends_on)
            if in_degree[table_name] == 0:
                queue.append(table_name)
        
        # 处理队列
        while queue:
            # 按名称排序以保证确定性
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            
            node = self._dependency_graph[current]
            for dep_table in node.depended_by:
                in_degree[dep_table] -= 1
                if in_degree[dep_table] == 0:
                    queue.append(dep_table)
        
        return result
    
    def get_tables_by_level(self) -> List[List[str]]:
        """按依赖层级获取表
        
        返回按层级分组的表列表，同一层级的表可以并行生成。
        
        Returns:
            层级表列表，第一层是没有依赖的表
        """
        if not self._analyzed:
            raise RuntimeError("请先调用 analyze() 方法分析表结构")
        
        levels: List[List[str]] = []
        remaining = set(self._all_tables)
        processed: Set[str] = set()
        
        while remaining:
            # 找出当前层级（所有依赖都已处理的表）
            current_level = []
            for table_name in list(remaining):
                node = self._dependency_graph[table_name]
                # 检查所有依赖是否已处理（排除自引用）
                deps = node.depends_on - {table_name}
                if deps.issubset(processed):
                    current_level.append(table_name)
            
            if not current_level:
                # 存在循环依赖，将剩余表加入最后一层
                if remaining:
                    levels.append(sorted(list(remaining)))
                break
            
            current_level.sort()
            levels.append(current_level)
            processed.update(current_level)
            remaining -= set(current_level)
        
        return levels
    
    def has_self_reference(self, table_name: str) -> bool:
        """检查表是否有自引用
        
        Args:
            table_name: 表名
            
        Returns:
            是否有自引用
        """
        node = self._dependency_graph.get(table_name)
        return bool(node and node.self_references)
    
    def get_self_references(self, table_name: str) -> List[ForeignKeyInfo]:
        """获取表的自引用外键
        
        Args:
            table_name: 表名
            
        Returns:
            自引用外键列表
        """
        node = self._dependency_graph.get(table_name)
        return node.self_references if node else []
    
    def get_tables_with_self_reference(self) -> List[str]:
        """获取所有有自引用的表
        
        Returns:
            有自引用的表名列表
        """
        return [
            table_name for table_name, node in self._dependency_graph.items()
            if node.self_references
        ]
    
    def get_dependency_summary(self) -> Dict[str, Dict]:
        """获取依赖关系摘要
        
        Returns:
            依赖关系摘要字典
        """
        if not self._analyzed:
            raise RuntimeError("请先调用 analyze() 方法分析表结构")
        
        summary = {}
        for table_name, node in self._dependency_graph.items():
            summary[table_name] = {
                'depends_on': sorted(list(node.depends_on)),
                'depended_by': sorted(list(node.depended_by)),
                'foreign_keys_count': len(node.foreign_keys),
                'has_self_reference': bool(node.self_references),
                'self_references_count': len(node.self_references)
            }
        
        return summary
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """验证依赖关系完整性
        
        检查所有外键引用的表是否都存在。
        
        Returns:
            元组：(是否有效, 错误信息列表)
        """
        if not self._analyzed:
            raise RuntimeError("请先调用 analyze() 方法分析表结构")
        
        errors = []
        
        for table_name, node in self._dependency_graph.items():
            for dep_table in node.depends_on:
                if dep_table not in self._all_tables:
                    errors.append(
                        f"表 '{table_name}' 引用了不存在的表 '{dep_table}'"
                    )
        
        return len(errors) == 0, errors
