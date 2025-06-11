from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.v1.app import router as v1_router  # 引入定义的router
# from app.api.v1.dashboard import router as dashboard_router  # 引入Dashboard router

from pathlib import Path


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

# 注册接口
app.include_router(v1_router)
# app.include_router(dashboard_router)  # 注册Dashboard API

@app.get("/")
async def health_check():
    from datetime import datetime
    return {
        "status": "server測試成功",
        "server_time": datetime.utcnow().isoformat()
    }

@app.get("/dashboard")
async def read_root():
    """返回HTML首页"""
    file_path = Path(__file__).resolve().parent / "static" / "dashboard.html"
    return FileResponse(file_path)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # 修改为正确的应用路径
        host="127.0.0.1",
        port=settings.PORT,
        reload=True
    )

