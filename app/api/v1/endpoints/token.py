from fastapi import APIRouter, Request
from app.schemas.token import TokenCreate, TokenResponse
from app.schemas.errors import ErrorResponse
from app.services.token_service import create_token, get_ip_prefix
from app.models.database import IPRepository
from app.core.exceptions import ForbiddenError, TokenError

router = APIRouter()

@router.post(
    "/add_token",
    response_model=TokenResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def add_token(request: Request, token_data: TokenCreate):
    """
    添加新的token
    
    Args:
        request: FastAPI请求对象
        token_data: token创建数据
    
    Returns:
        新创建的token信息
        
    Raises:
        ForbiddenError: 当IP验证失败时
        TokenError: 当token创建失败时
        ValidationError: 当请求数据验证失败时
    """
    # 获取并验证客户端IP
    client_ip = request.client.host if request.client else None
    if not client_ip:
        raise ForbiddenError(
            message="無法獲取客戶端 IP",
            error_code="IP_DENY"
        )
    
    # 验证IP白名单
    allowed_ips = IPRepository.get_allowed_ips()
    client_prefix = get_ip_prefix(client_ip)
    allowed_prefixes = [get_ip_prefix(ip) for ip in allowed_ips]
    
    if client_prefix not in allowed_prefixes:
        raise ForbiddenError(
            message="IP 使用有限制",
            error_code="IP_DENY",
            reason="请联系info@2dqy.com或bob@2dqy.com"
        )
    
    try:
        # 创建token
        return create_token(token_data)
    except ValueError as e:
        raise TokenError(
            message=str(e),
            error_code="TOKEN_INVALID"
        ) 