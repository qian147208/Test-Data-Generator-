# -*- coding: utf-8 -*-
"""数据生成引擎

提供统一的数据生成接口，支持单字段和整表数据生成。
"""

from typing import Any, List, Dict, Optional, Union, TYPE_CHECKING
import logging

from .base import DataGenerator
from .generators import get_generator_for_type, GENERATOR_REGISTRY
from .strategies import (
    GenerationStrategy, 
    StrategyFactory, 
    StrategyType,
    NormalStrategy,
    BoundaryStrategy,
    AbnormalStrategy,
    MixedStrategy
)

if TYPE_CHECKING:
    from src.schema_parser.models import ColumnInfo, TableSchema


logger = logging.getLogger(__name__)


class ColumnRule:
    """字段生成规则
    
    用于自定义字段的数据生成规则。
    """
    
    def __init__(self,
                 column_name: str,
                 strategy: Optional[str] = None,
                 generator_params: Optional[Dict[str, Any]] = None,
                 custom_values: Optional[List[Any]] = None,
                 custom_generator: Optional[DataGenerator] = None):
        """初始化字段规则
        
        Args:
            column_name: 字段名
            strategy: 生成策略名称
            generator_params: 生成器参数
            custom_values: 自定义值列表（如果提供，将直接使用这些值）
            custom_generator: 自定义生成器实例
        """
        self.column_name = column_name
        self.strategy = strategy
        self.generator_params = generator_params or {}
        self.custom_values = custom_values
        self.custom_generator = custom_generator
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'column_name': self.column_name,
            'strategy': self.strategy,
            'generator_params': self.generator_params,
            'custom_values': self.custom_values,
            'has_custom_generator': self.custom_generator is not None
        }


class GenerationResult:
    """数据生成结果
    
    封装数据生成的结果信息。
    """
    
    def __init__(self,
                 data: List[Dict[str, Any]],
                 table_name: str,
                 strategy: str,
                 total_rows: int,
                 warnings: Optional[List[str]] = None):
        """初始化生成结果
        
        Args:
            data: 生成的数据列表
            table_name: 表名
            strategy: 使用的策略
            total_rows: 总行数
            warnings: 警告信息列表
        """
        self.data = data
        self.table_name = table_name
        self.strategy = strategy
        self.total_rows = total_rows
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'table_name': self.table_name,
            'strategy': self.strategy,
            'total_rows': self.total_rows,
            'warnings': self.warnings,
            'data': self.data
        }
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __iter__(self):
        return iter(self.data)
    
    def __getitem__(self, index):
        return self.data[index]


class DataEngine:
    """数据生成引擎
    
    提供统一的数据生成接口，支持：
    - 单字段数据生成
    - 整表数据生成
    - 自定义字段规则
    - 多种生成策略
    """
    
    def __init__(self, locale: str = 'zh_CN'):
        """初始化数据引擎
        
        Args:
            locale: Faker 语言区域设置
        """
        self.locale = locale
        self._generator_cache: Dict[str, DataGenerator] = {}
        self._column_rules: Dict[str, ColumnRule] = {}
        self._warnings: List[str] = []
    
    def register_column_rule(self, rule: ColumnRule):
        """注册字段生成规则
        
        Args:
            rule: 字段规则
        """
        self._column_rules[rule.column_name] = rule
        logger.info(f"已注册字段规则: {rule.column_name}")
    
    def register_column_rules(self, rules: List[ColumnRule]):
        """批量注册字段生成规则
        
        Args:
            rules: 字段规则列表
        """
        for rule in rules:
            self.register_column_rule(rule)
    
    def clear_column_rules(self):
        """清除所有字段规则"""
        self._column_rules.clear()
    
    def get_generator(self, column_info: ColumnInfo) -> DataGenerator:
        """获取字段对应的生成器
        
        优先使用自定义规则中的生成器，否则根据数据类型自动选择。
        
        Args:
            column_info: 字段信息
            
        Returns:
            数据生成器实例
        """
        # 检查是否有自定义生成器
        if column_info.name in self._column_rules:
            rule = self._column_rules[column_info.name]
            if rule.custom_generator:
                return rule.custom_generator
            # 对于新的数据类型，直接使用字符串生成器
            if rule.strategy in ['chinese', 'letters', 'characters', 'random_number']:
                from .generators import StringGenerator
                generator = StringGenerator(locale=self.locale)
                return generator
        
        # 使用缓存的生成器
        cache_key = f"{column_info.data_type}_{column_info.name}_{column_info.length}_{column_info.precision}_{column_info.scale}"
        if cache_key in self._generator_cache:
            return self._generator_cache[cache_key]
        
        # 根据数据类型获取生成器
        generator = get_generator_for_type(column_info.data_type)
        
        if generator is None:
            logger.warning(
                f"未找到数据类型 '{column_info.data_type}' 的生成器，"
                f"将使用字符串生成器"
            )
            # 默认使用字符串生成器
            from .generators import StringGenerator
            generator = StringGenerator(locale=self.locale)
        else:
            # 为生成器设置语言区域
            if hasattr(generator, 'locale'):
                generator.locale = self.locale
        
        self._generator_cache[cache_key] = generator
        return generator
    
    def generate_for_column(self,
                            column_info: ColumnInfo,
                            strategy: Union[str, GenerationStrategy] = 'normal',
                            count: int = 10,
                            **kwargs) -> List[Any]:
        """为单个字段生成数据
        
        Args:
            column_info: 字段信息
            strategy: 生成策略（名称或实例）
            count: 生成数量
            **kwargs: 额外参数
            
        Returns:
            生成的数据列表
        """
        # 获取生成器
        generator = self.get_generator(column_info)
        
        # 获取策略实例
        if isinstance(strategy, str):
            # 检查字段规则中的策略
            if column_info.name in self._column_rules:
                rule = self._column_rules[column_info.name]
                if rule.strategy:
                    # 处理新的数据类型
                    if rule.strategy in ['chinese', 'letters', 'characters', 'random_number']:
                        # 对于新的数据类型，使用字符串生成器并传递pattern参数
                        kwargs['pattern'] = rule.strategy
                    strategy = rule.strategy
                # 合并生成器参数
                kwargs = {**rule.generator_params, **kwargs}
            
            strategy_instance = StrategyFactory.create_strategy(strategy)
        else:
            strategy_instance = strategy
        
        # 根据字段属性添加参数
        if column_info.length:
            kwargs['max_length'] = column_info.length
        if column_info.precision:
            kwargs['precision'] = column_info.precision
        if column_info.scale:
            kwargs['scale'] = column_info.scale
        if column_info.is_nullable:
            kwargs['nullable'] = column_info.is_nullable
        if hasattr(column_info, 'default') and column_info.default is not None:
            kwargs['default'] = column_info.default
        
        # 生成数据
        return strategy_instance.generate(generator, column_info, count, **kwargs)
    
    def generate_for_table(self,
                           table_schema: TableSchema,
                           strategy: Union[str, GenerationStrategy] = 'normal',
                           count: int = 10,
                           **kwargs) -> GenerationResult:
        """为整个表生成数据
        
        Args:
            table_schema: 表结构信息
            strategy: 生成策略（名称或实例）
            count: 生成行数
            **kwargs: 额外参数
            
        Returns:
            生成结果对象
        """
        self._warnings = []
        data = []
        
        # 获取策略名称（用于结果记录）
        strategy_name = strategy if isinstance(strategy, str) else strategy.strategy_type.value
        
        # 为每个字段生成数据
        column_data: Dict[str, List[Any]] = {}
        
        for column in table_schema.columns:
            try:
                # 跳过自增字段（通常由数据库自动生成）
                if column.autoincrement:
                    column_data[column.name] = [None] * count
                    self._warnings.append(f"字段 '{column.name}' 为自增字段，已跳过生成")
                    continue
                
                # 生成字段数据
                values = self.generate_for_column(column, strategy, count, **kwargs)
                column_data[column.name] = values
                
            except Exception as e:
                logger.error(f"生成字段 '{column.name}' 数据时出错: {e}")
                self._warnings.append(f"字段 '{column.name}' 生成失败: {str(e)}")
                column_data[column.name] = [None] * count
        
        # 组装行数据
        for i in range(count):
            row = {}
            for column in table_schema.columns:
                if column.name in column_data:
                    row[column.name] = column_data[column.name][i]
            data.append(row)
        
        return GenerationResult(
            data=data,
            table_name=table_schema.table_name,
            strategy=strategy_name,
            total_rows=count,
            warnings=self._warnings
        )
    
    def generate_with_foreign_keys(self,
                                   table_schema: TableSchema,
                                   strategy: Union[str, GenerationStrategy] = 'normal',
                                   count: int = 10,
                                   foreign_key_values: Optional[Dict[str, List[Any]]] = None,
                                   **kwargs) -> GenerationResult:
        """生成带有外键约束的数据
        
        Args:
            table_schema: 表结构信息
            strategy: 生成策略
            count: 生成行数
            foreign_key_values: 外键字段的可选值字典
            **kwargs: 额外参数
            
        Returns:
            生成结果对象
        """
        if foreign_key_values is None:
            foreign_key_values = {}
        
        # 找出外键字段
        fk_columns = set()
        for fk in table_schema.foreign_keys:
            fk_columns.update(fk.constrained_columns)
        
        # 为每个字段生成数据
        column_data: Dict[str, List[Any]] = {}
        
        for column in table_schema.columns:
            if column.autoincrement:
                column_data[column.name] = [None] * count
                continue
            
            # 如果是外键字段且有提供值
            if column.name in fk_columns and column.name in foreign_key_values:
                values = foreign_key_values[column.name]
                # 从提供的值中随机选择
                from faker import Faker
                faker = Faker(self.locale)
                column_data[column.name] = [
                    faker.random_element(values) for _ in range(count)
                ]
            else:
                column_data[column.name] = self.generate_for_column(
                    column, strategy, count, **kwargs
                )
        
        # 组装行数据
        data = []
        for i in range(count):
            row = {}
            for column in table_schema.columns:
                if column.name in column_data:
                    row[column.name] = column_data[column.name][i]
            data.append(row)
        
        strategy_name = strategy if isinstance(strategy, str) else strategy.strategy_type.value
        
        return GenerationResult(
            data=data,
            table_name=table_schema.table_name,
            strategy=strategy_name,
            total_rows=count,
            warnings=self._warnings
        )
    
    def preview_column(self,
                       column_info: ColumnInfo,
                       strategy: str = 'normal',
                       count: int = 5) -> Dict[str, Any]:
        """预览字段生成结果
        
        生成少量数据用于预览，同时返回字段和生成器信息。
        
        Args:
            column_info: 字段信息
            strategy: 生成策略
            count: 预览数量
            
        Returns:
            包含预览数据和元信息的字典
        """
        generator = self.get_generator(column_info)
        values = self.generate_for_column(column_info, strategy, count)
        
        return {
            'column_name': column_info.name,
            'data_type': column_info.data_type,
            'nullable': column_info.is_nullable,
            'strategy': strategy,
            'generator': generator.__class__.__name__,
            'sample_values': values
        }
    
    def get_supported_types(self) -> List[str]:
        """获取所有支持的数据类型
        
        Returns:
            支持的数据类型列表
        """
        supported = set()
        for generator_class in GENERATOR_REGISTRY.values():
            generator = generator_class()
            supported.update(generator.SUPPORTED_TYPES)
        return sorted(list(supported))
    
    def get_available_strategies(self) -> List[str]:
        """获取所有可用的生成策略
        
        Returns:
            策略名称列表
        """
        return StrategyFactory.list_strategies()


class DataEngineBuilder:
    """数据引擎构建器
    
    提供流式 API 构建数据引擎实例。
    """
    
    def __init__(self):
        self._locale = 'zh_CN'
        self._column_rules: List[ColumnRule] = []
    
    def with_locale(self, locale: str) -> 'DataEngineBuilder':
        """设置语言区域"""
        self._locale = locale
        return self
    
    def with_column_rule(self, rule: ColumnRule) -> 'DataEngineBuilder':
        """添加字段规则"""
        self._column_rules.append(rule)
        return self
    
    def with_column_rules(self, rules: List[ColumnRule]) -> 'DataEngineBuilder':
        """批量添加字段规则"""
        self._column_rules.extend(rules)
        return self
    
    def build(self) -> DataEngine:
        """构建数据引擎实例"""
        engine = DataEngine(locale=self._locale)
        engine.register_column_rules(self._column_rules)
        return engine
