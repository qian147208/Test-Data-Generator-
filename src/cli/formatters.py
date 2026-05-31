# -*- coding: utf-8 -*-
"""输出格式化模块

提供多种数据输出格式，支持:
- SQL INSERT 语句
- CSV 文件
- JSON 文件
"""

import csv
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BaseFormatter(ABC):
    """输出格式化器基类
    
    所有格式化器必须继承此类并实现 format 和 save 方法。
    """
    
    @abstractmethod
    def format(self, data: List[Dict[str, Any]], table_name: str, **kwargs) -> str:
        """格式化数据
        
        Args:
            data: 数据列表
            table_name: 表名
            **kwargs: 额外参数
            
        Returns:
            格式化后的字符串
        """
        pass
    
    @abstractmethod
    def save(self, data: List[Dict[str, Any]], table_name: str, 
             output_path: Union[str, Path], **kwargs) -> Path:
        """保存数据到文件
        
        Args:
            data: 数据列表
            table_name: 表名
            output_path: 输出文件路径
            **kwargs: 额外参数
            
        Returns:
            保存的文件路径
        """
        pass
    
    @staticmethod
    def ensure_output_dir(output_path: Union[str, Path]) -> Path:
        """确保输出目录存在
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            Path 对象
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class SQLFormatter(BaseFormatter):
    """SQL INSERT 语句格式化器
    
    将数据格式化为 SQL INSERT 语句。
    
    Example:
        >>> formatter = SQLFormatter()
        >>> sql = formatter.format([{'id': 1, 'name': 'test'}], 'users')
        >>> print(sql)
        INSERT INTO users (id, name) VALUES (1, 'test');
    """
    
    def __init__(self, 
                 batch_size: int = 100,
                 include_header: bool = True,
                 quote_char: str = "'",
                 escape_char: str = "\\'"):
        """初始化 SQL 格式化器
        
        Args:
            batch_size: 批量插入的行数
            include_header: 是否包含注释头
            quote_char: 字符串引号字符
            escape_char: 转义字符
        """
        self.batch_size = batch_size
        self.include_header = include_header
        self.quote_char = quote_char
        self.escape_char = escape_char
    
    def format(self, data: List[Dict[str, Any]], table_name: str, 
               **kwargs) -> str:
        """格式化为 SQL INSERT 语句
        
        Args:
            data: 数据列表
            table_name: 表名
            
        Returns:
            SQL INSERT 语句字符串
        """
        if not data:
            return f"-- 表 {table_name} 无数据\n"
        
        lines = []
        
        # 添加注释头
        if self.include_header:
            lines.append(f"-- 表: {table_name}")
            lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"-- 数据行数: {len(data)}")
            lines.append("")
        
        # 获取字段列表
        columns = list(data[0].keys())
        columns_str = ', '.join(columns)
        
        # 批量生成 INSERT 语句
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            
            if len(batch) == 1:
                # 单行插入
                values = self._format_row(batch[0], columns)
                lines.append(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values});")
            else:
                # 批量插入
                lines.append(f"INSERT INTO {table_name} ({columns_str}) VALUES")
                value_rows = []
                for row in batch:
                    value_rows.append(f"  ({self._format_row(row, columns)})")
                lines.append(',\n'.join(value_rows) + ';')
            
            lines.append("")
        
        return '\n'.join(lines)
    
    def _format_row(self, row: Dict[str, Any], columns: List[str]) -> str:
        """格式化单行数据
        
        Args:
            row: 数据行
            columns: 字段列表
            
        Returns:
            格式化的值字符串
        """
        values = []
        for col in columns:
            value = row.get(col)
            values.append(self._format_value(value))
        return ', '.join(values)
    
    def _format_value(self, value: Any) -> str:
        """格式化单个值
        
        Args:
            value: 值
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return 'NULL'
        elif isinstance(value, bool):
            return '1' if value else '0'
        elif isinstance(value, (int, float, Decimal)):
            return str(value)
        elif isinstance(value, (datetime, date)):
            return f"{self.quote_char}{value}{self.quote_char}"
        elif isinstance(value, str):
            # 转义特殊字符
            escaped = value.replace(self.quote_char, self.escape_char)
            return f"{self.quote_char}{escaped}{self.quote_char}"
        elif isinstance(value, (dict, list)):
            # JSON 类型
            json_str = json.dumps(value, ensure_ascii=False)
            escaped = json_str.replace(self.quote_char, self.escape_char)
            return f"{self.quote_char}{escaped}{self.quote_char}"
        else:
            return f"{self.quote_char}{str(value)}{self.quote_char}"
    
    def save(self, data: List[Dict[str, Any]], table_name: str,
             output_path: Union[str, Path], **kwargs) -> Path:
        """保存为 SQL 文件
        
        Args:
            data: 数据列表
            table_name: 表名
            output_path: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        path = self.ensure_output_dir(output_path)
        sql_content = self.format(data, table_name, **kwargs)
        
        path.write_text(sql_content, encoding='utf-8')
        logger.info(f"SQL 文件已保存: {path}")
        
        return path


class CSVFormatter(BaseFormatter):
    """CSV 文件格式化器
    
    将数据格式化为 CSV 文件。
    
    Example:
        >>> formatter = CSVFormatter()
        >>> formatter.save([{'id': 1, 'name': 'test'}], 'users', 'output/users.csv')
    """
    
    def __init__(self,
                 delimiter: str = ',',
                 quotechar: str = '"',
                 include_header: bool = True,
                 encoding: str = 'utf-8-sig'):
        """初始化 CSV 格式化器
        
        Args:
            delimiter: 字段分隔符
            quotechar: 引号字符
            include_header: 是否包含表头
            encoding: 文件编码
        """
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.include_header = include_header
        self.encoding = encoding
    
    def format(self, data: List[Dict[str, Any]], table_name: str, 
               **kwargs) -> str:
        """格式化为 CSV 字符串
        
        Args:
            data: 数据列表
            table_name: 表名
            
        Returns:
            CSV 格式字符串
        """
        if not data:
            return ""
        
        import io
        output = io.StringIO()
        
        # 获取字段列表
        columns = list(data[0].keys())
        
        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            delimiter=self.delimiter,
            quotechar=self.quotechar,
            extrasaction='ignore'
        )
        
        # 写入表头
        if self.include_header:
            writer.writeheader()
        
        # 写入数据
        for row in data:
            # 处理特殊类型
            processed_row = {}
            for key, value in row.items():
                processed_row[key] = self._format_value(value)
            writer.writerow(processed_row)
        
        return output.getvalue()
    
    def _format_value(self, value: Any) -> str:
        """格式化单个值
        
        Args:
            value: 值
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return ''
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, (datetime, date)):
            return str(value)
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)
    
    def save(self, data: List[Dict[str, Any]], table_name: str,
             output_path: Union[str, Path], **kwargs) -> Path:
        """保存为 CSV 文件
        
        Args:
            data: 数据列表
            table_name: 表名
            output_path: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        path = self.ensure_output_dir(output_path)
        csv_content = self.format(data, table_name, **kwargs)
        
        path.write_text(csv_content, encoding=self.encoding)
        logger.info(f"CSV 文件已保存: {path}")
        
        return path


class JSONFormatter(BaseFormatter):
    """JSON 文件格式化器
    
    将数据格式化为 JSON 文件。
    
    Example:
        >>> formatter = JSONFormatter()
        >>> formatter.save([{'id': 1, 'name': 'test'}], 'users', 'output/users.json')
    """
    
    def __init__(self,
                 indent: int = 2,
                 ensure_ascii: bool = False,
                 include_metadata: bool = True):
        """初始化 JSON 格式化器
        
        Args:
            indent: 缩进空格数
            ensure_ascii: 是否确保 ASCII 编码
            include_metadata: 是否包含元数据
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.include_metadata = include_metadata
    
    def format(self, data: List[Dict[str, Any]], table_name: str,
               **kwargs) -> str:
        """格式化为 JSON 字符串
        
        Args:
            data: 数据列表
            table_name: 表名
            
        Returns:
            JSON 格式字符串
        """
        if self.include_metadata:
            output = {
                'table_name': table_name,
                'generated_at': datetime.now().isoformat(),
                'total_rows': len(data),
                'data': data
            }
        else:
            output = data
        
        return json.dumps(
            output,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=self._json_serializer
        )
    
    def _json_serializer(self, obj: Any) -> Any:
        """JSON 序列化器
        
        处理无法直接序列化的类型。
        
        Args:
            obj: 对象
            
        Returns:
            可序列化的值
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        else:
            return str(obj)
    
    def save(self, data: List[Dict[str, Any]], table_name: str,
             output_path: Union[str, Path], **kwargs) -> Path:
        """保存为 JSON 文件
        
        Args:
            data: 数据列表
            table_name: 表名
            output_path: 输出文件路径
            
        Returns:
            保存的文件路径
        """
        path = self.ensure_output_dir(output_path)
        json_content = self.format(data, table_name, **kwargs)
        
        path.write_text(json_content, encoding='utf-8')
        logger.info(f"JSON 文件已保存: {path}")
        
        return path


class FormatterFactory:
    """格式化器工厂
    
    根据格式类型创建对应的格式化器实例。
    """
    
    _formatters = {
        'sql': SQLFormatter,
        'csv': CSVFormatter,
        'json': JSONFormatter
    }
    
    @classmethod
    def create(cls, format_type: str, **kwargs) -> BaseFormatter:
        """创建格式化器实例
        
        Args:
            format_type: 格式类型 (sql/csv/json)
            **kwargs: 格式化器参数
            
        Returns:
            格式化器实例
            
        Raises:
            ValueError: 不支持的格式类型
        """
        format_type = format_type.lower()
        
        if format_type not in cls._formatters:
            raise ValueError(
                f"不支持的格式类型: {format_type}。"
                f"支持的格式: {', '.join(cls._formatters.keys())}"
            )
        
        formatter_class = cls._formatters[format_type]
        return formatter_class(**kwargs)
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """获取支持的格式列表
        
        Returns:
            格式列表
        """
        return list(cls._formatters.keys())
    
    @classmethod
    def register_formatter(cls, format_type: str, formatter_class: type) -> None:
        """注册自定义格式化器
        
        Args:
            format_type: 格式类型
            formatter_class: 格式化器类
        """
        cls._formatters[format_type.lower()] = formatter_class
        logger.info(f"已注册格式化器: {format_type}")


def format_data(data: List[Dict[str, Any]], 
                table_name: str,
                format_type: str = 'sql',
                **kwargs) -> str:
    """格式化数据的便捷函数
    
    Args:
        data: 数据列表
        table_name: 表名
        format_type: 格式类型
        **kwargs: 格式化器参数
        
    Returns:
        格式化后的字符串
    """
    formatter = FormatterFactory.create(format_type, **kwargs)
    return formatter.format(data, table_name, **kwargs)


def save_data(data: List[Dict[str, Any]],
              table_name: str,
              output_path: Union[str, Path],
              format_type: str = 'sql',
              **kwargs) -> Path:
    """保存数据的便捷函数
    
    Args:
        data: 数据列表
        table_name: 表名
        output_path: 输出文件路径
        format_type: 格式类型
        **kwargs: 格式化器参数
        
    Returns:
        保存的文件路径
    """
    formatter = FormatterFactory.create(format_type, **kwargs)
    return formatter.save(data, table_name, output_path, **kwargs)
