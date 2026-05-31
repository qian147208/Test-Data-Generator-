# -*- coding: utf-8 -*-
"""SQL 工具模块

提供 SQL 语句生成和转义的公共函数。
"""

from typing import Any, List, Dict

def escape_value(value: Any) -> str:
    """转义 SQL 值"""
    if value is None:
        return "NULL"
    elif isinstance(value, bool):
        return "1" if value else "0"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    elif isinstance(value, bytes):
        return f"X'{value.hex()}'"
    else:
        escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

def generate_insert_sql(
    table_name: str,
    data: List[Dict[str, Any]],
    batch_size: int = 100,
    use_backticks: bool = True
) -> List[str]:
    """生成 INSERT SQL 语句"""
    if not data:
        return []

    sql_statements = []
    columns = list(data[0].keys())
    quote = "`" if use_backticks else '"'
    columns_str = ", ".join(f"{quote}{col}{quote}" for col in columns)

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        values_list = []
        for row in batch:
            values = ", ".join(escape_value(row.get(col)) for col in columns)
            values_list.append(f"({values})")
        values_str = ",\n".join(values_list)
        sql = f"INSERT INTO {quote}{table_name}{quote} ({columns_str})\nVALUES\n{values_str};"
        sql_statements.append(sql)

    return sql_statements

def generate_create_table_sql(
    table_name: str,
    columns_info: List[Dict[str, Any]],
    primary_keys: List[str] = None,
    foreign_keys: List[Dict[str, Any]] = None,
    use_backticks: bool = True
) -> str:
    """生成 CREATE TABLE SQL 语句"""
    quote = "`" if use_backticks else '"'
    column_defs = []

    for col in columns_info:
        col_def = f"  {quote}{col['name']}{quote} {col['data_type']}"
        if col.get('length'):
            if col.get('scale'):
                col_def += f"({col['length']}, {col['scale']})"
            else:
                col_def += f"({col['length']})"
        if not col.get('is_nullable', True):
            col_def += " NOT NULL"
        if col.get('autoincrement'):
            col_def += " AUTO_INCREMENT"
        if col.get('default') is not None:
            col_def += f" DEFAULT {escape_value(col['default'])}"
        column_defs.append(col_def)

    if primary_keys:
        pk_str = ", ".join(f"{quote}{pk}{quote}" for pk in primary_keys)
        column_defs.append(f"  PRIMARY KEY ({pk_str})")

    if foreign_keys:
        for fk in foreign_keys:
            fk_cols = ", ".join(f"{quote}{col}{quote}" for col in fk['constrained_columns'])
            ref_cols = ", ".join(f"{quote}{col}{quote}" for col in fk['referred_columns'])
            fk_def = f"  FOREIGN KEY ({fk_cols}) REFERENCES {quote}{fk['referred_table']}{quote}({ref_cols})"
            if fk.get('on_delete'):
                fk_def += f" ON DELETE {fk['on_delete']}"
            if fk.get('on_update'):
                fk_def += f" ON UPDATE {fk['on_update']}"
            column_defs.append(fk_def)

    sql = f"CREATE TABLE {quote}{table_name}{quote} (\n"
    sql += ",\n".join(column_defs)
    sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"

    return sql
