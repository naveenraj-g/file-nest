"""
services.identity.router — Route registration for the Identity Service.

Assembles all sub-routers. The /v1 prefix is added in main.py so all final
paths are /v1/api-keys/*.

Usage:
    from services.identity.router import router
    app.include_router(router, prefix="/v1")
"""
from fastapi import APIRouter

from .routes.api_keys import router as api_keys_router

router = APIRouter()
router.include_router(api_keys_router)
