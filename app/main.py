from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime

from app.core.config import settings
from app.api.v1.endpoints import token

# 创建FastAPI应用程序
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="识别图像中的血压、血糖等信息"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 包含API路由
app.include_router(token.router, prefix=settings.API_V1_STR)

# 健康检查接口
@app.get("/")
async def health_check():
    return {
        "status": "server測試成功",
        "server_time": datetime.utcnow().isoformat()
    }

# HTML首页
@app.get("/html")
async def read_root():
    """返回HTML首页"""
    from pathlib import Path
    file_path = Path(__file__).parent / "static" / "index.html"
    from fastapi.responses import FileResponse
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.v1.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )

