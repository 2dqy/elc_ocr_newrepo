import random
import string
from typing import Optional
from app.schemas.token import TokenCreate, TokenResponse
from app.models.database import TokenRepository, CenterRepository, IPRepository

def generate_random_token(length: int = 10) -> str:
    """
    生成随机token
    
    Args:
        length: token长度，默认10位
    
    Returns:
        随机生成的token字符串
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_ip_prefix(ip: str) -> str:
    """
    获取IP地址的前缀（前三段）
    
    Args:
        ip: IP地址
    
    Returns:
        IP地址前缀
    """
    return '.'.join(ip.split('.')[:3])

def verify_token(token: str) -> bool:
    """
    验证token是否有效
    
    Args:
        token: 要验证的token
    
    Returns:
        token是否有效
    """
    return TokenRepository.token_exists(token)

def update_token_usage(token: str) -> bool:
    """
    更新token使用次数
    
    Args:
        token: 要更新的token
        
    Returns:
        更新是否成功
    """
    return TokenRepository.update_token_usage(token)

def create_token(token_data: TokenCreate) -> TokenResponse:
    """
    创建新的token
    
    Args:
        token_data: token创建数据
    
    Returns:
        创建的token信息
        
    Raises:
        ValueError: 当token格式无效或已存在，或center_id无效时抛出
    """
    # 如果没有提供token，生成随机token
    token = token_data.token or generate_random_token()
    
    # 验证token格式
    if not token.isalnum():
        raise ValueError("Token只能包含字母和数字")
    
    # 检查token是否已存在
    if TokenRepository.token_exists(token):
        raise ValueError("Token已存在")
    
    # 验证center_id
    if not CenterRepository.center_exists(token_data.center_id):
        raise ValueError("无效的center_id")
    
    # 添加token到数据库
    new_token_id = TokenRepository.add_token(
        token=token,
        use_times=token_data.use_times,
        center_id=token_data.center_id
    )
    
    return TokenResponse(
        id=new_token_id,
        token=token,
        use_times=token_data.use_times,
        center_id=token_data.center_id
    ) 