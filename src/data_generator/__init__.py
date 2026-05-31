# -*- coding: utf-8 -*-
"""测试数据生成模块

负责根据表结构生成测试数据，支持:
- 基于字段类型的数据生成
- 自定义数据规则
- Faker库集成
- 批量数据生成
- 多种生成策略（正常值、边界值、异常值）
"""

from .base import DataGenerator
from .generators import (
    IntegerGenerator,
    FloatGenerator,
    StringGenerator,
    DateTimeGenerator,
    DateGenerator,
    BooleanGenerator,
    EnumGenerator,
    JSONGenerator,
    UUIDGenerator,
    get_generator_for_type,
    GENERATOR_REGISTRY
)
from .strategies import (
    StrategyType,
    GenerationStrategy,
    NormalStrategy,
    BoundaryStrategy,
    AbnormalStrategy,
    MixedStrategy,
    CustomStrategy,
    StrategyFactory
)
from .engine import (
    DataEngine,
    DataEngineBuilder,
    ColumnRule,
    GenerationResult
)

__all__ = [
    # 基类
    'DataGenerator',
    
    # 生成器
    'IntegerGenerator',
    'FloatGenerator',
    'StringGenerator',
    'DateTimeGenerator',
    'DateGenerator',
    'BooleanGenerator',
    'EnumGenerator',
    'JSONGenerator',
    'UUIDGenerator',
    'get_generator_for_type',
    'GENERATOR_REGISTRY',
    
    # 策略
    'StrategyType',
    'GenerationStrategy',
    'NormalStrategy',
    'BoundaryStrategy',
    'AbnormalStrategy',
    'MixedStrategy',
    'CustomStrategy',
    'StrategyFactory',
    
    # 引擎
    'DataEngine',
    'DataEngineBuilder',
    'ColumnRule',
    'GenerationResult',
]
