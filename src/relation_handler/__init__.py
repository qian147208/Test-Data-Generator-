# -*- coding: utf-8 -*-
"""关联关系处理模块

负责处理表之间的关联关系，包括:
- 依赖关系分析
- 拓扑排序
- 外键关系维护
- 自引用关联处理
- 数据一致性保证
"""

from .dependency_analyzer import (
    DependencyAnalyzer,
    DependencyNode,
    CycleInfo
)
from .topological_sorter import (
    TopologicalSorter,
    SortResult
)
from .foreign_key_handler import ForeignKeyHandler
from .self_reference_handler import (
    SelfReferenceHandler,
    SelfReferenceConfig,
    SelfReferenceResult
)
from .relation_manager import (
    RelationManager,
    GenerationPlan,
    ProcessResult
)

__all__ = [
    # 依赖分析
    'DependencyAnalyzer',
    'DependencyNode',
    'CycleInfo',
    
    # 拓扑排序
    'TopologicalSorter',
    'SortResult',
    
    # 外键处理
    'ForeignKeyHandler',
    
    # 自引用处理
    'SelfReferenceHandler',
    'SelfReferenceConfig',
    'SelfReferenceResult',
    
    # 关联管理
    'RelationManager',
    'GenerationPlan',
    'ProcessResult'
]
