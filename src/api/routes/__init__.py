# -*- coding: utf-8 -*-
"""API 路由模块"""

from .connection import router as connection_router
from .tables import router as tables_router
from .generate import router as generate_router
from .export import router as export_router

__all__ = [
    'connection_router',
    'tables_router',
    'generate_router',
    'export_router'
]
