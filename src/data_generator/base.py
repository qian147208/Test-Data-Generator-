# -*- coding: utf-8 -*-
"""数据生成器抽象基类

定义数据生成器的抽象接口和基础功能。
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict, TYPE_CHECKING
from faker import Faker

if TYPE_CHECKING:
    from src.schema_parser.models import ColumnInfo


class DataGenerator(ABC):
    """数据生成器抽象基类
    
    所有具体数据生成器的基类，定义了统一的接口和共享功能。
    
    Attributes:
        faker: Faker 实例，用于生成随机数据
        locale: Faker 的语言区域设置
    """
    
    def __init__(self, locale: str = 'zh_CN'):
        """初始化数据生成器
        
        Args:
            locale: Faker 的语言区域设置，默认为中文
        """
        self.faker = Faker(locale)
        self.locale = locale
    
    @abstractmethod
    def generate_normal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成正常值数据
        
        根据字段约束生成符合要求的正常数据。
        
        Args:
            column_info: 字段信息
            count: 生成数据的数量
            **kwargs: 额外的生成参数
            
        Returns:
            生成的数据列表
        """
        pass
    
    @abstractmethod
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成边界值数据
        
        生成边界值测试数据，如最小值、最大值、空值等。
        
        Args:
            column_info: 字段信息
            count: 生成数据的数量
            **kwargs: 额外的生成参数
            
        Returns:
            生成的数据列表
        """
        pass
    
    @abstractmethod
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据
        
        生成异常值测试数据，如超出范围、格式错误等。
        
        Args:
            column_info: 字段信息
            count: 生成数据的数量
            **kwargs: 额外的生成参数
            
        Returns:
            生成的数据列表
        """
        pass
    
    def generate(self, column_info: ColumnInfo, strategy: str = 'normal', 
                 count: int = 1, **kwargs) -> List[Any]:
        """根据策略生成数据
        
        根据指定的策略生成数据。
        
        Args:
            column_info: 字段信息
            strategy: 生成策略，可选值: 'normal', 'boundary', 'abnormal'
            count: 生成数据的数量
            **kwargs: 额外的生成参数
            
        Returns:
            生成的数据列表
            
        Raises:
            ValueError: 当策略名称无效时
        """
        strategy_map = {
            'normal': self.generate_normal,
            'boundary': self.generate_boundary,
            'abnormal': self.generate_abnormal
        }
        
        if strategy not in strategy_map:
            raise ValueError(f"无效的策略: {strategy}，可选值: {list(strategy_map.keys())}")
        
        return strategy_map[strategy](column_info, count, **kwargs)
    
    def supports_type(self, data_type: str) -> bool:
        """检查生成器是否支持指定的数据类型
        
        Args:
            data_type: 数据类型名称
            
        Returns:
            是否支持该数据类型
        """
        return False
    
    def _handle_nullable(self, values: List[Any], column_info: ColumnInfo, 
                         null_probability: float = 0.1) -> List[Any]:
        """处理可空字段
        
        根据字段是否允许为空，随机插入空值。
        
        Args:
            values: 原始数据列表
            column_info: 字段信息
            null_probability: 插入空值的概率（仅当字段允许为空时）
            
        Returns:
            处理后的数据列表
        """
        if not column_info.is_nullable:
            return values
        
        result = []
        for value in values:
            if self.faker.random.random() < null_probability:
                result.append(None)
            else:
                result.append(value)
        
        return result
    
    def _apply_unique_constraint(self, values: List[Any], column_info: ColumnInfo) -> List[Any]:
        """应用唯一约束
        
        如果字段有唯一约束，确保生成的值唯一。
        
        Args:
            values: 原始数据列表
            column_info: 字段信息
            
        Returns:
            处理后的数据列表
        """
        if not column_info.is_unique:
            return values
        
        # 去重并保持顺序
        seen = set()
        result = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        
        return result
    
    def _validate_constraints(self, value: Any, column_info: ColumnInfo) -> bool:
        """验证值是否符合字段约束
        
        Args:
            value: 要验证的值
            column_info: 字段信息
            
        Returns:
            是否符合约束
        """
        # 检查空值约束
        if value is None and not column_info.is_nullable:
            return False
        
        return True
    
    def get_generator_info(self) -> Dict[str, Any]:
        """获取生成器信息
        
        Returns:
            生成器的元信息
        """
        return {
            'class_name': self.__class__.__name__,
            'locale': self.locale,
            'supported_types': getattr(self, 'SUPPORTED_TYPES', [])
        }
