from fastapi import APIRouter, Depends, HTTPException
import logging

from server.models import (
    AuthCheckRequest,
    AuthCheckResponse
)
from server.auth import AuthValidator, security

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/check", response_model=AuthCheckResponse)
async def check_auth(request: AuthCheckRequest, token: str = Depends(AuthValidator.validate_token)):
    """验证用户权限"""
    try:
        allowed = True
        message = f"用户拥有{request.pool or 'default'}的{request.resource}的{request.action}权限"

        return AuthCheckResponse(allowed=allowed, message=message)

    except Exception as e:
        logger.error(f"Failed to check auth: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


__all__ = ["router"]
