from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import uvicorn
import logging
from datetime import datetime

from server.routes import (
    jobs_router,
    pools_router,
    nodes_router,
    labels_router,
    global_labels_router,
    quotas_router,
    namespaces_router,
    inferences_router,
    apikeys_router
)
from server.routes.clusters import router as clusters_router
from server.routes.apikeys import set_store
from server.auth import install_api_auth

# 配置日志
import os
log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.debug(f"日志级别设置为: {log_level}")

app = FastAPI(
    title="GPU Control API",
    description="面向算法工程师的AI算力调度平台API",
    version="1.0.0"
)

# CORS：默认不开放跨域；需要时用 GPUCTL_CORS_ORIGINS=https://a.com,https://b.com 显式放行
_cors_origins = [o.strip() for o in os.getenv("GPUCTL_CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# API Key 鉴权（GPUCTL_API_AUTH=apikey 时启用；独立 server 无浏览器会话，不设兜底）
_auth_store = install_api_auth(app)
if _auth_store is not None:
    set_store(_auth_store)

# 注册路由
app.include_router(jobs_router)
app.include_router(pools_router)
app.include_router(labels_router)  # 先注册labels_router，避免路由冲突
app.include_router(nodes_router)    # 后注册nodes_router
app.include_router(quotas_router)
app.include_router(namespaces_router)
app.include_router(global_labels_router)
app.include_router(clusters_router, prefix="/api/v1")
app.include_router(inferences_router)
app.include_router(apikeys_router)


# 根路由
@app.get("/")
async def root():
    return {"message": "GPU Control API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )