"""FastAPI 应用入口。

Phase 0：仅 /health 端点，验证工程骨架能跑。
后续 Phase 会逐步加 auth/workflows/agent 等路由。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.projects import router as projects_router
from app.api.v1.usage import router as usage_router
from app.api.v1.workflows import router as workflows_router
from app.config import settings
from app.core.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger("app")
    logger.info("startup", app=settings.app_name, version=settings.version, debug=settings.debug)
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(feedback_router)
app.include_router(auth_router)
app.include_router(workflows_router)
app.include_router(projects_router)
app.include_router(usage_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.version, "app": settings.app_name}


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs" if settings.debug else "disabled",
    }
