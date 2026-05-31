# -*- coding: utf-8 -*-
"""各数据类型的生成器实现

提供针对不同数据类型的具体生成器实现。
"""

import json
import uuid
from datetime import datetime, date, timedelta
from typing import Any, List, Optional, Dict, Union, TYPE_CHECKING
from decimal import Decimal

from .base import DataGenerator

if TYPE_CHECKING:
    from src.schema_parser.models import ColumnInfo


class IntegerGenerator(DataGenerator):
    """整数生成器
    
    支持生成各种整数类型的数据，包括 TINYINT, SMALLINT, INT, BIGINT 等。
    """
    
    SUPPORTED_TYPES = ['TINYINT', 'SMALLINT', 'INT', 'INTEGER', 'BIGINT', 'MEDIUMINT']
    
    # 各整数类型的范围
    TYPE_RANGES = {
        'TINYINT': (-128, 127),
        'SMALLINT': (-32768, 32767),
        'MEDIUMINT': (-8388608, 8388607),
        'INT': (-2147483648, 2147483647),
        'INTEGER': (-2147483648, 2147483647),
        'BIGINT': (-9223372036854775808, 9223372036854775807),
    }
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1, 
                        min_value: Optional[int] = None, 
                        max_value: Optional[int] = None, **kwargs) -> List[int]:
        """生成正常整数数据
        
        Args:
            column_info: 字段信息
            count: 生成数量
            min_value: 最小值（覆盖默认范围）
            max_value: 最大值（覆盖默认范围）
            
        Returns:
            整数列表
        """
        data_type = column_info.data_type.upper()
        default_min, default_max = self.TYPE_RANGES.get(data_type, (0, 100))
        
        min_val = min_value if min_value is not None else default_min
        max_val = max_value if max_value is not None else default_max
        
        values = [self.faker.random_int(min=min_val, max=max_val) for _ in range(count)]
        values = self._handle_nullable(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[int]]:
        """生成边界值数据
        
        生成最小值、最大值、0、空值等边界值。
        """
        data_type = column_info.data_type.upper()
        min_val, max_val = self.TYPE_RANGES.get(data_type, (0, 100))
        
        boundary_values = [min_val, max_val, 0, min_val + 1, max_val - 1]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        # 如果需要更多数据，循环填充
        base_values = [min_val, max_val, 0, min_val + 1, max_val - 1]
        while len(boundary_values) < count:
            boundary_values.append(base_values[len(boundary_values) % len(base_values)])
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据
        
        生成超出范围、类型错误等异常数据。
        """
        data_type = column_info.data_type.upper()
        min_val, max_val = self.TYPE_RANGES.get(data_type, (0, 100))
        
        abnormal_values = [
            max_val + 1,  # 超出最大值
            min_val - 1,  # 超出最小值
            999999999999,  # 超大值
            -999999999999,  # 超小值
            3.14159,  # 浮点数
            "not_a_number",  # 字符串
            "",  # 空字符串
        ]
        
        if column_info.is_nullable:
            abnormal_values.append(None)
        
        return abnormal_values[:count]


class FloatGenerator(DataGenerator):
    """浮点数生成器
    
    支持生成 FLOAT, DOUBLE, DECIMAL 等类型的浮点数数据。
    """
    
    SUPPORTED_TYPES = ['FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1,
                        min_value: Optional[float] = None,
                        max_value: Optional[float] = None, **kwargs) -> List[float]:
        """生成正常浮点数数据"""
        min_val = min_value if min_value is not None else 0.0
        max_val = max_value if max_value is not None else 10000.0
        
        # 考虑精度和小数位数
        scale = column_info.scale if column_info.scale else 2
        precision = column_info.precision if column_info.precision else 10
        
        # 根据精度计算最大值
        if precision and scale:
            # 计算整数部分的最大位数
            int_part_digits = precision - scale
            if int_part_digits > 0:
                max_val = min(max_val, 10 ** int_part_digits - 1 / (10 ** scale))
        
        values = []
        for _ in range(count):
            value = self.faker.pyfloat(
                min_value=min_val, 
                max_value=max_val,
                right_digits=scale
            )
            # 确保精度和小数位数正确
            value = round(value, scale)
            values.append(value)
        
        values = self._handle_nullable(values, column_info)
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[float]]:
        """生成边界值数据"""
        scale = column_info.scale if column_info.scale else 2
        
        boundary_values = [
            0.0,
            0.1,
            -0.1,
            round(1.0 / 3.0, scale),
            round(2.0 / 3.0, scale),
        ]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        # 考虑精度范围
        if column_info.precision:
            max_val = 10 ** (column_info.precision - scale) - 1
            boundary_values.extend([max_val, -max_val])
        
        while len(boundary_values) < count:
            boundary_values.append(boundary_values[len(boundary_values) % len(boundary_values)])
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        abnormal_values = [
            float('inf'),  # 无穷大
            float('-inf'),  # 负无穷大
            float('nan'),  # NaN
            1e308,  # 接近浮点数上限
            -1e308,  # 接近浮点数下限
            "not_a_float",  # 字符串
            None,  # 空值
        ]
        
        return abnormal_values[:count]


class StringGenerator(DataGenerator):
    """字符串生成器
    
    支持生成各种字符串类型的数据，包括 CHAR, VARCHAR, TEXT 等。
    """
    
    SUPPORTED_TYPES = ['CHAR', 'VARCHAR', 'TEXT', 'TINYTEXT', 'MEDIUMTEXT', 'LONGTEXT', 'STRING']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1,
                        pattern: Optional[str] = None,
                        min_length: Optional[int] = None,
                        max_length: Optional[int] = None, **kwargs) -> List[str]:
        """生成正常字符串数据
        
        Args:
            column_info: 字段信息
            count: 生成数量
            pattern: 字符串模式（如 'name', 'email', 'address' 等）
            min_length: 最小长度
            max_length: 最大长度
        """
        max_len = column_info.length if column_info.length else 255
        min_len = min_length if min_length is not None else 1
        actual_max = max_length if max_length is not None else max_len
        
        values = []
        
        for _ in range(count):
            if pattern == 'name':
                value = self.faker.name()
            elif pattern == 'email':
                value = self.faker.email()
            elif pattern == 'phone':
                value = self.faker.phone_number()
            elif pattern == 'address':
                value = self.faker.address()
            elif pattern == 'company':
                value = self.faker.company()
            elif pattern == 'url':
                value = self.faker.url()
            elif pattern == 'uuid':
                value = str(self.faker.uuid4())
            elif pattern == 'chinese':
                # 生成汉字
                length = self.faker.random_int(min=min_len, max=min(actual_max, max_len))
                # 生成指定长度的汉字
                value = ''.join([chr(self.faker.random_int(0x4e00, 0x9fa5)) for _ in range(length)])
            elif pattern == 'letters':
                # 生成字母
                length = self.faker.random_int(min=min_len, max=min(actual_max, max_len))
                value = self.faker.lexify(text='?' * length)
            elif pattern == 'characters':
                # 生成字符（包括字母、数字、特殊字符）
                length = self.faker.random_int(min=min_len, max=min(actual_max, max_len))
                value = self.faker.password(length=length, special_chars=True, digits=True, upper_case=True, lower_case=True)
            elif pattern == 'random_number':
                # 生成随机数字字符串
                length = self.faker.random_int(min=min_len, max=min(actual_max, max_len))
                value = ''.join([str(self.faker.random_digit()) for _ in range(length)])
            else:
                # 生成随机字符串
                length = self.faker.random_int(min=min_len, max=min(actual_max, max_len))
                if length < 5:
                    # 对于短字符串，使用word()方法
                    value = self.faker.word()[:length]
                    # 确保长度符合要求
                    while len(value) < length:
                        value += self.faker.word()[:length - len(value)]
                else:
                    # 对于长字符串，使用text()方法
                    value = self.faker.text(max_nb_chars=length)[:length]
            
            # 严格截断到最大长度
            value = str(value)[:actual_max]
            # 确保最小长度
            if len(value) < min_len:
                value = value.ljust(min_len, ' ')
            values.append(value)
        
        values = self._handle_nullable(values, column_info)
        values = self._apply_unique_constraint(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[str]]:
        """生成边界值数据"""
        max_len = column_info.length if column_info.length else 255
        
        boundary_values = [
            "",  # 空字符串
            " ",  # 单空格
            "a",  # 单字符
            "a" * max_len,  # 最大长度
            "a" * (max_len - 1),  # 最大长度-1
            "\t\n\r",  # 特殊字符
            "测试中文",  # 中文
            "test123!@#",  # 特殊字符
        ]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        max_len = column_info.length if column_info.length else 255
        
        abnormal_values = [
            "a" * (max_len + 1),  # 超出最大长度
            "a" * (max_len + 100),  # 远超最大长度
            12345,  # 数字类型
            None,  # 空值
            "",  # 空字符串（如果非空字段）
        ]
        
        # SQL 注入测试字符串
        sql_injection_tests = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1; DELETE FROM table",
        ]
        abnormal_values.extend(sql_injection_tests)
        
        return abnormal_values[:count]


class DateTimeGenerator(DataGenerator):
    """日期时间生成器
    
    支持生成 DATETIME, TIMESTAMP 类型的数据。
    """
    
    SUPPORTED_TYPES = ['DATETIME', 'TIMESTAMP', 'TIMESTAMP WITH TIME ZONE']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None, **kwargs) -> List[datetime]:
        """生成正常日期时间数据"""
        start = start_date if start_date else datetime(2000, 1, 1)
        end = end_date if end_date else datetime.now()
        
        values = [self.faker.date_time_between(start_date=start, end_date=end) for _ in range(count)]
        values = self._handle_nullable(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[datetime]]:
        """生成边界值数据"""
        now = datetime.now()
        
        boundary_values = [
            datetime(1970, 1, 1, 0, 0, 0),  # Unix 纪元
            datetime(2000, 1, 1, 0, 0, 0),  # 千禧年
            datetime(2038, 1, 19, 3, 14, 7),  # 2038 问题边界
            datetime.min,  # 最小值
            datetime.max,  # 最大值
            now,  # 当前时间
            datetime(now.year, 1, 1),  # 年初
            datetime(now.year, 12, 31, 23, 59, 59),  # 年末
        ]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        abnormal_values = [
            "not_a_date",
            "2023-13-01",  # 无效月份
            "2023-02-30",  # 无效日期
            "2023-01-01 25:00:00",  # 无效小时
            12345,  # 数字
            None,  # 空值
            "",  # 空字符串
        ]
        
        return abnormal_values[:count]


class DateGenerator(DataGenerator):
    """日期生成器
    
    支持生成 DATE 类型的数据。
    """
    
    SUPPORTED_TYPES = ['DATE']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None, **kwargs) -> List[date]:
        """生成正常日期数据"""
        start = start_date if start_date else date(2000, 1, 1)
        end = end_date if end_date else date.today()
        
        values = [self.faker.date_between(start_date=start, end_date=end) for _ in range(count)]
        values = self._handle_nullable(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[date]]:
        """生成边界值数据"""
        today = date.today()
        
        boundary_values = [
            date(1970, 1, 1),  # Unix 纪元
            date(2000, 1, 1),  # 千禧年
            date.min,  # 最小值
            date.max,  # 最大值
            today,  # 今天
            date(today.year, 1, 1),  # 年初
            date(today.year, 12, 31),  # 年末
        ]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        abnormal_values = [
            "not_a_date",
            "2023-13-01",  # 无效月份
            "2023-02-30",  # 无效日期
            12345,  # 数字
            None,  # 空值
            "",  # 空字符串
            datetime.now(),  # datetime 对象
        ]
        
        return abnormal_values[:count]


class BooleanGenerator(DataGenerator):
    """布尔值生成器
    
    支持生成 BOOLEAN, BOOL 类型的数据。
    """
    
    SUPPORTED_TYPES = ['BOOLEAN', 'BOOL', 'BIT']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[bool]:
        """生成正常布尔值数据"""
        values = [self.faker.pybool() for _ in range(count)]
        values = self._handle_nullable(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[bool]]:
        """生成边界值数据"""
        boundary_values = [True, False]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        while len(boundary_values) < count:
            boundary_values.append(boundary_values[len(boundary_values) % len(boundary_values)])
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        abnormal_values = [
            1,  # 数字 1
            0,  # 数字 0
            "true",  # 字符串
            "false",  # 字符串
            "yes",  # 字符串
            "",  # 空字符串
            None,  # 空值
            2,  # 非 0/1 数字
            -1,  # 负数
        ]
        
        return abnormal_values[:count]


class EnumGenerator(DataGenerator):
    """枚举值生成器
    
    支持生成 ENUM, SET 类型的数据。
    """
    
    SUPPORTED_TYPES = ['ENUM', 'SET']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1,
                        enum_values: Optional[List[str]] = None, **kwargs) -> List[str]:
        """生成正常枚举值数据
        
        Args:
            column_info: 字段信息
            count: 生成数量
            enum_values: 枚举值列表（如果字段信息中没有）
        """
        # 从字段信息中获取枚举值，或使用传入的值
        values_list = enum_values or getattr(column_info, 'enum_values', ['value1', 'value2', 'value3'])
        
        values = [self.faker.random_element(values_list) for _ in range(count)]
        values = self._handle_nullable(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1,
                          enum_values: Optional[List[str]] = None, **kwargs) -> List[Optional[str]]:
        """生成边界值数据"""
        values_list = enum_values or getattr(column_info, 'enum_values', ['value1', 'value2', 'value3'])
        
        boundary_values = [values_list[0]]  # 第一个值
        if len(values_list) > 1:
            boundary_values.append(values_list[-1])  # 最后一个值
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        while len(boundary_values) < count:
            boundary_values.append(self.faker.random_element(values_list))
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1,
                          enum_values: Optional[List[str]] = None, **kwargs) -> List[Any]:
        """生成异常值数据"""
        values_list = enum_values or getattr(column_info, 'enum_values', ['value1', 'value2', 'value3'])
        
        abnormal_values = [
            "invalid_enum_value",  # 无效枚举值
            "",  # 空字符串
            " " * 10,  # 空格
            123,  # 数字
            None,  # 空值
            values_list[0].upper() if values_list else "UPPERCASE",  # 大小写错误
        ]
        
        return abnormal_values[:count]


class JSONGenerator(DataGenerator):
    """JSON 数据生成器
    
    支持生成 JSON, JSONB 类型的数据。
    """
    
    SUPPORTED_TYPES = ['JSON', 'JSONB']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1,
                        json_template: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """生成正常 JSON 数据
        
        Args:
            column_info: 字段信息
            count: 生成数量
            json_template: JSON 模板（如果提供，将基于模板生成）
        """
        values = []
        
        for _ in range(count):
            if json_template:
                # 基于模板生成
                value = self._generate_from_template(json_template)
            else:
                # 生成随机 JSON
                value = {
                    'id': self.faker.uuid4(),
                    'name': self.faker.name(),
                    'email': self.faker.email(),
                    'created_at': self.faker.iso8601(),
                    'status': self.faker.random_element(['active', 'inactive', 'pending']),
                    'score': self.faker.pyfloat(min_value=0, max_value=100),
                    'tags': self.faker.words(nb=3),
                }
            values.append(value)
        
        values = self._handle_nullable(values, column_info)
        
        return values
    
    def _generate_from_template(self, template: Dict) -> Dict:
        """根据模板生成 JSON 数据"""
        result = {}
        for key, value_type in template.items():
            if value_type == 'string':
                result[key] = self.faker.word()
            elif value_type == 'int':
                result[key] = self.faker.random_int()
            elif value_type == 'float':
                result[key] = self.faker.pyfloat()
            elif value_type == 'bool':
                result[key] = self.faker.pybool()
            elif value_type == 'date':
                result[key] = self.faker.date()
            elif value_type == 'email':
                result[key] = self.faker.email()
            elif value_type == 'name':
                result[key] = self.faker.name()
            elif isinstance(value_type, dict):
                result[key] = self._generate_from_template(value_type)
            elif isinstance(value_type, list) and len(value_type) > 0:
                result[key] = [self.faker.word() for _ in range(3)]
            else:
                result[key] = self.faker.word()
        
        return result
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[Dict]]:
        """生成边界值数据"""
        boundary_values = [
            {},  # 空对象
            {'key': 'value'},  # 简单对象
            {'a': {'b': {'c': 'd'}}},  # 嵌套对象
            {'array': [1, 2, 3]},  # 包含数组
            {'null_value': None},  # 包含 null
            {'unicode': '中文测试'},  # Unicode
        ]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        abnormal_values = [
            "not_json",  # 非 JSON 字符串
            "{invalid json}",  # 无效 JSON
            12345,  # 数字
            None,  # 空值
            "",  # 空字符串
            "[]",  # JSON 数组字符串
            '{"key": undefined}',  # 包含 undefined
        ]
        
        return abnormal_values[:count]


class UUIDGenerator(DataGenerator):
    """UUID 生成器
    
    支持生成 UUID 类型的数据。
    """
    
    SUPPORTED_TYPES = ['UUID', 'UNIQUEIDENTIFIER']
    
    def supports_type(self, data_type: str) -> bool:
        return data_type.upper() in self.SUPPORTED_TYPES
    
    def generate_normal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[str]:
        """生成正常 UUID 数据"""
        values = [str(uuid.uuid4()) for _ in range(count)]
        values = self._handle_nullable(values, column_info)
        values = self._apply_unique_constraint(values, column_info)
        
        return values
    
    def generate_boundary(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Optional[str]]:
        """生成边界值数据"""
        boundary_values = [
            "00000000-0000-0000-0000-000000000000",  # 全零 UUID
            "ffffffff-ffff-ffff-ffff-ffffffffffff",  # 全 F UUID
            str(uuid.uuid4()),  # 随机 UUID
        ]
        
        if column_info.is_nullable:
            boundary_values.append(None)
        
        while len(boundary_values) < count:
            boundary_values.append(str(uuid.uuid4()))
        
        return boundary_values[:count]
    
    def generate_abnormal(self, column_info: ColumnInfo, count: int = 1, **kwargs) -> List[Any]:
        """生成异常值数据"""
        abnormal_values = [
            "not-a-uuid",  # 无效格式
            "12345",  # 太短
            "gggggggg-gggg-gggg-gggg-gggggggggggg",  # 无效字符
            "",  # 空字符串
            None,  # 空值
            12345,  # 数字
            "00000000-0000-0000-0000-00000000000",  # 少一位
            "00000000-0000-0000-0000-0000000000000",  # 多一位
        ]
        
        return abnormal_values[:count]


# 生成器注册表
GENERATOR_REGISTRY: Dict[str, type] = {
    'integer': IntegerGenerator,
    'float': FloatGenerator,
    'string': StringGenerator,
    'datetime': DateTimeGenerator,
    'date': DateGenerator,
    'boolean': BooleanGenerator,
    'enum': EnumGenerator,
    'json': JSONGenerator,
    'uuid': UUIDGenerator,
}


def get_generator_for_type(data_type: str) -> Optional[DataGenerator]:
    """根据数据类型获取对应的生成器
    
    Args:
        data_type: 数据类型名称
        
    Returns:
        对应的生成器实例，如果没有匹配则返回 None
    """
    data_type_upper = data_type.upper()
    
    for generator_class in GENERATOR_REGISTRY.values():
        generator = generator_class()
        if generator.supports_type(data_type_upper):
            return generator
    
    return None
