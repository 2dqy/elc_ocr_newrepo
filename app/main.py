from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.app import router as v1_router  # 引入定义的router



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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.v1.app:app",
        port=settings.PORT,
        reload=True
    )

