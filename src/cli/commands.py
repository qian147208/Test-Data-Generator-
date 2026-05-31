# -*- coding: utf-8 -*-
"""命令实现模块

实现所有命令行命令的具体逻辑，包括:
- connect_command: 连接数据库
- list_tables_command: 列出所有表
- generate_command: 生成测试数据
- batch_command: 批量生成
- preview_command: 预览数据
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..db_connector import DatabaseConnector, DatabaseConfig
from ..schema_parser import SchemaParser, TableSchema
from ..data_generator import (
    DataEngine, 
    DataEngineBuilder,
    ColumnRule,
    GenerationResult,
    StrategyFactory
)
from ..relation_handler import RelationManager, GenerationPlan
from .formatters import FormatterFactory, save_data
from .config_handler import (
    AppConfig, 
    TableGenerationConfig,
    ConfigHandler
)

logger = logging.getLogger(__name__)


class CommandContext:
    """命令上下文
    
    存储命令执行过程中的共享状态。
    """
    
    def __init__(self):
        """初始化命令上下文"""
        self.connector: Optional[DatabaseConnector] = None
        self.parser: Optional[SchemaParser] = None
        self.engine: Optional[DataEngine] = None
        self.relation_manager: Optional[RelationManager] = None
        self._schemas: Dict[str, TableSchema] = {}
    
    def set_connector(self, connector: DatabaseConnector) -> None:
        """设置数据库连接器"""
        self.connector = connector
        self.parser = SchemaParser(connector.get_engine())
    
    def set_engine(self, engine: DataEngine) -> None:
        """设置数据引擎"""
        self.engine = engine
    
    def set_relation_manager(self, manager: RelationManager) -> None:
        """设置关联管理器"""
        self.relation_manager = manager
    
    def get_schema(self, table_name: str) -> Optional[TableSchema]:
        """获取表结构"""
        return self._schemas.get(table_name)
    
    def load_schemas(self, table_names: Optional[List[str]] = None) -> Dict[str, TableSchema]:
        """加载表结构
        
        Args:
            table_names: 表名列表，如果为 None 则加载所有表
            
        Returns:
            表结构字典
        """
        if self.parser is None:
            raise RuntimeError("数据库连接器未初始化")
        
        if table_names:
            for name in table_names:
                if name not in self._schemas:
                    self._schemas[name] = self.parser.parse_table(name)
        else:
            self._schemas = self.parser.parse_all_tables()
        
        return self._schemas
    
    def clear(self) -> None:
        """清除上下文"""
        if self.connector:
            self.connector.disconnect()
        self.connector = None
        self.parser = None
        self.engine = None
        self.relation_manager = None
        self._schemas.clear()


# 全局上下文
_context = CommandContext()


def get_context() -> CommandContext:
    """获取全局命令上下文"""
    return _context


def connect_command(
    host: str = 'localhost',
    port: Optional[int] = None,
    database: str = '',
    username: str = 'root',
    password: str = '',
    db_type: str = 'mysql'
) -> Dict[str, Any]:
    """连接数据库命令
    
    Args:
        host: 数据库主机地址
        port: 数据库端口
        database: 数据库名称
        username: 用户名
        password: 密码
        db_type: 数据库类型
        
    Returns:
        连接结果信息
    """
    result = {
        'success': False,
        'message': '',
        'database': database,
        'type': db_type
    }
    
    try:
        # 创建配置
        config = DatabaseConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            db_type=db_type
        )
        
        # 创建连接器
        connector = DatabaseConnector(config)
        connector.connect()
        
        # 设置上下文
        _context.set_connector(connector)
        
        result['success'] = True
        result['message'] = f"成功连接到 {db_type} 数据库: {database}"
        result['pool_status'] = connector.pool_status
        
        logger.info(result['message'])
        
    except Exception as e:
        result['message'] = f"连接失败: {str(e)}"
        logger.error(result['message'])
    
    return result


def list_tables_command(
    table_name: Optional[str] = None,
    show_details: bool = False
) -> Dict[str, Any]:
    """列出数据库表命令
    
    Args:
        table_name: 指定表名，如果为 None 则列出所有表
        show_details: 是否显示详细信息
        
    Returns:
        表信息
    """
    result = {
        'success': False,
        'message': '',
        'tables': [],
        'table_details': None
    }
    
    try:
        parser = _context.parser
        if parser is None:
            result['message'] = "数据库未连接，请先执行 connect 命令"
            return result
        
        if table_name:
            # 获取指定表信息
            schema = parser.parse_table(table_name)
            result['tables'] = [table_name]
            result['table_details'] = schema.to_dict()
            
            if show_details:
                # 获取依赖关系
                deps = parser.get_table_dependencies(table_name)
                result['dependencies'] = deps
        else:
            # 获取所有表
            table_names = parser.get_table_names()
            result['tables'] = table_names
            
            if show_details:
                # 加载所有表结构
                schemas = _context.load_schemas(table_names)
                result['table_details'] = {
                    name: {
                        'columns_count': len(schema.columns),
                        'primary_keys': schema.primary_keys,
                        'foreign_keys_count': len(schema.foreign_keys),
                        'indexes_count': len(schema.indexes)
                    }
                    for name, schema in schemas.items()
                }
        
        result['success'] = True
        result['message'] = f"共找到 {len(result['tables'])} 个表"
        
    except Exception as e:
        result['message'] = f"获取表信息失败: {str(e)}"
        logger.error(result['message'])
    
    return result


def generate_command(
    table_name: str,
    count: int = 10,
    strategy: str = 'normal',
    output_path: Optional[Union[str, Path]] = None,
    output_format: str = 'sql',
    seed: Optional[int] = None,
    column_rules: Optional[List[Dict[str, Any]]] = None,
    insert_to_db: bool = False
) -> Dict[str, Any]:
    """生成测试数据命令
    
    Args:
        table_name: 表名
        count: 生成数量
        strategy: 生成策略
        output_path: 输出路径
        output_format: 输出格式
        seed: 随机种子
        column_rules: 字段规则列表
        insert_to_db: 是否直接插入数据库
        
    Returns:
        生成结果
    """
    result = {
        'success': False,
        'message': '',
        'table_name': table_name,
        'count': count,
        'strategy': strategy,
        'data': [],
        'output_file': None
    }
    
    try:
        # 检查连接
        if _context.parser is None:
            result['message'] = "数据库未连接，请先执行 connect 命令"
            return result
        
        # 加载表结构
        schema = _context.load_schemas([table_name]).get(table_name)
        if schema is None:
            result['message'] = f"表 '{table_name}' 不存在"
            return result
        
        # 创建数据引擎
        engine_builder = DataEngineBuilder()
        if seed is not None:
            import random
            random.seed(seed)
        
        # 添加字段规则
        if column_rules:
            for rule_dict in column_rules:
                rule = ColumnRule(
                    column_name=rule_dict.get('name', ''),
                    strategy=rule_dict.get('strategy'),
                    generator_params=rule_dict.get('params', {}),
                    custom_values=rule_dict.get('custom_values')
                )
                engine_builder.with_column_rule(rule)
        
        engine = engine_builder.build()
        _context.set_engine(engine)
        
        # 生成数据
        generation_result = engine.generate_for_table(
            table_schema=schema,
            strategy=strategy,
            count=count
        )
        
        result['data'] = generation_result.data
        result['warnings'] = generation_result.warnings
        
        # 输出或保存
        if output_path:
            # 保存到文件
            saved_path = save_data(
                data=generation_result.data,
                table_name=table_name,
                output_path=output_path,
                format_type=output_format
            )
            result['output_file'] = str(saved_path)
            result['message'] = f"成功生成 {count} 条数据，已保存到: {saved_path}"
        elif insert_to_db:
            # 插入数据库
            _insert_data_to_db(table_name, generation_result.data, schema)
            result['message'] = f"成功生成并插入 {count} 条数据到表 {table_name}"
        else:
            result['message'] = f"成功生成 {count} 条数据"
        
        result['success'] = True
        
    except Exception as e:
        result['message'] = f"生成数据失败: {str(e)}"
        logger.error(result['message'], exc_info=True)
    
    return result


def batch_command(
    config_path: Union[str, Path],
    insert_to_db: bool = False
) -> Dict[str, Any]:
    """批量生成命令
    
    从配置文件读取配置并批量生成数据。
    
    Args:
        config_path: 配置文件路径
        insert_to_db: 是否直接插入数据库
        
    Returns:
        批量生成结果
    """
    result = {
        'success': False,
        'message': '',
        'tables': [],
        'total_records': 0,
        'output_files': []
    }
    
    try:
        # 加载配置
        handler = ConfigHandler()
        config = handler.load(config_path)
        
        # 检查数据库连接配置
        if config.database is None:
            result['message'] = "配置文件中缺少数据库连接配置"
            return result
        
        # 连接数据库
        db_config = config.database
        connect_result = connect_command(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            username=db_config.username,
            password=db_config.password,
            db_type=db_config.type
        )
        
        if not connect_result['success']:
            result['message'] = f"数据库连接失败: {connect_result['message']}"
            return result
        
        # 设置全局随机种子
        if config.seed is not None:
            import random
            random.seed(config.seed)
        
        # 加载所有表结构
        table_names = [t.name for t in config.tables]
        schemas = _context.load_schemas(table_names)
        
        # 初始化关联管理器
        relation_manager = RelationManager(seed=config.seed)
        relation_manager.plan_generation_order(schemas)
        _context.set_relation_manager(relation_manager)
        
        # 按顺序生成数据
        plan = relation_manager.get_generation_plan()
        
        for table_config in config.tables:
            table_name = table_config.name
            schema = schemas.get(table_name)
            
            if schema is None:
                logger.warning(f"表 '{table_name}' 不存在，跳过")
                continue
            
            # 准备字段规则
            column_rules = None
            if table_config.columns:
                column_rules = [col.to_dict() for col in table_config.columns]
            
            # 确定输出路径
            output_path = None
            output_format = config.default_output.format
            if table_config.output:
                output_path = table_config.output.path
                output_format = table_config.output.format
            elif config.default_output.path:
                output_path = Path(config.default_output.path) / f"{table_name}.{output_format}"
            
            # 生成数据
            gen_result = generate_command(
                table_name=table_name,
                count=table_config.count,
                strategy=table_config.strategy,
                output_path=output_path,
                output_format=output_format,
                seed=table_config.seed or config.seed,
                column_rules=column_rules,
                insert_to_db=insert_to_db
            )
            
            table_result = {
                'table_name': table_name,
                'success': gen_result['success'],
                'count': table_config.count,
                'output_file': gen_result.get('output_file'),
                'message': gen_result['message']
            }
            
            result['tables'].append(table_result)
            result['total_records'] += table_config.count
            
            if gen_result.get('output_file'):
                result['output_files'].append(gen_result['output_file'])
        
        result['success'] = True
        result['message'] = f"批量生成完成，共处理 {len(result['tables'])} 个表，生成 {result['total_records']} 条记录"
        
    except Exception as e:
        result['message'] = f"批量生成失败: {str(e)}"
        logger.error(result['message'], exc_info=True)
    
    return result


def preview_command(
    table_name: str,
    strategy: str = 'normal',
    count: int = 5,
    column_name: Optional[str] = None
) -> Dict[str, Any]:
    """预览数据命令
    
    生成少量数据用于预览。
    
    Args:
        table_name: 表名
        strategy: 生成策略
        count: 预览数量
        column_name: 指定字段名（可选）
        
    Returns:
        预览结果
    """
    result = {
        'success': False,
        'message': '',
        'table_name': table_name,
        'strategy': strategy,
        'preview_data': []
    }
    
    try:
        # 检查连接
        if _context.parser is None:
            result['message'] = "数据库未连接，请先执行 connect 命令"
            return result
        
        # 加载表结构
        schema = _context.load_schemas([table_name]).get(table_name)
        if schema is None:
            result['message'] = f"表 '{table_name}' 不存在"
            return result
        
        # 创建数据引擎
        engine = DataEngineBuilder().build()
        
        if column_name:
            # 预览单个字段
            column = schema.get_column(column_name)
            if column is None:
                result['message'] = f"字段 '{column_name}' 不存在"
                return result
            
            preview = engine.preview_column(column, strategy, count)
            result['preview_data'] = [preview]
            result['message'] = f"字段 '{column_name}' 预览"
        else:
            # 预览整个表
            for column in schema.columns:
                preview = engine.preview_column(column, strategy, count)
                result['preview_data'].append(preview)
            
            result['message'] = f"表 '{table_name}' 所有字段预览"
        
        result['success'] = True
        
    except Exception as e:
        result['message'] = f"预览失败: {str(e)}"
        logger.error(result['message'])
    
    return result


def _insert_data_to_db(
    table_name: str,
    data: List[Dict[str, Any]],
    schema: TableSchema
) -> None:
    """将数据插入数据库
    
    Args:
        table_name: 表名
        data: 数据列表
        schema: 表结构
    """
    from sqlalchemy import Table, MetaData
    from sqlalchemy.engine import Engine
    
    engine = _context.connector.get_engine()
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    table = metadata.tables[table_name]
    
    with engine.begin() as conn:
        for row in data:
            # 过滤掉 None 值（让数据库使用默认值）
            filtered_row = {k: v for k, v in row.items() if v is not None}
            conn.execute(table.insert().values(**filtered_row))
    
    logger.info(f"已插入 {len(data)} 条数据到表 {table_name}")


def get_available_strategies() -> List[str]:
    """获取可用的生成策略列表"""
    return StrategyFactory.list_strategies()


def get_available_formats() -> List[str]:
    """获取可用的输出格式列表"""
    return FormatterFactory.get_supported_formats()
