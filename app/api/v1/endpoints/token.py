from fastapi import APIRouter, HTTPException, Request
from app.schemas.token import TokenCreate, TokenResponse, ErrorResponse
from app.services.token_service import create_token, get_ip_prefix
from app.models.database import IPRepository

router = APIRouter()

@router.post("/add_token", response_model=TokenResponse, responses={400: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def add_token(request: Request, token_data: TokenCreate):
    """
    添加新的token
    
    Args:
        request: FastAPI请求对象
        token_data: token创建数据
    
    Returns:
        新创建的token信息
    """
    # 获取并验证客户端IP
    client_ip = request.client.host if request.client else None
    if not client_ip:
        raise HTTPException(
            status_code=403,
            detail={
                "errors": [{
                    "message": "無法獲取客戶端 IP",
                    "extensions": {"code": "IP_DENY"}
                }]
            }
        )
    
    # 验证IP白名单
    allowed_ips = IPRepository.get_allowed_ips()
    client_prefix = get_ip_prefix(client_ip)
    allowed_prefixes = [get_ip_prefix(ip) for ip in allowed_ips]
    
    if client_prefix not in allowed_prefixes:
        raise HTTPException(
            status_code=403,
            detail={
                "errors": [{
                    "message": "IP 使用有限制",
                    "extensions": {
                        "code": "IP_DENY",
                        "reason": "请联系info@2dqy.com或bob@2dqy.com"
                    }
                }]
            }
        )
    
    try:
        # 创建token
        return create_token(token_data)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [{
                    "message": str(e),
                    "extensions": {"code": "TOKEN_INVALID"}
                }]
            }
        ) 