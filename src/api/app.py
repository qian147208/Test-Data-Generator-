# -*- coding: utf-8 -*-
"""FastAPI 应用入口

创建和配置 FastAPI 应用实例。
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional
import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .routes import (
    connection_router,
    tables_router,
    generate_router,
    export_router
)
from .schemas import ErrorResponse


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("API 服务启动中...")
    
    yield
    
    # 关闭时执行
    logger.info("API 服务关闭中...")
    
    # 断开数据库连接
    from .routes.connection import get_connection_manager, set_connection_manager
    try:
        manager = get_connection_manager()
        if manager and manager.is_connected:
            manager.disconnect()
            logger.info("数据库连接已断开")
    except Exception:
        pass
    
    # 清理资源
    from .routes.generate import clear_generated_data
    clear_generated_data()
    logger.info("生成数据已清理")


def create_app(
    title: str = "测试数据生成 API",
    description: str = """
## 功能概述

提供测试数据生成的 RESTful API 接口，支持：

### 数据库连接管理
- 连接 MySQL、PostgreSQL、SQLite 数据库
- 管理连接池
- 测试连接状态

### 表结构查询
- 获取所有表列表
- 查询表详细结构
- 分析表依赖关系

### 测试数据生成
- 单表数据生成
- 批量数据生成
- 自定义生成规则
- 多种生成策略（正常值、边界值、异常值、混合）

### SQL 导出
- 导出 INSERT 语句
- 批量导出
- 文件下载

## 使用流程

1. 调用 `/api/connect` 建立数据库连接
2. 调用 `/api/tables` 获取表列表
3. 调用 `/api/generate` 生成测试数据
4. 调用 `/api/export/sql` 导出 SQL 语句
""",
    version: str = "1.0.0",
    cors_origins: Optional[list] = None,
    static_dir: Optional[str] = None
) -> FastAPI:
    """创建 FastAPI 应用实例
    
    Args:
        title: 应用标题
        description: 应用描述
        version: 版本号
        cors_origins: CORS 允许的源列表
        static_dir: 静态文件目录
        
    Returns:
        FastAPI 应用实例
    """
    # 创建应用
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # 配置 CORS
    if cors_origins is None:
        cors_origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(connection_router)
    app.include_router(tables_router)
    app.include_router(generate_router)
    app.include_router(export_router)
    
    # 挂载静态文件
    if static_dir:
        try:
            app.mount("/static", StaticFiles(directory=static_dir), name="static")
            logger.info(f"静态文件目录已挂载: {static_dir}")
        except Exception as e:
            logger.warning(f"挂载静态文件目录失败: {e}")
    
    # 挂载前端构建文件
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
    if os.path.exists(frontend_dir):
        try:
            app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
            logger.info(f"前端构建文件已挂载: {frontend_dir}")
        except Exception as e:
            logger.warning(f"挂载前端构建文件失败: {e}")
    
    # 异常处理
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """处理 Pydantic 验证错误"""
        logger.error(f"验证错误: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "error_message": "请求数据验证失败",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "error_message": str(exc),
                "details": None
            }
        )
    
    # 健康检查端点
    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "service": "test-data-generator-api",
            "version": version
        }
    
    # 根路径
    @app.get("/api", tags=["系统"])
    async def api_root():
        """API 根路径"""
        return {
            "message": "测试数据生成 API 服务",
            "version": version,
            "docs": "/docs",
            "redoc": "/redoc"
        }
    
    logger.info("FastAPI 应用创建成功")
    
    return app


# 默认应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
