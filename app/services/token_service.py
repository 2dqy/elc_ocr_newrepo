import random
import string
from typing import Optional
from app.db.database import Database
from app.schemas.token import TokenCreate, TokenResponse

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
    db = Database()
    return db.token_exists(token)

def update_token_usage(token: str) -> None:
    """
    更新token使用次数
    
    Args:
        token: 要更新的token
    """
    db = Database()
    # TODO: 实现token使用次数更新逻辑
    pass

def create_token(token_data: TokenCreate) -> TokenResponse:
    """
    创建新的token
    
    Args:
        token_data: token创建数据
    
    Returns:
        创建的token信息
    """
    db = Database()
    
    # 如果没有提供token，生成随机token
    token = token_data.token or generate_random_token()
    
    # 验证token格式
    if not token.isalnum():
        raise ValueError("Token只能包含字母和数字")
    
    # 检查token是否已存在
    if db.token_exists(token):
        raise ValueError("Token已存在")
    
    # 验证center_id
    if not db.center_id_exists(token_data.center_id):
        raise ValueError("无效的center_id")
    
    # 添加token到数据库
    db.add_token(token, token_data.use_times, token_data.center_id)
    
    # 获取新创建的token ID
    # TODO: 实现获取新创建token ID的逻辑
    new_token_id = 1  # 临时占位
    
    return TokenResponse(
        id=new_token_id,
        token=token,
        use_times=token_data.use_times,
        center_id=token_data.center_id
    ) 