from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os

security = HTTPBearer()


class AuthValidator:
    """认证验证器"""

    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'gpuctl-secret-key')
        self.algorithm = os.getenv('JWT_ALGORITHM', 'HS256')

    async def validate_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """验证Bearer Token"""
        token = credentials.credentials

        try:
            # 验证JWT token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def validate_admin(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """验证管理员权限"""
        payload = await self.validate_token(credentials)

        if payload.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return payload

    async def validate_pool_access(self, pool_name: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
        """验证用户对资源池的访问权限"""
        payload = await self.validate_token(credentials)
        user_pools = payload.get('pools', [])

        if pool_name not in user_pools and 'admin' not in user_pools:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to pool: {pool_name}"
            )

        return payload


# 创建全局认证器实例
auth_validator = AuthValidator()


# 依赖项
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户"""
    return await auth_validator.validate_token(credentials)


async def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取管理员用户"""
    return await auth_validator.validate_admin(credentials)


async def validate_pool_access(pool_name: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证资源池访问权限"""
    return await auth_validator.validate_pool_access(pool_name, credentials)