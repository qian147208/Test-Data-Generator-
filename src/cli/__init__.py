# -*- coding: utf-8 -*-
"""命令行接口模块

提供命令行交互功能，包括:
- 数据库连接配置
- 表选择
- 数据生成参数设置
- 输出格式选择
"""

from .formatters import (
    BaseFormatter,
    SQLFormatter,
    CSVFormatter,
    JSONFormatter,
    FormatterFactory,
    format_data,
    save_data
)

from .config_handler import (
    DatabaseConnectionConfig,
    OutputConfig,
    ColumnRuleConfig,
    TableGenerationConfig,
    AppConfig,
    ConfigHandler,
    load_config,
    save_config,
    create_config_template
)

from .commands import (
    CommandContext,
    get_context,
    connect_command,
    list_tables_command,
    generate_command,
    batch_command,
    preview_command,
    get_available_strategies,
    get_available_formats
)

__all__ = [
    # 格式化器
    'BaseFormatter',
    'SQLFormatter',
    'CSVFormatter',
    'JSONFormatter',
    'FormatterFactory',
    'format_data',
    'save_data',
    
    # 配置处理
    'DatabaseConnectionConfig',
    'OutputConfig',
    'ColumnRuleConfig',
    'TableGenerationConfig',
    'AppConfig',
    'ConfigHandler',
    'load_config',
    'save_config',
    'create_config_template',
    
    # 命令
    'CommandContext',
    'get_context',
    'connect_command',
    'list_tables_command',
    'generate_command',
    'batch_command',
    'preview_command',
    'get_available_strategies',
    'get_available_formats'
]
