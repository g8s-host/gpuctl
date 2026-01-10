from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class AuthValidator:
    """认证验证器"""

    @staticmethod
    async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """验证Bearer Token"""
        token = credentials.credentials
        # 这里应该实现实际的token验证逻辑
        # 为了方便测试，允许任何非空token
        if not token:
            raise HTTPException(status_code=401, detail="Invalid token")
        return token


security = HTTPBearer()