# -*- coding: utf-8 -*-
"""拓扑排序模块

对表进行拓扑排序，确定正确的数据生成顺序。
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque

from ..schema_parser.models import TableSchema, ForeignKeyInfo


@dataclass
class SortResult:
    """排序结果
    
    Attributes:
        ordered_tables: 排序后的表列表
        cycle_tables: 参与循环的表列表
        cycle_detected: 是否检测到循环依赖
        levels: 按层级分组的表列表
    """
    ordered_tables: List[str] = field(default_factory=list)
    cycle_tables: List[str] = field(default_factory=list)
    cycle_detected: bool = False
    levels: List[List[str]] = field(default_factory=list)


class TopologicalSorter:
    """拓扑排序器
    
    对数据库表进行拓扑排序，确定正确的数据生成顺序。
    支持处理循环依赖情况。
    
    Example:
        >>> sorter = TopologicalSorter()
        >>> result = sorter.sort(tables, dependencies)
        >>> print(result.ordered_tables)
    """
    
    def __init__(self):
        """初始化拓扑排序器"""
        self._graph: Dict[str, Set[str]] = {}
        self._reverse_graph: Dict[str, Set[str]] = {}
        self._all_tables: Set[str] = set()
    
    def sort(
        self, 
        tables: Dict[str, TableSchema],
        dependencies: Optional[Dict[str, Set[str]]] = None
    ) -> SortResult:
        """对表进行拓扑排序
        
        Args:
            tables: 表名到表结构的映射字典
            dependencies: 可选的依赖关系字典，如果未提供则从表结构中提取
            
        Returns:
            SortResult 对象
        """
        # 构建依赖图
        self._build_graph(tables, dependencies)
        
        # 检测循环依赖
        cycle_tables = self._detect_cycle()
        
        # 执行拓扑排序
        if cycle_tables:
            # 存在循环依赖，使用特殊处理
            ordered_tables = self._sort_with_cycle(cycle_tables)
        else:
            ordered_tables = self._sort_normal()
        
        # 计算层级
        levels = self._calculate_levels()
        
        return SortResult(
            ordered_tables=ordered_tables,
            cycle_tables=cycle_tables,
            cycle_detected=bool(cycle_tables),
            levels=levels
        )
    
    def _build_graph(
        self, 
        tables: Dict[str, TableSchema],
        dependencies: Optional[Dict[str, Set[str]]] = None
    ) -> None:
        """构建依赖图
        
        Args:
            tables: 表名到表结构的映射字典
            dependencies: 可选的依赖关系字典
        """
        self._graph.clear()
        self._reverse_graph.clear()
        self._all_tables = set(tables.keys())
        
        # 初始化图
        for table_name in self._all_tables:
            self._graph[table_name] = set()
            self._reverse_graph[table_name] = set()
        
        # 构建边
        if dependencies:
            for table_name, deps in dependencies.items():
                for dep_table in deps:
                    if dep_table in self._all_tables and dep_table != table_name:
                        self._graph[table_name].add(dep_table)
                        self._reverse_graph[dep_table].add(table_name)
        else:
            # 从表结构中提取依赖
            for table_name, table_schema in tables.items():
                for fk in table_schema.foreign_keys:
                    if fk.referred_table in self._all_tables and fk.referred_table != table_name:
                        self._graph[table_name].add(fk.referred_table)
                        self._reverse_graph[fk.referred_table].add(table_name)
    
    def _detect_cycle(self) -> List[str]:
        """检测循环依赖
        
        使用深度优先搜索检测图中的循环。
        
        Returns:
            参与循环的表列表，如果没有循环则返回空列表
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []
        cycle_tables: List[str] = []
        
        def dfs(node: str) -> bool:
            """深度优先搜索"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self._graph[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    nonlocal cycle_tables
                    cycle_tables = path[cycle_start:]
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for table in self._all_tables:
            if table not in visited:
                if dfs(table):
                    break
        
        return cycle_tables
    
    def _sort_normal(self) -> List[str]:
        """正常拓扑排序（无循环）
        
        使用 Kahn 算法进行拓扑排序。
        
        Returns:
            排序后的表列表
        """
        # 计算入度
        in_degree: Dict[str, int] = {}
        for table in self._all_tables:
            in_degree[table] = len(self._graph[table])
        
        # 找出入度为 0 的节点
        queue = deque([table for table in self._all_tables if in_degree[table] == 0])
        result: List[str] = []
        
        while queue:
            # 排序以保证确定性
            current_list = sorted(list(queue))
            queue.clear()
            
            for current in current_list:
                result.append(current)
                
                for neighbor in self._reverse_graph[current]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result
    
    def _sort_with_cycle(self, cycle_tables: List[str]) -> List[str]:
        """处理循环依赖的排序
        
        将循环依赖的表作为一个组处理，确定最佳生成顺序。
        
        Args:
            cycle_tables: 参与循环的表列表
            
        Returns:
            排序后的表列表
        """
        cycle_set = set(cycle_tables)
        
        # 计算入度（忽略循环内部的边）
        in_degree: Dict[str, int] = {}
        for table in self._all_tables:
            # 计算来自循环外部的依赖
            external_deps = self._graph[table] - cycle_set
            in_degree[table] = len(external_deps)
        
        # 对于循环内的表，将它们作为一个整体处理
        # 先处理循环外的表
        result: List[str] = []
        queue = deque([
            table for table in self._all_tables 
            if table not in cycle_set and in_degree[table] == 0
        ])
        
        while queue:
            current_list = sorted(list(queue))
            queue.clear()
            
            for current in current_list:
                result.append(current)
                
                for neighbor in self._reverse_graph[current]:
                    if neighbor not in cycle_set:
                        in_degree[neighbor] -= 1
                        if in_degree[neighbor] == 0:
                            queue.append(neighbor)
        
        # 添加循环中的表（按特定顺序）
        # 对于循环依赖，我们需要确定一个合理的顺序
        # 这里使用循环表的拓扑顺序
        cycle_order = self._order_cycle_tables(cycle_tables)
        result.extend(cycle_order)
        
        # 添加依赖循环表的表
        remaining = self._all_tables - set(result)
        if remaining:
            remaining_queue = deque([
                table for table in remaining 
                if all(dep in result for dep in self._graph[table])
            ])
            
            while remaining_queue:
                current_list = sorted(list(remaining_queue))
                remaining_queue.clear()
                
                for current in current_list:
                    result.append(current)
                    
                    for neighbor in self._reverse_graph[current]:
                        if neighbor in remaining:
                            if all(dep in result for dep in self._graph[neighbor]):
                                remaining_queue.append(neighbor)
        
        return result
    
    def _order_cycle_tables(self, cycle_tables: List[str]) -> List[str]:
        """对循环中的表进行排序
        
        确定循环内表的合理生成顺序。
        
        Args:
            cycle_tables: 循环中的表列表
            
        Returns:
            排序后的表列表
        """
        if not cycle_tables:
            return []
        
        # 简单策略：按名称排序
        # 实际应用中可能需要更复杂的策略
        return sorted(cycle_tables)
    
    def _calculate_levels(self) -> List[List[str]]:
        """计算表的层级
        
        将表按依赖层级分组，同一层级的表可以并行生成。
        
        Returns:
            层级表列表
        """
        levels: List[List[str]] = []
        remaining = set(self._all_tables)
        processed: Set[str] = set()
        
        while remaining:
            # 找出当前层级
            current_level = []
            for table in list(remaining):
                deps = self._graph[table] - {table}  # 排除自引用
                if deps.issubset(processed):
                    current_level.append(table)
            
            if not current_level:
                # 可能存在循环依赖，将剩余表加入
                if remaining:
                    levels.append(sorted(list(remaining)))
                break
            
            current_level.sort()
            levels.append(current_level)
            processed.update(current_level)
            remaining -= set(current_level)
        
        return levels
    
    def get_dependencies(self, table_name: str) -> Set[str]:
        """获取表的依赖
        
        Args:
            table_name: 表名
            
        Returns:
            依赖的表集合
        """
        return self._graph.get(table_name, set()).copy()
    
    def get_dependents(self, table_name: str) -> Set[str]:
        """获取依赖该表的其他表
        
        Args:
            table_name: 表名
            
        Returns:
            依赖该表的表集合
        """
        return self._reverse_graph.get(table_name, set()).copy()
    
    def get_in_degree(self, table_name: str) -> int:
        """获取表的入度
        
        Args:
            table_name: 表名
            
        Returns:
            入度值
        """
        return len(self._graph.get(table_name, set()))
    
    def get_out_degree(self, table_name: str) -> int:
        """获取表的出度
        
        Args:
            table_name: 表名
            
        Returns:
            出度值
        """
        return len(self._reverse_graph.get(table_name, set()))
    
    def is_source_table(self, table_name: str) -> bool:
        """判断是否为源表（没有依赖的表）
        
        Args:
            table_name: 表名
            
        Returns:
            是否为源表
        """
        return len(self._graph.get(table_name, set())) == 0
    
    def is_sink_table(self, table_name: str) -> bool:
        """判断是否为汇表（没有其他表依赖的表）
        
        Args:
            table_name: 表名
            
        Returns:
            是否为汇表
        """
        return len(self._reverse_graph.get(table_name, set())) == 0
    
    def get_source_tables(self) -> List[str]:
        """获取所有源表
        
        Returns:
            源表列表
        """
        return sorted([
            table for table in self._all_tables 
            if self.is_source_table(table)
        ])
    
    def get_sink_tables(self) -> List[str]:
        """获取所有汇表
        
        Returns:
            汇表列表
        """
        return sorted([
            table for table in self._all_tables 
            if self.is_sink_table(table)
        ])
    
    def get_generation_plan(self) -> Dict[str, dict]:
        """获取生成计划
        
        为每个表生成详细的生成计划信息。
        
        Returns:
            生成计划字典
        """
        plan = {}
        levels = self._calculate_levels()
        
        for level_idx, level_tables in enumerate(levels):
            for table_name in level_tables:
                plan[table_name] = {
                    'level': level_idx,
                    'dependencies': sorted(list(self._graph.get(table_name, set()))),
                    'dependents': sorted(list(self._reverse_graph.get(table_name, set()))),
                    'can_parallel': len(level_tables) > 1,
                    'parallel_tables': sorted([t for t in level_tables if t != table_name])
                }
        
        return plan
