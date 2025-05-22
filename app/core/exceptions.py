from typing import Optional
from fastapi import HTTPException
from app.schemas.errors import ErrorResponse, ErrorDetail, ErrorExtension

class APIError(HTTPException):
    """自定义API错误异常"""
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str,
        reason: Optional[str] = None
    ):
        """
        初始化API错误
        
        Args:
            status_code: HTTP状态码
            message: 错误消息
            error_code: 错误代码
            reason: 错误原因（可选）
        """
        detail = ErrorResponse(
            errors=[
                ErrorDetail(
                    message=message,
                    extensions=ErrorExtension(
                        code=error_code,
                        reason=reason
                    )
                )
            ]
        )
        super().__init__(status_code=status_code, detail=detail.dict())

# 预定义的错误类型
class TokenError(APIError):
    """Token相关错误"""
    def __init__(self, message: str, error_code: str = "TOKEN_ERROR", reason: Optional[str] = None):
        super().__init__(status_code=400, message=message, error_code=error_code, reason=reason)

class AuthenticationError(APIError):
    """认证相关错误"""
    def __init__(self, message: str, error_code: str = "AUTH_ERROR", reason: Optional[str] = None):
        super().__init__(status_code=401, message=message, error_code=error_code, reason=reason)

class ForbiddenError(APIError):
    """权限相关错误"""
    def __init__(self, message: str, error_code: str = "FORBIDDEN", reason: Optional[str] = None):
        super().__init__(status_code=403, message=message, error_code=error_code, reason=reason)

class ValidationError(APIError):
    """数据验证错误"""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", reason: Optional[str] = None):
        super().__init__(status_code=422, message=message, error_code=error_code, reason=reason)

class DatabaseError(APIError):
    """数据库操作错误"""
    def __init__(self, message: str, error_code: str = "DATABASE_ERROR", reason: Optional[str] = None):
        super().__init__(status_code=500, message=message, error_code=error_code, reason=reason) 