from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from app.schemas.errors import ErrorResponse, ErrorDetail, ErrorExtension
import pymysql

def add_error_handlers(app: FastAPI) -> None:
    """
    添加全局错误处理器
    
    Args:
        app: FastAPI应用实例
    """
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        errors = []
        for error in exc.errors():
            errors.append(
                ErrorDetail(
                    message=f"验证错误: {error['msg']}",
                    extensions=ErrorExtension(
                        code="VALIDATION_ERROR",
                        reason=f"位置: {' -> '.join(str(loc) for loc in error['loc'])}"
                    )
                )
            )
        
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(errors=errors).dict()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict) and 'errors' in exc.detail:
            # 已经是标准错误格式
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )
        
        # 转换为标准错误格式
        error_response = ErrorResponse(
            errors=[
                ErrorDetail(
                    message=str(exc.detail),
                    extensions=ErrorExtension(
                        code=f"HTTP_{exc.status_code}",
                    )
                )
            ]
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.dict()
        )

    @app.exception_handler(pymysql.Error)
    async def mysql_exception_handler(request: Request, exc: pymysql.Error):
        """处理MySQL数据库错误"""
        error_response = ErrorResponse(
            errors=[
                ErrorDetail(
                    message="数据库操作错误",
                    extensions=ErrorExtension(
                        code="DATABASE_ERROR",
                        reason=str(exc)
                    )
                )
            ]
        )
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理所有其他未处理的异常"""
        error_response = ErrorResponse(
            errors=[
                ErrorDetail(
                    message="服务器内部错误",
                    extensions=ErrorExtension(
                        code="INTERNAL_SERVER_ERROR",
                        reason=str(exc)
                    )
                )
            ]
        )
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        ) 