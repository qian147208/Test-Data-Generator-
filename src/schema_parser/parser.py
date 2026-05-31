# -*- coding: utf-8 -*-
"""表结构解析器

解析数据库表结构，支持 MySQL 和 PostgreSQL 数据库。
使用 SQLAlchemy 的 inspect 功能获取表信息。
"""

import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy import inspect, create_engine, Engine
from sqlalchemy.engine import Connection

from .models import (
    ColumnInfo, 
    ForeignKeyInfo, 
    IndexInfo, 
    TableSchema,
    CheckConstraintInfo
)
from .constraint_parser import ConstraintParser


class SchemaParser:
    """表结构解析器
    
    解析数据库表结构信息，包括字段、主键、外键、索引和约束等。
    支持 MySQL 和 PostgreSQL 数据库。
    
    Attributes:
        engine: SQLAlchemy 引擎
        connection: 数据库连接
        dialect: 数据库类型
        inspector: SQLAlchemy 检查器
        constraint_parser: 约束解析器
    """
    
    def __init__(self, engine_or_connection: Any):
        """初始化表结构解析器
        
        Args:
            engine_or_connection: SQLAlchemy Engine 或 Connection 对象
        """
        if isinstance(engine_or_connection, Engine):
            self.engine = engine_or_connection
            self.connection = None
        elif isinstance(engine_or_connection, Connection):
            self.engine = engine_or_connection.engine
            self.connection = engine_or_connection
        else:
            raise TypeError(
                "参数必须是 SQLAlchemy Engine 或 Connection 对象"
            )
        
        # 获取数据库方言
        self.dialect = self.engine.dialect.name
        
        # 创建 inspector
        if self.connection:
            self.inspector = inspect(self.connection)
        else:
            self.inspector = inspect(self.engine)
        
        # 创建约束解析器
        self.constraint_parser = ConstraintParser(self.dialect)
        
        # 缓存表结构
        self._schema_cache: Dict[str, TableSchema] = {}
        # 缓存表名列表
        self._table_names_cache: Dict[Optional[str], List[str]] = {}
        # 缓存依赖关系
        self._dependencies_cache: Dict[str, Dict[str, List[str]]] = {}
        # 缓存过期时间（秒）
        self._cache_ttl: int = 3600  # 1小时
        # 缓存时间戳
        self._cache_timestamps: Dict[str, float] = {}
    
    def get_table_names(self, schema: Optional[str] = None) -> List[str]:
        """获取所有表名
        
        Args:
            schema: Schema 名称（PostgreSQL 使用）
            
        Returns:
            表名列表
        """
        cache_key = self._get_cache_key("table_names", schema)
        
        if not self._is_cache_valid(cache_key) or schema not in self._table_names_cache:
            self._table_names_cache[schema] = self.inspector.get_table_names(schema=schema)
            self._update_cache_timestamp(cache_key)
        
        return self._table_names_cache[schema]
    
    def get_view_names(self, schema: Optional[str] = None) -> List[str]:
        """获取所有视图名
        
        Args:
            schema: Schema 名称（PostgreSQL 使用）
            
        Returns:
            视图名列表
        """
        return self.inspector.get_view_names(schema=schema)
    
    def parse_table(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        use_cache: bool = True
    ) -> TableSchema:
        """解析单个表结构
        
        Args:
            table_name: 表名
            schema: Schema 名称（PostgreSQL 使用）
            use_cache: 是否使用缓存
            
        Returns:
            TableSchema 对象
        """
        # 检查缓存
        cache_key = self._get_cache_key("table", schema, table_name)
        if use_cache and cache_key in self._schema_cache and self._is_cache_valid(cache_key):
            return self._schema_cache[cache_key]
        
        # 创建表结构对象
        table_schema = TableSchema(
            table_name=table_name,
            schema=schema
        )
        
        # 解析字段信息
        table_schema.columns = self._parse_columns(table_name, schema)
        
        # 解析主键
        pk_info = self.inspector.get_pk_constraint(table_name, schema=schema)
        table_schema.primary_keys = pk_info.get('constrained_columns', [])
        
        # 更新字段的主键标记
        for col in table_schema.columns:
            if col.name in table_schema.primary_keys:
                col.is_primary_key = True
        
        # 解析外键
        table_schema.foreign_keys = self._parse_foreign_keys(table_name, schema)
        
        # 解析索引
        table_schema.indexes = self._parse_indexes(table_name, schema, pk_info)
        
        # 解析 CHECK 约束
        table_schema.check_constraints = self._parse_check_constraints(
            table_name, schema
        )
        
        # 解析表注释
        table_schema.comment = self._parse_table_comment(table_name, schema)
        
        # 缓存结果
        if use_cache:
            self._schema_cache[cache_key] = table_schema
            self._update_cache_timestamp(cache_key)
        
        return table_schema
    
    async def parse_table_async(
        self, 
        table_name: str, 
        schema: Optional[str] = None,
        use_cache: bool = True
    ) -> TableSchema:
        """异步解析单个表结构
        
        Args:
            table_name: 表名
            schema: Schema 名称（PostgreSQL 使用）
            use_cache: 是否使用缓存
            
        Returns:
            TableSchema 对象
        """
        # 使用线程池执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.parse_table, 
            table_name, 
            schema, 
            use_cache
        )
    
    async def parse_all_tables_async(
        self, 
        schema: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, TableSchema]:
        """异步解析所有表结构
        
        Args:
            schema: Schema 名称（PostgreSQL 使用）
            use_cache: 是否使用缓存
            
        Returns:
            字典：表名 -> TableSchema
        """
        table_names = self.get_table_names(schema)
        tasks = []
        
        for table_name in table_names:
            task = self.parse_table_async(table_name, schema, use_cache)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return {table_names[i]: results[i] for i in range(len(table_names))}
    
    def parse_all_tables(
        self, 
        schema: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, TableSchema]:
        """解析所有表结构
        
        Args:
            schema: Schema 名称（PostgreSQL 使用）
            use_cache: 是否使用缓存
            
        Returns:
            字典：表名 -> TableSchema
        """
        result = {}
        table_names = self.get_table_names(schema)
        
        for table_name in table_names:
            result[table_name] = self.parse_table(
                table_name, schema, use_cache
            )
        
        return result
    
    def _parse_columns(
        self, 
        table_name: str, 
        schema: Optional[str]
    ) -> List[ColumnInfo]:
        """解析表的所有字段信息
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            ColumnInfo 列表
        """
        columns = []
        column_infos = self.inspector.get_columns(table_name, schema=schema)
        
        for col_info in column_infos:
            column = self._parse_single_column(col_info)
            columns.append(column)
        
        return columns
    
    def _parse_single_column(self, col_info: Dict[str, Any]) -> ColumnInfo:
        """解析单个字段信息
        
        Args:
            col_info: SQLAlchemy 返回的字段信息字典
            
        Returns:
            ColumnInfo 对象
        """
        name = col_info.get('name', '')
        
        # 解析数据类型
        data_type, length, precision, scale = self._parse_column_type(
            col_info.get('type')
        )
        
        # 解析约束
        is_nullable, is_unique, default, autoincrement = \
            self.constraint_parser.parse_column_constraints(col_info)
        
        # 解析注释
        comment = col_info.get('comment')
        
        # 创建 ColumnInfo 对象
        column = ColumnInfo(
            name=name,
            data_type=data_type,
            is_nullable=is_nullable,
            default=default,
            is_primary_key=False,  # 稍后更新
            is_unique=is_unique,
            length=length,
            precision=precision,
            scale=scale,
            comment=comment,
            autoincrement=autoincrement
        )
        
        return column
    
    def _parse_column_type(
        self, 
        column_type: Any
    ) -> tuple:
        """解析字段数据类型
        
        Args:
            column_type: SQLAlchemy 类型对象
            
        Returns:
            元组：(类型名称, 长度, 精度, 小数位数)
        """
        if column_type is None:
            return 'UNKNOWN', None, None, None
        
        # 获取类型字符串
        type_str = str(column_type).upper()
        type_class = type(column_type).__name__.upper()
        
        # 提取长度、精度、小数位数
        length = None
        precision = None
        scale = None
        
        # 获取类型属性
        if hasattr(column_type, 'length') and column_type.length:
            length = column_type.length
        
        if hasattr(column_type, 'precision') and column_type.precision:
            precision = column_type.precision
        
        if hasattr(column_type, 'scale') and column_type.scale:
            scale = column_type.scale
        
        # 规范化类型名称
        data_type = self._normalize_type_name(type_str, type_class)
        
        return data_type, length, precision, scale
    
    def _normalize_type_name(self, type_str: str, type_class: str) -> str:
        """规范化数据类型名称
        
        Args:
            type_str: 类型字符串
            type_class: 类型类名
            
        Returns:
            规范化的类型名称
        """
        # 整数类型
        integer_types = {
            'INTEGER', 'INT', 'SMALLINT', 'TINYINT', 'MEDIUMINT', 'BIGINT',
            'SMALLSERIAL', 'SERIAL', 'BIGSERIAL'
        }
        if any(t in type_str for t in integer_types) or type_class in integer_types:
            if 'BIG' in type_str or type_class == 'BIGINT':
                return 'BIGINT'
            elif 'SMALL' in type_str or type_class == 'SMALLINT':
                return 'SMALLINT'
            elif 'TINY' in type_str or type_class == 'TINYINT':
                return 'TINYINT'
            elif 'MEDIUM' in type_str:
                return 'MEDIUMINT'
            return 'INTEGER'
        
        # 浮点数类型
        float_types = {'FLOAT', 'DOUBLE', 'REAL', 'DOUBLE PRECISION'}
        if any(t in type_str for t in float_types) or type_class in float_types:
            if 'DOUBLE' in type_str:
                return 'DOUBLE'
            elif 'REAL' in type_str:
                return 'REAL'
            return 'FLOAT'
        
        # 定点数类型
        if 'DECIMAL' in type_str or 'NUMERIC' in type_str or \
           type_class in {'DECIMAL', 'NUMERIC'}:
            return 'DECIMAL'
        
        # 字符串类型
        string_types = {
            'VARCHAR', 'CHAR', 'CHARACTER VARYING', 'CHARACTER',
            'NVARCHAR', 'NCHAR', 'TEXT', 'LONGTEXT', 'MEDIUMTEXT', 'TINYTEXT'
        }
        if any(t in type_str for t in string_types) or type_class in string_types:
            if 'LONGTEXT' in type_str:
                return 'LONGTEXT'
            elif 'MEDIUMTEXT' in type_str:
                return 'MEDIUMTEXT'
            elif 'TINYTEXT' in type_str:
                return 'TINYTEXT'
            elif 'TEXT' in type_str or type_class == 'TEXT':
                return 'TEXT'
            elif 'NVARCHAR' in type_str or 'NCHAR' in type_str:
                return type_str.split('(')[0]
            elif 'CHARACTER VARYING' in type_str or type_class == 'VARCHAR':
                return 'VARCHAR'
            elif 'CHAR' in type_str:
                return 'CHAR'
            return 'VARCHAR'
        
        # 日期时间类型
        datetime_types = {
            'DATE', 'TIME', 'DATETIME', 'TIMESTAMP', 'TIMESTAMPTZ',
            'TIMESTAMP WITH TIME ZONE', 'YEAR'
        }
        if any(t in type_str for t in datetime_types) or type_class in datetime_types:
            if 'TIMESTAMPTZ' in type_str or 'TIMESTAMP WITH TIME ZONE' in type_str:
                return 'TIMESTAMPTZ'
            elif 'TIMESTAMP' in type_str:
                return 'TIMESTAMP'
            elif 'DATETIME' in type_str:
                return 'DATETIME'
            elif 'TIME' in type_str:
                return 'TIME'
            elif 'DATE' in type_str:
                return 'DATE'
            elif 'YEAR' in type_str:
                return 'YEAR'
        
        # 布尔类型
        if 'BOOL' in type_str or type_class == 'BOOLEAN':
            return 'BOOLEAN'
        
        # JSON 类型
        json_types = {'JSON', 'JSONB'}
        if any(t in type_str for t in json_types) or type_class in json_types:
            if 'JSONB' in type_str:
                return 'JSONB'
            return 'JSON'
        
        # 二进制类型
        binary_types = {
            'BLOB', 'BINARY', 'VARBINARY', 'LONGBLOB', 'MEDIUMBLOB',
            'TINYBLOB', 'BYTEA'
        }
        if any(t in type_str for t in binary_types) or type_class in binary_types:
            if 'LONGBLOB' in type_str:
                return 'LONGBLOB'
            elif 'MEDIUMBLOB' in type_str:
                return 'MEDIUMBLOB'
            elif 'TINYBLOB' in type_str:
                return 'TINYBLOB'
            elif 'BYTEA' in type_str:
                return 'BYTEA'
            elif 'VARBINARY' in type_str:
                return 'VARBINARY'
            elif 'BINARY' in type_str:
                return 'BINARY'
            return 'BLOB'
        
        # 枚举类型
        if 'ENUM' in type_str or type_class == 'ENUM':
            return 'ENUM'
        
        # UUID 类型
        if 'UUID' in type_str or type_class == 'UUID':
            return 'UUID'
        
        # 数组类型（PostgreSQL）
        if 'ARRAY' in type_str or type_class == 'ARRAY':
            return 'ARRAY'
        
        # 其他类型，返回类型类名
        return type_class if type_class else type_str.split('(')[0]
    
    def _parse_primary_keys(
        self, 
        table_name: str, 
        schema: Optional[str]
    ) -> List[str]:
        """解析表的主键
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            主键字段名列表
        """
        pk_info = self.inspector.get_pk_constraint(table_name, schema=schema)
        return pk_info.get('constrained_columns', [])
    
    def _parse_foreign_keys(
        self, 
        table_name: str, 
        schema: Optional[str]
    ) -> List[ForeignKeyInfo]:
        """解析表的外键
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            ForeignKeyInfo 列表
        """
        foreign_keys = []
        fk_infos = self.inspector.get_foreign_keys(table_name, schema=schema)
        
        for fk_info in fk_infos:
            fk = ForeignKeyInfo(
                name=fk_info.get('name', ''),
                constrained_table=table_name,
                constrained_columns=fk_info.get('constrained_columns', []),
                referred_table=fk_info.get('referred_table', ''),
                referred_columns=fk_info.get('referred_columns', []),
                on_update=fk_info.get('onupdate'),
                on_delete=fk_info.get('ondelete')
            )
            foreign_keys.append(fk)
        
        return foreign_keys
    
    def _parse_indexes(
        self, 
        table_name: str, 
        schema: Optional[str],
        pk_info: Optional[Dict] = None
    ) -> List[IndexInfo]:
        """解析表的索引
        
        Args:
            table_name: 表名
            schema: Schema 名称
            pk_info: 主键信息（避免重复查询）
            
        Returns:
            IndexInfo 列表
        """
        indexes = []
        idx_infos = self.inspector.get_indexes(table_name, schema=schema)
        
        for idx_info in idx_infos:
            idx = IndexInfo(
                name=idx_info.get('name', ''),
                table_name=table_name,
                columns=idx_info.get('column_names', []),
                is_unique=idx_info.get('unique', False),
                is_primary=False,  # 主键索引单独处理
                index_type=idx_info.get('type')
            )
            indexes.append(idx)
        
        # 添加主键索引
        if not pk_info:
            pk_info = self.inspector.get_pk_constraint(table_name, schema=schema)
        
        if pk_info.get('constrained_columns'):
            pk_index = IndexInfo(
                name=pk_info.get('name', 'PRIMARY'),
                table_name=table_name,
                columns=pk_info.get('constrained_columns', []),
                is_unique=True,
                is_primary=True
            )
            indexes.append(pk_index)
        
        return indexes
    
    def _parse_check_constraints(
        self, 
        table_name: str, 
        schema: Optional[str]
    ) -> List[CheckConstraintInfo]:
        """解析表的 CHECK 约束
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            CheckConstraintInfo 列表
        """
        check_constraints = []
        
        # 尝试获取 CHECK 约束
        # 注意：不是所有数据库都支持通过 inspector 获取 CHECK 约束
        try:
            if hasattr(self.inspector, 'get_check_constraints'):
                cc_infos = self.inspector.get_check_constraints(
                    table_name, schema=schema
                )
                for cc_info in cc_infos:
                    cc = self.constraint_parser.parse_check_constraint(
                        cc_info, table_name
                    )
                    if cc:
                        check_constraints.append(cc)
        except Exception:
            # 某些数据库或版本可能不支持
            pass
        
        return check_constraints
    
    def _parse_table_comment(
        self, 
        table_name: str, 
        schema: Optional[str]
    ) -> Optional[str]:
        """解析表注释
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            表注释
        """
        try:
            # 尝试获取表注释
            if hasattr(self.inspector, 'get_table_comment'):
                comment_info = self.inspector.get_table_comment(
                    table_name, schema=schema
                )
                return comment_info.get('text')
        except Exception:
            pass
        
        return None
    
    def _get_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键
        
        Args:
            prefix: 缓存键前缀
            *args: 缓存键参数
            
        Returns:
            缓存键字符串
        """
        key_parts = [prefix]
        for arg in args:
            if arg is not None:
                key_parts.append(str(arg))
        return ":".join(key_parts)
    
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效
        
        Args:
            key: 缓存键
            
        Returns:
            是否有效
        """
        import time
        timestamp = self._cache_timestamps.get(key)
        if timestamp is None:
            return False
        return time.time() - timestamp < self._cache_ttl
    
    def _update_cache_timestamp(self, key: str):
        """更新缓存时间戳
        
        Args:
            key: 缓存键
        """
        import time
        self._cache_timestamps[key] = time.time()
    
    def clear_cache(self):
        """清除缓存"""
        self._schema_cache.clear()
        self._table_names_cache.clear()
        self._dependencies_cache.clear()
        self._cache_timestamps.clear()
    
    def set_cache_ttl(self, ttl: int):
        """设置缓存过期时间
        
        Args:
            ttl: 过期时间（秒）
        """
        self._cache_ttl = ttl
    
    def get_cache_ttl(self) -> int:
        """获取缓存过期时间
        
        Returns:
            过期时间（秒）
        """
        return self._cache_ttl
    
    def get_table_dependencies(
        self, 
        table_name: str, 
        schema: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """获取表的依赖关系
        
        分析表的外键关系，返回该表依赖的其他表和依赖该表的其他表。
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            字典：{
                'depends_on': [该表依赖的其他表名列表],
                'depended_by': [依赖该表的其他表名列表]
            }
        """
        depends_on = set()
        depended_by = set()
        
        # 获取当前表的外键（该表依赖的其他表）
        table_schema = self.parse_table(table_name, schema)
        for fk in table_schema.foreign_keys:
            depends_on.add(fk.referred_table)
        
        # 遍历所有表，找出依赖该表的其他表
        # 优化：使用已缓存的表结构，避免重复解析
        all_tables = self.get_table_names(schema)
        for other_table in all_tables:
            if other_table == table_name:
                continue
            
            # 使用缓存的表结构
            other_schema = self.parse_table(other_table, schema)
            for fk in other_schema.foreign_keys:
                if fk.referred_table == table_name:
                    depended_by.add(other_table)
        
        return {
            'depends_on': sorted(list(depends_on)),
            'depended_by': sorted(list(depended_by))
        }
    
    def get_all_dependencies(self, schema: Optional[str] = None) -> Dict[str, Dict[str, List[str]]]:
        """获取所有表的依赖关系
        
        Args:
            schema: Schema 名称
            
        Returns:
            字典：{表名: {'depends_on': [...], 'depended_by': [...]}}
        """
        dependencies = {}
        table_names = self.get_table_names(schema)
        
        # 先解析所有表结构（利用缓存）
        all_table_schemas = self.parse_all_tables(schema)
        
        # 构建外键映射，避免重复遍历
        foreign_key_map = {}
        for tbl_name, tbl_schema in all_table_schemas.items():
            for fk in tbl_schema.foreign_keys:
                if fk.referred_table not in foreign_key_map:
                    foreign_key_map[fk.referred_table] = []
                foreign_key_map[fk.referred_table].append(tbl_name)
        
        # 生成依赖关系
        for table_name in table_names:
            table_schema = all_table_schemas[table_name]
            
            # 依赖的表
            depends_on = set()
            for fk in table_schema.foreign_keys:
                depends_on.add(fk.referred_table)
            
            # 被依赖的表
            depended_by = set(foreign_key_map.get(table_name, []))
            
            dependencies[table_name] = {
                'depends_on': sorted(list(depends_on)),
                'depended_by': sorted(list(depended_by))
            }
        
        return dependencies
    
    async def get_table_dependencies_async(
        self, 
        table_name: str, 
        schema: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """异步获取表的依赖关系
        
        Args:
            table_name: 表名
            schema: Schema 名称
            
        Returns:
            字典：{
                'depends_on': [该表依赖的表名列表],
                'depended_by': [依赖该表的其他表名列表]
            }
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.get_table_dependencies, 
            table_name, 
            schema
        )
    
    def get_all_dependencies(self, schema: Optional[str] = None) -> Dict[str, Dict[str, List[str]]]:
        """获取所有表的依赖关系
        
        Args:
            schema: Schema 名称
            
        Returns:
            字典：{表名: {'depends_on': [...], 'depended_by': [...]}}
        """
        dependencies = {}
        table_names = self.get_table_names(schema)
        
        for table_name in table_names:
            dependencies[table_name] = self.get_table_dependencies(
                table_name, schema
            )
        
        return dependencies
    
    async def get_all_dependencies_async(self, schema: Optional[str] = None) -> Dict[str, Dict[str, List[str]]]:
        """异步获取所有表的依赖关系
        
        Args:
            schema: Schema 名称
            
        Returns:
            字典：{表名: {'depends_on': [...], 'depended_by': [...]}}
        """
        table_names = self.get_table_names(schema)
        tasks = []
        
        for table_name in table_names:
            task = self.get_table_dependencies_async(table_name, schema)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return {table_names[i]: results[i] for i in range(len(table_names))}
