# -*- coding: utf-8 -*-
"""数据生成策略模块

定义不同的数据生成策略，包括正常值、边界值和异常值生成策略。
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Callable, TYPE_CHECKING
from enum import Enum

from .base import DataGenerator
from .generators import get_generator_for_type

if TYPE_CHECKING:
    from src.schema_parser.models import ColumnInfo


class StrategyType(Enum):
    """策略类型枚举"""
    NORMAL = 'normal'
    BOUNDARY = 'boundary'
    ABNORMAL = 'abnormal'
    MIXED = 'mixed'


class GenerationStrategy(ABC):
    """数据生成策略抽象基类
    
    定义数据生成策略的接口。
    """
    
    @abstractmethod
    def generate(self, generator: DataGenerator, column_info: ColumnInfo, 
                 count: int, **kwargs) -> List[Any]:
        """执行数据生成
        
        Args:
            generator: 数据生成器
            column_info: 字段信息
            count: 生成数量
            **kwargs: 额外参数
            
        Returns:
            生成的数据列表
        """
        pass
    
    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """获取策略类型"""
        pass


class NormalStrategy(GenerationStrategy):
    """正常值生成策略
    
    生成符合字段约束的正常数据，适用于功能测试和常规测试场景。
    """
    
    def __init__(self, null_probability: float = 0.1):
        """初始化正常值策略
        
        Args:
            null_probability: 空值生成概率（仅对可空字段有效）
        """
        self.null_probability = null_probability
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.NORMAL
    
    def generate(self, generator: DataGenerator, column_info: ColumnInfo, 
                 count: int, **kwargs) -> List[Any]:
        """生成正常值数据
        
        Args:
            generator: 数据生成器
            column_info: 字段信息
            count: 生成数量
            **kwargs: 额外参数（可包含 min_value, max_value, pattern 等）
            
        Returns:
            生成的数据列表
        """
        # 提取可能的额外参数
        extra_params = {}
        
        # 数值类型参数
        if 'min_value' in kwargs:
            extra_params['min_value'] = kwargs['min_value']
        if 'max_value' in kwargs:
            extra_params['max_value'] = kwargs['max_value']
        if 'precision' in kwargs:
            extra_params['precision'] = kwargs['precision']
        if 'scale' in kwargs:
            extra_params['scale'] = kwargs['scale']
        
        # 字符串类型参数
        if 'pattern' in kwargs:
            extra_params['pattern'] = kwargs['pattern']
        if 'min_length' in kwargs:
            extra_params['min_length'] = kwargs['min_length']
        if 'max_length' in kwargs:
            extra_params['max_length'] = kwargs['max_length']
        
        # 日期类型参数
        if 'start_date' in kwargs:
            extra_params['start_date'] = kwargs['start_date']
        if 'end_date' in kwargs:
            extra_params['end_date'] = kwargs['end_date']
        
        # 枚举类型参数
        if 'enum_values' in kwargs:
            extra_params['enum_values'] = kwargs['enum_values']
        
        # JSON 类型参数
        if 'json_template' in kwargs:
            extra_params['json_template'] = kwargs['json_template']
        
        # 其他参数
        if 'nullable' in kwargs:
            extra_params['nullable'] = kwargs['nullable']
        if 'default' in kwargs:
            extra_params['default'] = kwargs['default']
        
        return generator.generate_normal(column_info, count, **extra_params)


class BoundaryStrategy(GenerationStrategy):
    """边界值生成策略
    
    生成边界值测试数据，包括最小值、最大值、空值等边界情况。
    适用于边界值测试和健壮性测试。
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.BOUNDARY
    
    def generate(self, generator: DataGenerator, column_info: ColumnInfo, 
                 count: int, **kwargs) -> List[Any]:
        """生成边界值数据
        
        会生成以下类型的边界值：
        - 数据类型的最小值和最大值
        - 空值（如果字段允许）
        - 空字符串（对于字符串类型）
        - 零值（对于数值类型）
        - 特殊日期（对于日期类型）
        
        Args:
            generator: 数据生成器
            column_info: 字段信息
            count: 生成数量
            **kwargs: 额外参数
            
        Returns:
            生成的数据列表
        """
        boundary_values = generator.generate_boundary(column_info, count, **kwargs)
        
        # 如果边界值数量不足，补充正常值
        if len(boundary_values) < count:
            normal_values = generator.generate_normal(
                column_info, 
                count - len(boundary_values),
                **kwargs
            )
            boundary_values.extend(normal_values)
        
        return boundary_values[:count]


class AbnormalStrategy(GenerationStrategy):
    """异常值生成策略
    
    生成异常值测试数据，包括超出范围、格式错误、类型错误等。
    适用于异常测试和负面测试。
    
    注意：生成的数据可能无法插入数据库，主要用于测试系统的错误处理能力。
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.ABNORMAL
    
    def generate(self, generator: DataGenerator, column_info: ColumnInfo, 
                 count: int, **kwargs) -> List[Any]:
        """生成异常值数据
        
        会生成以下类型的异常值：
        - 超出数据类型范围的值
        - 类型错误的值（如字符串字段传入数字）
        - 格式错误的值
        - SQL 注入测试字符串（对于字符串类型）
        - 特殊字符和 Unicode 字符
        
        Args:
            generator: 数据生成器
            column_info: 字段信息
            count: 生成数量
            **kwargs: 额外参数
            
        Returns:
            生成的数据列表
        """
        abnormal_values = generator.generate_abnormal(column_info, count, **kwargs)
        
        # 如果异常值数量不足，补充边界值
        if len(abnormal_values) < count:
            boundary_values = generator.generate_boundary(
                column_info,
                count - len(abnormal_values),
                **kwargs
            )
            abnormal_values.extend(boundary_values)
        
        return abnormal_values[:count]


class MixedStrategy(GenerationStrategy):
    """混合生成策略
    
    按照指定比例混合生成正常值、边界值和异常值。
    适用于综合测试场景。
    """
    
    def __init__(self, 
                 normal_ratio: float = 0.6,
                 boundary_ratio: float = 0.3,
                 abnormal_ratio: float = 0.1):
        """初始化混合策略
        
        Args:
            normal_ratio: 正常值比例
            boundary_ratio: 边界值比例
            abnormal_ratio: 异常值比例
            
        Raises:
            ValueError: 当比例之和不为 1 时
        """
        total = normal_ratio + boundary_ratio + abnormal_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"比例之和必须为 1，当前为 {total}")
        
        self.normal_ratio = normal_ratio
        self.boundary_ratio = boundary_ratio
        self.abnormal_ratio = abnormal_ratio
        
        self._normal_strategy = NormalStrategy()
        self._boundary_strategy = BoundaryStrategy()
        self._abnormal_strategy = AbnormalStrategy()
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MIXED
    
    def generate(self, generator: DataGenerator, column_info: ColumnInfo, 
                 count: int, **kwargs) -> List[Any]:
        """按比例混合生成数据
        
        Args:
            generator: 数据生成器
            column_info: 字段信息
            count: 生成数量
            **kwargs: 额外参数
            
        Returns:
            生成的数据列表
        """
        normal_count = int(count * self.normal_ratio)
        boundary_count = int(count * self.boundary_ratio)
        abnormal_count = count - normal_count - boundary_count
        
        result = []
        
        if normal_count > 0:
            result.extend(self._normal_strategy.generate(
                generator, column_info, normal_count, **kwargs
            ))
        
        if boundary_count > 0:
            result.extend(self._boundary_strategy.generate(
                generator, column_info, boundary_count, **kwargs
            ))
        
        if abnormal_count > 0:
            result.extend(self._abnormal_strategy.generate(
                generator, column_info, abnormal_count, **kwargs
            ))
        
        return result


class CustomStrategy(GenerationStrategy):
    """自定义生成策略
    
    允许用户提供自定义的数据生成函数。
    """
    
    def __init__(self, 
                 generate_func: Callable[[ColumnInfo, int], List[Any]],
                 strategy_name: str = 'custom'):
        """初始化自定义策略
        
        Args:
            generate_func: 自定义生成函数，接收字段信息和数量，返回数据列表
            strategy_name: 策略名称
        """
        self._generate_func = generate_func
        self._strategy_name = strategy_name
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.NORMAL  # 自定义策略归类为 NORMAL
    
    @property
    def strategy_name(self) -> str:
        return self._strategy_name
    
    def generate(self, generator: DataGenerator, column_info: ColumnInfo, 
                 count: int, **kwargs) -> List[Any]:
        """使用自定义函数生成数据
        
        Args:
            generator: 数据生成器（可能不会被使用）
            column_info: 字段信息
            count: 生成数量
            **kwargs: 额外参数
            
        Returns:
            生成的数据列表
        """
        return self._generate_func(column_info, count, **kwargs)


# 策略工厂
class StrategyFactory:
    """策略工厂类
    
    用于创建和管理数据生成策略。
    """
    
    _strategies: Dict[str, type] = {
        'normal': NormalStrategy,
        'boundary': BoundaryStrategy,
        'abnormal': AbnormalStrategy,
        'mixed': MixedStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: str, **kwargs) -> GenerationStrategy:
        """创建策略实例
        
        Args:
            strategy_type: 策略类型名称
            **kwargs: 策略初始化参数
            
        Returns:
            策略实例
            
        Raises:
            ValueError: 当策略类型无效时
        """
        if strategy_type not in cls._strategies:
            raise ValueError(
                f"无效的策略类型: {strategy_type}，"
                f"可选值: {list(cls._strategies.keys())}"
            )
        
        strategy_class = cls._strategies[strategy_type]
        return strategy_class(**kwargs)
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """注册自定义策略
        
        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        cls._strategies[name] = strategy_class
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """列出所有可用策略
        
        Returns:
            策略名称列表
        """
        return list(cls._strategies.keys())
