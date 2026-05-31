#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试数据生成工具

一个用于从数据库表结构生成测试数据的命令行工具。
支持 PostgreSQL、MySQL、SQLite 等多种数据库。

使用方法:
    python main.py --help
    python main.py init
    python main.py connect -d mydb -u root --pwd password
    python main.py list-tables -d mydb
    python main.py generate -d mydb -t users -c 100
    python main.py batch -c config.yaml
    python main.py preview -d mydb -t users
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 尝试导入模块
try:
    from src.cli.commands import (
        connect_command,
        list_tables_command,
        generate_command,
        batch_command,
        preview_command,
        get_available_strategies,
        get_available_formats,
        get_context
    )
    from src.cli.config_handler import create_config_template
    from src.cli.formatters import FormatterFactory
    MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"部分模块导入失败: {e}")
    MODULES_AVAILABLE = False


# 数据库连接状态（用于跨命令共享）
_db_connection = {
    'connected': False,
    'config': None
}


def check_modules():
    """检查模块是否可用"""
    if not MODULES_AVAILABLE:
        click.secho("错误: 必要模块未正确加载，请检查安装", fg='red')
        sys.exit(1)


@click.group()
@click.version_option(version='1.0.0', prog_name='test-data-generator')
@click.option('--verbose', '-v', is_flag=True, help='显示详细输出')
def cli(verbose: bool):
    """测试数据生成工具

    从数据库表结构自动生成测试数据，支持多种数据库类型。

    \b
    支持的数据库:
      - MySQL
      - PostgreSQL
      - SQLite

    \b
    快速开始:
      1. 初始化配置文件: python main.py init
      2. 编辑配置文件 config.yaml
      3. 批量生成数据: python main.py batch -c config.yaml
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option('--output', '-o', 'output_path', default='config.yaml',
              type=click.Path(), help='配置文件输出路径')
def init(output_path: str):
    """初始化配置文件

    在指定目录生成默认配置文件模板。

    \b
    示例:
      python main.py init
      python main.py init -o my_config.yaml
    """
    check_modules()
    
    output = Path(output_path)
    
    if output.exists():
        if not click.confirm(f"配置文件 '{output}' 已存在，是否覆盖？"):
            click.secho("操作已取消", fg='yellow')
            return
    
    try:
        create_config_template(output)
        click.secho(f"配置文件已创建: {output}", fg='green')
        click.echo("\n请编辑配置文件，设置数据库连接和生成规则。")
    except Exception as e:
        click.secho(f"创建配置文件失败: {e}", fg='red')


@cli.command()
@click.option('--host', '-h', default='localhost', help='数据库主机地址')
@click.option('--port', '-p', default=None, type=int, help='数据库端口')
@click.option('--database', '-d', required=True, help='数据库名称')
@click.option('--user', '-u', default='root', help='数据库用户名')
@click.option('--password', '--pwd', default='', help='数据库密码')
@click.option('--type', '-t', 'db_type', default='mysql',
              type=click.Choice(['mysql', 'postgresql', 'sqlite']),
              help='数据库类型')
def connect(host: str, port: Optional[int], database: str, 
            user: str, password: str, db_type: str):
    """连接数据库并验证连接

    \b
    示例:
      python main.py connect -d mydb -u root --pwd password
      python main.py connect -d mydb -t postgresql -h localhost -p 5432
      python main.py connect -d /path/to/db.sqlite -t sqlite
    """
    check_modules()
    
    click.echo(f"正在连接 {db_type} 数据库: {database}")
    click.echo(f"主机: {host}")
    if port:
        click.echo(f"端口: {port}")
    click.echo(f"用户: {user}")
    
    result = connect_command(
        host=host,
        port=port,
        database=database,
        username=user,
        password=password,
        db_type=db_type
    )
    
    if result['success']:
        click.secho(f"\n{result['message']}", fg='green')
        
        # 显示连接池状态
        if 'pool_status' in result:
            pool = result['pool_status']
            click.echo(f"\n连接池状态:")
            click.echo(f"  状态: {pool.get('status', 'unknown')}")
            click.echo(f"  池大小: {pool.get('pool_size', 0)}")
            click.echo(f"  已检出: {pool.get('checked_out', 0)}")
        
        # 保存连接状态
        _db_connection['connected'] = True
        _db_connection['config'] = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'db_type': db_type
        }
    else:
        click.secho(f"\n错误: {result['message']}", fg='red')
        sys.exit(1)


@cli.command('list-tables')
@click.option('--database', '-d', required=False, help='数据库名称（如果未连接）')
@click.option('--table', '-t', 'table_name', default=None, help='指定表名（可选）')
@click.option('--details', is_flag=True, help='显示详细信息')
def list_tables(database: Optional[str], table_name: Optional[str], details: bool):
    """列出数据库中的所有表或指定表的详细信息

    \b
    示例:
      python main.py list-tables
      python main.py list-tables -t users
      python main.py list-tables --details
    """
    check_modules()
    
    # 检查是否已连接
    context = get_context()
    if context.parser is None:
        click.secho("错误: 数据库未连接，请先执行 connect 命令", fg='red')
        sys.exit(1)
    
    result = list_tables_command(
        table_name=table_name,
        show_details=details
    )
    
    if result['success']:
        if table_name:
            click.secho(f"\n表 '{table_name}' 的结构信息:", fg='cyan', bold=True)
            table_details = result.get('table_details', {})
            
            # 显示字段信息
            columns = table_details.get('columns', [])
            if columns:
                click.echo("\n字段:")
                click.echo(f"  {'字段名':<20} {'类型':<15} {'可空':<6} {'主键':<6} {'唯一':<6}")
                click.echo("  " + "-" * 60)
                for col in columns:
                    click.echo(
                        f"  {col['name']:<20} {col['data_type']:<15} "
                        f"{'是' if col['is_nullable'] else '否':<6} "
                        f"{'是' if col['is_primary_key'] else '否':<6} "
                        f"{'是' if col['is_unique'] else '否':<6}"
                    )
            
            # 显示主键
            pks = table_details.get('primary_keys', [])
            if pks:
                click.echo(f"\n主键: {', '.join(pks)}")
            
            # 显示外键
            fks = table_details.get('foreign_keys', [])
            if fks:
                click.echo("\n外键:")
                for fk in fks:
                    cols = ', '.join(fk['constrained_columns'])
                    ref_cols = ', '.join(fk['referred_columns'])
                    click.echo(f"  {cols} -> {fk['referred_table']}({ref_cols})")
            
            # 显示依赖关系
            if details and 'dependencies' in result:
                deps = result['dependencies']
                if deps.get('depends_on'):
                    click.echo(f"\n依赖的表: {', '.join(deps['depends_on'])}")
                if deps.get('depended_by'):
                    click.echo(f"被依赖的表: {', '.join(deps['depended_by'])}")
        else:
            click.secho(f"\n数据库中的所有表 ({len(result['tables'])} 个):", fg='cyan', bold=True)
            
            if details and result.get('table_details'):
                click.echo(f"\n  {'表名':<30} {'字段数':<8} {'外键数':<8} {'索引数':<8}")
                click.echo("  " + "-" * 60)
                for name, info in result['table_details'].items():
                    click.echo(
                        f"  {name:<30} {info['columns_count']:<8} "
                        f"{info['foreign_keys_count']:<8} {info['indexes_count']:<8}"
                    )
            else:
                for i, name in enumerate(result['tables'], 1):
                    click.echo(f"  {i}. {name}")
    else:
        click.secho(f"错误: {result['message']}", fg='red')


@cli.command()
@click.option('--database', '-d', required=False, help='数据库名称（如果未连接）')
@click.option('--table', '-t', 'table_name', required=True, help='目标表名')
@click.option('--count', '-c', default=10, type=int, help='生成数据条数')
@click.option('--strategy', '-s', default='normal',
              type=click.Choice(['normal', 'boundary', 'abnormal', 'mixed']),
              help='生成策略')
@click.option('--format', '-f', 'output_format', default='sql',
              type=click.Choice(['sql', 'csv', 'json']),
              help='输出格式')
@click.option('--output', '-o', 'output_path', default=None,
              type=click.Path(), help='输出文件路径')
@click.option('--seed', type=int, default=None, help='随机种子')
@click.option('--insert', is_flag=True, help='直接插入数据库')
def generate(database: Optional[str], table_name: str, count: int,
             strategy: str, output_format: str, output_path: Optional[str],
             seed: Optional[int], insert: bool):
    """为指定表生成测试数据

    \b
    示例:
      python main.py generate -t users -c 100
      python main.py generate -t orders -c 50 -o output/orders.sql -f sql
      python main.py generate -t products -c 200 -s boundary
      python main.py generate -t users -c 100 --insert
    """
    check_modules()
    
    # 检查是否已连接
    context = get_context()
    if context.parser is None:
        click.secho("错误: 数据库未连接，请先执行 connect 命令", fg='red')
        sys.exit(1)
    
    click.echo(f"正在为表 '{table_name}' 生成 {count} 条测试数据...")
    click.echo(f"生成策略: {strategy}")
    
    if output_path:
        click.echo(f"输出文件: {output_path}")
        click.echo(f"输出格式: {output_format}")
    elif insert:
        click.echo("数据将直接插入数据库")
    else:
        click.echo("数据将输出到控制台（前 5 条）")
    
    result = generate_command(
        table_name=table_name,
        count=count,
        strategy=strategy,
        output_path=output_path,
        output_format=output_format,
        seed=seed,
        insert_to_db=insert
    )
    
    if result['success']:
        click.secho(f"\n{result['message']}", fg='green')
        
        # 显示警告
        if result.get('warnings'):
            click.echo("\n警告:")
            for warning in result['warnings']:
                click.secho(f"  - {warning}", fg='yellow')
        
        # 如果没有输出文件，显示部分数据
        if not output_path and not insert:
            click.echo("\n生成的数据预览（前 5 条）:")
            for i, row in enumerate(result['data'][:5], 1):
                click.echo(f"\n  记录 {i}:")
                for key, value in row.items():
                    click.echo(f"    {key}: {value}")
    else:
        click.secho(f"\n错误: {result['message']}", fg='red')
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', 'config_path', required=True,
              type=click.Path(exists=True), help='配置文件路径')
@click.option('--insert', is_flag=True, help='直接插入数据库')
def batch(config_path: str, insert: bool):
    """批量生成测试数据（使用配置文件）

    \b
    示例:
      python main.py batch -c config.yaml
      python main.py batch -c config.json --insert
    """
    check_modules()
    
    click.echo(f"使用配置文件 {config_path} 批量生成数据...")
    
    result = batch_command(
        config_path=config_path,
        insert_to_db=insert
    )
    
    if result['success']:
        click.secho(f"\n{result['message']}", fg='green')
        
        # 显示每个表的处理结果
        click.echo("\n处理结果:")
        for table_result in result['tables']:
            status = "成功" if table_result['success'] else "失败"
            status_color = 'green' if table_result['success'] else 'red'
            click.echo(f"  - {table_result['table_name']}: ", nl=False)
            click.secho(status, fg=status_color, nl=False)
            click.echo(f" ({table_result['count']} 条)")
            
            if table_result.get('output_file'):
                click.echo(f"    输出: {table_result['output_file']}")
        
        # 显示输出文件列表
        if result['output_files']:
            click.echo(f"\n生成的文件:")
            for file_path in result['output_files']:
                click.echo(f"  - {file_path}")
    else:
        click.secho(f"\n错误: {result['message']}", fg='red')
        sys.exit(1)


@cli.command()
@click.option('--database', '-d', required=False, help='数据库名称（如果未连接）')
@click.option('--table', '-t', 'table_name', required=True, help='目标表名')
@click.option('--column', '-c', 'column_name', default=None, help='指定字段名（可选）')
@click.option('--strategy', '-s', default='normal',
              type=click.Choice(['normal', 'boundary', 'abnormal', 'mixed']),
              help='生成策略')
@click.option('--count', default=5, type=int, help='预览数量')
def preview(database: Optional[str], table_name: str, column_name: Optional[str],
            strategy: str, count: int):
    """预览生成数据

    生成少量数据用于预览生成效果。

    \b
    示例:
      python main.py preview -t users
      python main.py preview -t users -c name
      python main.py preview -t orders -s boundary --count 10
    """
    check_modules()
    
    # 检查是否已连接
    context = get_context()
    if context.parser is None:
        click.secho("错误: 数据库未连接，请先执行 connect 命令", fg='red')
        sys.exit(1)
    
    result = preview_command(
        table_name=table_name,
        strategy=strategy,
        count=count,
        column_name=column_name
    )
    
    if result['success']:
        click.secho(f"\n{result['message']}", fg='cyan', bold=True)
        click.echo(f"生成策略: {strategy}")
        click.echo(f"预览数量: {count}")
        
        # 显示预览数据
        for preview in result['preview_data']:
            click.echo(f"\n字段: {preview['column_name']}")
            click.echo(f"  类型: {preview['data_type']}")
            click.echo(f"  可空: {'是' if preview['nullable'] else '否'}")
            click.echo(f"  生成器: {preview['generator']}")
            click.echo(f"  示例值:")
            for i, value in enumerate(preview['sample_values'], 1):
                click.echo(f"    {i}. {value}")
    else:
        click.secho(f"\n错误: {result['message']}", fg='red')
        sys.exit(1)


@cli.command('list-strategies')
def list_strategies():
    """列出所有可用的生成策略"""
    check_modules()
    
    strategies = get_available_strategies()
    click.secho("\n可用的生成策略:", fg='cyan', bold=True)
    
    strategy_descriptions = {
        'normal': '正常值策略 - 生成符合业务规则的正常数据',
        'boundary': '边界值策略 - 生成边界值和极限值数据',
        'abnormal': '异常值策略 - 生成异常和无效数据',
        'mixed': '混合策略 - 混合使用多种策略'
    }
    
    for strategy in strategies:
        desc = strategy_descriptions.get(strategy, '')
        click.echo(f"  - {strategy}: {desc}")


@cli.command('list-formats')
def list_formats():
    """列出所有可用的输出格式"""
    check_modules()
    
    formats = get_available_formats()
    click.secho("\n可用的输出格式:", fg='cyan', bold=True)
    
    format_descriptions = {
        'sql': 'SQL INSERT 语句 - 生成可直接执行的 SQL 语句',
        'csv': 'CSV 文件 - 逗号分隔值文件，兼容 Excel',
        'json': 'JSON 文件 - 结构化数据格式'
    }
    
    for fmt in formats:
        desc = format_descriptions.get(fmt, '')
        click.echo(f"  - {fmt}: {desc}")


@cli.command()
@click.option('--host', '-h', default='127.0.0.1', help='服务器主机地址')
@click.option('--port', '-p', default=8000, type=int, help='服务器端口')
@click.option('--reload', is_flag=True, help='启用自动重载（开发模式）')
def web(host: str, port: int, reload: bool):
    """启动 Web 服务

    启动 FastAPI Web 服务器，提供前端界面和 RESTful API。

    \b
    示例:
      python main.py web
      python main.py web -h 0.0.0.0 -p 8080
      python main.py web --reload
    """
    try:
        import uvicorn
    except ImportError:
        click.secho("错误: uvicorn 未安装，请运行: pip install uvicorn", fg='red')
        sys.exit(1)
    
    click.secho(f"\n启动 Web 服务...", fg='cyan', bold=True)
    click.echo(f"主机: {host}")
    click.echo(f"端口: {port}")
    click.echo(f"访问地址: http://{host}:{port}")
    click.echo(f"API 文档: http://{host}:{port}/docs")
    click.echo("\n按 Ctrl+C 停止服务\n")
    
    try:
        uvicorn.run(
            "src.api.app:app",
            host=host,
            port=port,
            reload=reload
        )
    except KeyboardInterrupt:
        click.echo("\n服务已停止")
    except Exception as e:
        click.secho(f"\n启动服务失败: {e}", fg='red')
        sys.exit(1)


def main():
    """主入口函数"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        logger.exception("程序执行出错")
        click.secho(f"\n错误: {e}", fg='red')
        sys.exit(1)


if __name__ == '__main__':
    main()
