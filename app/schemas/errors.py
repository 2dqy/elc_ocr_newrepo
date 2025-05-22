from typing import List, Optional
from pydantic import BaseModel, Field

class ErrorExtension(BaseModel):
    """错误扩展信息模型"""
    code: str = Field(..., description="错误代码")
    reason: Optional[str] = Field(None, description="错误原因的详细说明")

class ErrorDetail(BaseModel):
    """单个错误详情模型"""
    message: str = Field(..., description="错误消息")
    extensions: ErrorExtension = Field(..., description="错误扩展信息")

class ErrorResponse(BaseModel):
    """统一错误响应模型"""
    errors: List[ErrorDetail] = Field(..., description="错误列表") 