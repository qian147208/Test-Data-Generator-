# -*- coding: utf-8 -*-
"""配置文件处理模块

支持 YAML 和 JSON 格式的配置文件，包括:
- 数据库连接配置
- 数据生成规则配置
- 批量生成配置
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# 尝试导入 YAML 支持
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML 未安装，YAML 配置文件支持不可用。请使用: pip install pyyaml")


@dataclass
class DatabaseConnectionConfig:
    """数据库连接配置
    
    Attributes:
        type: 数据库类型 (mysql/postgresql/sqlite)
        host: 主机地址
        port: 端口号
        database: 数据库名称
        username: 用户名
        password: 密码
    """
    type: str = 'mysql'
    host: str = 'localhost'
    port: Optional[int] = None
    database: str = ''
    username: str = 'root'
    password: str = ''
    
    def __post_init__(self):
        """设置默认端口"""
        if self.port is None:
            default_ports = {
                'mysql': 3306,
                'postgresql': 5432,
                'sqlite': 0
            }
            self.port = default_ports.get(self.type, 3306)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConnectionConfig':
        """从字典创建"""
        return cls(
            type=data.get('type', 'mysql'),
            host=data.get('host', 'localhost'),
            port=data.get('port'),
            database=data.get('database', ''),
            username=data.get('username', 'root'),
            password=data.get('password', '')
        )


@dataclass
class OutputConfig:
    """输出配置
    
    Attributes:
        format: 输出格式 (sql/csv/json)
        path: 输出路径
    """
    format: str = 'sql'
    path: str = 'output/'
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OutputConfig':
        """从字典创建"""
        return cls(
            format=data.get('format', 'sql'),
            path=data.get('path', 'output/')
        )


@dataclass
class ColumnRuleConfig:
    """字段规则配置
    
    Attributes:
        name: 字段名
        strategy: 生成策略
        params: 生成器参数
        custom_values: 自定义值列表
    """
    name: str = ''
    strategy: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    custom_values: Optional[List[Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnRuleConfig':
        """从字典创建"""
        return cls(
            name=data.get('name', ''),
            strategy=data.get('strategy'),
            params=data.get('params', {}),
            custom_values=data.get('custom_values')
        )


@dataclass
class TableGenerationConfig:
    """表生成配置
    
    Attributes:
        name: 表名
        count: 生成数量
        strategy: 生成策略
        output: 输出配置
        columns: 字段规则列表
        seed: 随机种子
    """
    name: str = ''
    count: int = 10
    strategy: str = 'normal'
    output: Optional[OutputConfig] = None
    columns: List[ColumnRuleConfig] = field(default_factory=list)
    seed: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'name': self.name,
            'count': self.count,
            'strategy': self.strategy,
            'seed': self.seed
        }
        if self.output:
            result['output'] = self.output.to_dict()
        if self.columns:
            result['columns'] = [col.to_dict() for col in self.columns]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableGenerationConfig':
        """从字典创建"""
        output = None
        if 'output' in data:
            output = OutputConfig.from_dict(data['output'])
        
        columns = []
        if 'columns' in data:
            columns = [ColumnRuleConfig.from_dict(col) for col in data['columns']]
        
        return cls(
            name=data.get('name', ''),
            count=data.get('count', 10),
            strategy=data.get('strategy', 'normal'),
            output=output,
            columns=columns,
            seed=data.get('seed')
        )


@dataclass
class AppConfig:
    """应用配置
    
    Attributes:
        database: 数据库连接配置
        tables: 表生成配置列表
        default_output: 默认输出配置
        seed: 全局随机种子
    """
    database: Optional[DatabaseConnectionConfig] = None
    tables: List[TableGenerationConfig] = field(default_factory=list)
    default_output: OutputConfig = field(default_factory=OutputConfig)
    seed: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        if self.database:
            result['database'] = self.database.to_dict()
        if self.tables:
            result['tables'] = [table.to_dict() for table in self.tables]
        result['default_output'] = self.default_output.to_dict()
        if self.seed is not None:
            result['seed'] = self.seed
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """从字典创建"""
        database = None
        if 'database' in data:
            database = DatabaseConnectionConfig.from_dict(data['database'])
        
        tables = []
        if 'tables' in data:
            tables = [TableGenerationConfig.from_dict(t) for t in data['tables']]
        
        default_output = OutputConfig()
        if 'default_output' in data:
            default_output = OutputConfig.from_dict(data['default_output'])
        
        return cls(
            database=database,
            tables=tables,
            default_output=default_output,
            seed=data.get('seed')
        )


class ConfigHandler:
    """配置文件处理器
    
    支持读取和保存 YAML/JSON 格式的配置文件。
    
    Example:
        >>> handler = ConfigHandler()
        >>> config = handler.load('config.yaml')
        >>> handler.save(config, 'config_new.yaml')
    """
    
    def __init__(self):
        """初始化配置处理器"""
        self._config: Optional[AppConfig] = None
    
    def load(self, config_path: Union[str, Path]) -> AppConfig:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            AppConfig 对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        
        suffix = path.suffix.lower()
        
        if suffix in ('.yaml', '.yml'):
            if not YAML_AVAILABLE:
                raise ImportError(
                    "YAML 支持不可用。请安装 PyYAML: pip install pyyaml"
                )
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        elif suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            raise ValueError(
                f"不支持的配置文件格式: {suffix}。"
                f"支持的格式: .yaml, .yml, .json"
            )
        
        self._config = AppConfig.from_dict(data)
        logger.info(f"配置文件已加载: {path}")
        
        return self._config
    
    def save(self, config: AppConfig, output_path: Union[str, Path]) -> Path:
        """保存配置文件
        
        Args:
            config: 配置对象
            output_path: 输出路径
            
        Returns:
            保存的文件路径
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        suffix = path.suffix.lower()
        data = config.to_dict()
        
        if suffix in ('.yaml', '.yml'):
            if not YAML_AVAILABLE:
                raise ImportError(
                    "YAML 支持不可用。请安装 PyYAML: pip install pyyaml"
                )
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        elif suffix == '.json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(
                f"不支持的配置文件格式: {suffix}。"
                f"支持的格式: .yaml, .yml, .json"
            )
        
        logger.info(f"配置文件已保存: {path}")
        return path
    
    def get_config(self) -> Optional[AppConfig]:
        """获取当前配置
        
        Returns:
            AppConfig 对象，如果未加载则返回 None
        """
        return self._config
    
    def create_default_config(self) -> AppConfig:
        """创建默认配置
        
        Returns:
            默认配置对象
        """
        return AppConfig(
            database=DatabaseConnectionConfig(
                type='mysql',
                host='localhost',
                port=3306,
                database='test_db',
                username='root',
                password=''
            ),
            tables=[
                TableGenerationConfig(
                    name='users',
                    count=100,
                    strategy='normal',
                    output=OutputConfig(format='sql', path='output/users.sql')
                ),
                TableGenerationConfig(
                    name='orders',
                    count=50,
                    strategy='normal',
                    output=OutputConfig(format='csv', path='output/orders.csv')
                )
            ],
            default_output=OutputConfig(format='sql', path='output/'),
            seed=None
        )
    
    def create_template(self, output_path: Union[str, Path]) -> Path:
        """创建配置模板文件
        
        Args:
            output_path: 输出路径
            
        Returns:
            创建的文件路径
        """
        default_config = self.create_default_config()
        return self.save(default_config, output_path)


def load_config(config_path: Union[str, Path]) -> AppConfig:
    """加载配置文件的便捷函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        AppConfig 对象
    """
    handler = ConfigHandler()
    return handler.load(config_path)


def save_config(config: AppConfig, output_path: Union[str, Path]) -> Path:
    """保存配置文件的便捷函数
    
    Args:
        config: 配置对象
        output_path: 输出路径
        
    Returns:
        保存的文件路径
    """
    handler = ConfigHandler()
    return handler.save(config, output_path)


def create_config_template(output_path: Union[str, Path]) -> Path:
    """创建配置模板的便捷函数
    
    Args:
        output_path: 输出路径
        
    Returns:
        创建的文件路径
    """
    handler = ConfigHandler()
    return handler.create_template(output_path)
