from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class AuthValidator:
    """认证验证器"""

    @staticmethod
    async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
        """验证Bearer Token - 已禁用认证，始终返回 True"""
        return True


security = HTTPBearer()