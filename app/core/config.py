from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Settings(BaseSettings):
    """应用程序配置类"""
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "医疗图像分析API"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # DashScope配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY")
    
    # 服务器配置
    HOST: str = os.getenv("HOST")
    PORT: int = int(os.getenv("PORT"))
    
    # 图像处理配置
    MIN_PIXELS: int = int(os.getenv("MIN_PIXELS", 28 * 28 * 4))
    MAX_PIXELS: int = int(os.getenv("MAX_PIXELS", 28 * 28 * 8192))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 500 * 1024))
    
    class Config:
        case_sensitive = True

# 创建全局设置对象
settings = Settings() 