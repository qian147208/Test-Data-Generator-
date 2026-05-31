# -*- coding: utf-8 -*-
"""数据生成 API 路由"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    GenerateRequest, GenerateResponse, GeneratePreviewRequest,
    GenerateBatchRequest, GenerateBatchResponse, ColumnRuleConfig,
    APIResponse, ErrorResponse
)
from .connection import get_schema_parser
from ...data_generator import DataEngine, ColumnRule
from ...relation_handler import RelationManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/generate", tags=["数据生成"])

_relation_manager: Optional[RelationManager] = None
_generated_data: Dict[str, List[Dict[str, Any]]] = {}

def get_relation_manager() -> RelationManager:
    global _relation_manager
    if _relation_manager is None:
        _relation_manager = RelationManager()
    return _relation_manager

def store_generated_data(table_name: str, data: List[Dict[str, Any]]):
    global _generated_data
    _generated_data[table_name] = data

def get_generated_data(table_name: str) -> Optional[List[Dict[str, Any]]]:
    return _generated_data.get(table_name)

def clear_generated_data(table_name: Optional[str] = None):
    global _generated_data
    if table_name:
        _generated_data.pop(table_name, None)
    else:
        _generated_data.clear()

@router.post("", response_model=GenerateResponse, summary="生成测试数据")
async def generate_data(request: GenerateRequest):
    """生成测试数据"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    table_schema = parser.parse_table(request.table_name)
    if not table_schema.columns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"表 '{request.table_name}' 不存在")

    engine = DataEngine(locale=request.locale)
    if request.column_rules:
        for rule_config in request.column_rules:
            engine.register_column_rule(ColumnRule(
                column_name=rule_config.column_name,
                strategy=rule_config.strategy,
                generator_params=rule_config.generator_params,
                custom_values=rule_config.custom_values
            ))

    result = engine.generate_for_table(table_schema=table_schema, strategy=request.strategy, count=request.count)
    store_generated_data(request.table_name, result.data)

    logger.info(f"为表 '{request.table_name}' 生成了 {result.total_rows} 行数据")
    return GenerateResponse(
        table_name=result.table_name, strategy=result.strategy,
        total_rows=result.total_rows, warnings=result.warnings, data=result.data
    )

@router.post("/preview", response_model=GenerateResponse, summary="预览生成数据")
async def preview_data(request: GeneratePreviewRequest):
    """预览生成数据"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    table_schema = parser.parse_table(request.table_name)
    if not table_schema.columns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"表 '{request.table_name}' 不存在")

    engine = DataEngine()
    result = engine.generate_for_table(table_schema=table_schema, strategy=request.strategy, count=request.count)

    return GenerateResponse(
        table_name=result.table_name, strategy=result.strategy,
        total_rows=result.total_rows, warnings=result.warnings, data=result.data
    )

@router.post("/batch", response_model=GenerateBatchResponse, summary="批量生成测试数据")
async def generate_batch_data(request: GenerateBatchRequest):
    """批量生成测试数据"""
    parser = get_schema_parser()
    if parser is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接")

    tables_schemas = {name: parser.parse_table(name) for name in request.tables if parser.parse_table(name).columns}
    if not tables_schemas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有找到有效的表")

    engine = DataEngine(locale=request.locale)
    relation_manager = get_relation_manager()
    plan = relation_manager.plan_generation_order(tables_schemas)
    generation_order = plan.ordered_tables if request.respect_dependencies else list(tables_schemas.keys())

    results: Dict[str, GenerateResponse] = {}
    errors: List[str] = []

    for table_name in generation_order:
        if table_name not in tables_schemas:
            continue
        try:
            table_schema = tables_schemas[table_name]
            fk_values = {}
            for fk in table_schema.foreign_keys:
                if fk.referred_table != table_name:
                    ref_data = get_generated_data(fk.referred_table)
                    if ref_data:
                        for col in fk.referred_columns:
                            fk_values[col] = [row.get(col) for row in ref_data if row.get(col) is not None]

            result = engine.generate_with_foreign_keys(
                table_schema=table_schema, strategy=request.strategy,
                count=request.count_per_table, foreign_key_values=fk_values
            ) if fk_values else engine.generate_for_table(
                table_schema=table_schema, strategy=request.strategy, count=request.count_per_table
            )

            store_generated_data(table_name, result.data)
            results[table_name] = GenerateResponse(
                table_name=result.table_name, strategy=result.strategy,
                total_rows=result.total_rows, warnings=result.warnings, data=result.data
            )
            logger.info(f"批量生成: 表 '{table_name}' 完成")
        except Exception as e:
            errors.append(f"表 '{table_name}' 生成失败: {str(e)}")
            logger.error(errors[-1])

    return GenerateBatchResponse(
        total_tables=len(tables_schemas), processed_tables=len(results),
        results=results, generation_order=generation_order, errors=errors
    )

@router.get("/strategies", response_model=APIResponse, summary="获取可用策略")
async def get_available_strategies():
    engine = DataEngine()
    return APIResponse(success=True, message="获取可用策略成功", data=engine.get_available_strategies())

@router.get("/types", response_model=APIResponse, summary="获取支持的数据类型")
async def get_supported_types():
    engine = DataEngine()
    return APIResponse(success=True, message="获取支持的数据类型成功", data=engine.get_supported_types())

@router.delete("/data/{table_name}", response_model=APIResponse, summary="清除已生成的数据")
async def clear_table_data(table_name: str):
    clear_generated_data(table_name)
    return APIResponse(success=True, message=f"已清除表 '{table_name}' 的生成数据")

@router.delete("/data", response_model=APIResponse, summary="清除所有已生成的数据")
async def clear_all_data():
    clear_generated_data()
    return APIResponse(success=True, message="已清除所有生成数据")
