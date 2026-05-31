# -*- coding: utf-8 -*-
"""数据生成 API 路由

提供测试数据生成的 RESTful API 接口。
"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, status

from ..schemas import (
    GenerateRequest,
    GenerateResponse,
    GeneratePreviewRequest,
    GenerateBatchRequest,
    GenerateBatchResponse,
    ColumnRuleConfig,
    APIResponse,
    ErrorResponse
)
from .connection import get_connection_manager, get_schema_parser
from ...data_generator import (
    DataEngine,
    ColumnRule,
    GenerationResult
)
from ...relation_handler import RelationManager


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/generate", tags=["数据生成"])

# 全局 RelationManager 实例
_relation_manager: Optional[RelationManager] = None
_data_engine: Optional[DataEngine] = None
_generated_data: Dict[str, List[Dict[str, Any]]] = {}


def get_relation_manager() -> RelationManager:
    """获取 RelationManager 实例"""
    global _relation_manager
    if _relation_manager is None:
        _relation_manager = RelationManager()
    return _relation_manager


def get_data_engine(locale: str = "zh_CN") -> DataEngine:
    """获取 DataEngine 实例"""
    global _data_engine
    if _data_engine is None:
        _data_engine = DataEngine(locale=locale)
    return _data_engine


def store_generated_data(table_name: str, data: List[Dict[str, Any]]):
    """存储生成的数据"""
    global _generated_data
    _generated_data[table_name] = data


def get_generated_data(table_name: str) -> Optional[List[Dict[str, Any]]]:
    """获取已生成的数据"""
    return _generated_data.get(table_name)


def clear_generated_data(table_name: Optional[str] = None):
    """清除已生成的数据"""
    global _generated_data
    if table_name:
        _generated_data.pop(table_name, None)
    else:
        _generated_data.clear()


@router.post(
    "",
    response_model=GenerateResponse,
    responses={
        200: {"description": "数据生成成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "表不存在"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="生成测试数据",
    description="为指定表生成测试数据"
)
async def generate_data(request: GenerateRequest):
    """生成测试数据"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 获取表结构
        table_schema = parser.parse_table(request.table_name)
        if not table_schema.columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"表 '{request.table_name}' 不存在"
            )
        
        # 创建数据引擎
        engine = DataEngine(locale=request.locale)
        
        # 注册字段规则
        if request.column_rules:
            for rule_config in request.column_rules:
                rule = ColumnRule(
                    column_name=rule_config.column_name,
                    strategy=rule_config.strategy,
                    generator_params=rule_config.generator_params,
                    custom_values=rule_config.custom_values
                )
                engine.register_column_rule(rule)
        
        # 生成数据
        result = engine.generate_for_table(
            table_schema=table_schema,
            strategy=request.strategy,
            count=request.count
        )
        
        # 存储生成的数据
        store_generated_data(request.table_name, result.data)
        
        logger.info(f"为表 '{request.table_name}' 生成了 {result.total_rows} 行数据")
        
        return GenerateResponse(
            table_name=result.table_name,
            strategy=result.strategy,
            total_rows=result.total_rows,
            warnings=result.warnings,
            data=result.data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成数据失败: {str(e)}"
        )


@router.post(
    "/preview",
    response_model=GenerateResponse,
    responses={
        200: {"description": "预览数据成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "表不存在"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="预览生成数据",
    description="预览指定表的数据生成结果（生成少量数据）"
)
async def preview_data(request: GeneratePreviewRequest):
    """预览生成数据"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 获取表结构
        table_schema = parser.parse_table(request.table_name)
        if not table_schema.columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"表 '{request.table_name}' 不存在"
            )
        
        # 创建数据引擎
        engine = DataEngine()
        
        # 生成预览数据
        result = engine.generate_for_table(
            table_schema=table_schema,
            strategy=request.strategy,
            count=request.count
        )
        
        return GenerateResponse(
            table_name=result.table_name,
            strategy=result.strategy,
            total_rows=result.total_rows,
            warnings=result.warnings,
            data=result.data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览数据失败: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=GenerateBatchResponse,
    responses={
        200: {"description": "批量生成成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        503: {"model": ErrorResponse, "description": "数据库未连接"}
    },
    summary="批量生成测试数据",
    description="为多个表批量生成测试数据，自动处理表间依赖关系"
)
async def generate_batch_data(request: GenerateBatchRequest):
    """批量生成测试数据"""
    try:
        parser = get_schema_parser()
        if parser is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库未连接，请先调用 /api/connect 接口建立连接"
            )
        
        # 获取所有表结构
        tables_schemas = {}
        for table_name in request.tables:
            table_schema = parser.parse_table(table_name)
            if table_schema.columns:
                tables_schemas[table_name] = table_schema
        
        if not tables_schemas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有找到有效的表"
            )
        
        # 创建数据引擎和关联管理器
        engine = DataEngine(locale=request.locale)
        relation_manager = get_relation_manager()
        
        # 规划生成顺序
        generation_plan = relation_manager.plan_generation_order(tables_schemas)
        
        # 确定生成顺序
        if request.respect_dependencies:
            generation_order = generation_plan.ordered_tables
        else:
            generation_order = list(tables_schemas.keys())
        
        results: Dict[str, GenerateResponse] = {}
        errors: List[str] = []
        processed_count = 0
        
        for table_name in generation_order:
            if table_name not in tables_schemas:
                continue
            
            try:
                table_schema = tables_schemas[table_name]
                
                # 获取外键引用值
                fk_values = {}
                for fk in table_schema.foreign_keys:
                    if fk.referred_table != table_name:  # 排除自引用
                        ref_data = get_generated_data(fk.referred_table)
                        if ref_data:
                            for col in fk.referred_columns:
                                fk_values[col] = [row.get(col) for row in ref_data if row.get(col) is not None]
                
                # 生成数据
                if fk_values:
                    result = engine.generate_with_foreign_keys(
                        table_schema=table_schema,
                        strategy=request.strategy,
                        count=request.count_per_table,
                        foreign_key_values=fk_values
                    )
                else:
                    result = engine.generate_for_table(
                        table_schema=table_schema,
                        strategy=request.strategy,
                        count=request.count_per_table
                    )
                
                # 存储生成的数据
                store_generated_data(table_name, result.data)
                
                results[table_name] = GenerateResponse(
                    table_name=result.table_name,
                    strategy=result.strategy,
                    total_rows=result.total_rows,
                    warnings=result.warnings,
                    data=result.data
                )
                processed_count += 1
                
                logger.info(f"批量生成: 表 '{table_name}' 完成，生成 {result.total_rows} 行")
                
            except Exception as e:
                error_msg = f"表 '{table_name}' 生成失败: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return GenerateBatchResponse(
            total_tables=len(tables_schemas),
            processed_tables=processed_count,
            results=results,
            generation_order=generation_order,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量生成数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量生成数据失败: {str(e)}"
        )


@router.get(
    "/strategies",
    response_model=APIResponse,
    summary="获取可用策略",
    description="获取所有可用的数据生成策略"
)
async def get_available_strategies():
    """获取可用的生成策略"""
    engine = DataEngine()
    strategies = engine.get_available_strategies()
    
    return APIResponse(
        success=True,
        message="获取可用策略成功",
        data=strategies
    )


@router.get(
    "/types",
    response_model=APIResponse,
    summary="获取支持的数据类型",
    description="获取所有支持的数据类型"
)
async def get_supported_types():
    """获取支持的数据类型"""
    engine = DataEngine()
    types = engine.get_supported_types()
    
    return APIResponse(
        success=True,
        message="获取支持的数据类型成功",
        data=types
    )


@router.delete(
    "/data/{table_name}",
    response_model=APIResponse,
    summary="清除已生成的数据",
    description="清除指定表的已生成数据"
)
async def clear_table_data(table_name: str):
    """清除已生成的数据"""
    clear_generated_data(table_name)
    
    return APIResponse(
        success=True,
        message=f"已清除表 '{table_name}' 的生成数据"
    )


@router.delete(
    "/data",
    response_model=APIResponse,
    summary="清除所有已生成的数据",
    description="清除所有表的已生成数据"
)
async def clear_all_data():
    """清除所有已生成的数据"""
    clear_generated_data()
    
    return APIResponse(
        success=True,
        message="已清除所有生成数据"
    )
