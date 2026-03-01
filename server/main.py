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
    namespaces_router
)

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

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(jobs_router)
app.include_router(pools_router)
app.include_router(labels_router)  # 先注册labels_router，避免路由冲突
app.include_router(nodes_router)    # 后注册nodes_router
app.include_router(quotas_router)
app.include_router(namespaces_router)
app.include_router(global_labels_router)


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