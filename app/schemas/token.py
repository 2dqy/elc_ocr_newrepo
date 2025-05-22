from pydantic import BaseModel, Field
from typing import Optional

class TokenCreate(BaseModel):
    """创建Token的请求模型"""
    token: Optional[str] = Field(None, description="自定义token，如果为空则自动生成")
    use_times: Optional[int] = Field(10, description="token可使用次数，默认为10次")
    center_id: str = Field(..., description="中心ID")

class TokenResponse(BaseModel):
    """Token响应模型"""
    id: int
    token: str
    use_times: int
    center_id: str

class ErrorResponse(BaseModel):
    """错误响应模型"""
    errors: list[dict] 