import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import uvicorn


# 加载.env环境变量
load_dotenv()

# 创建FastAPI应用程序
app = FastAPI(title="医疗图像分析API", description="识别图像中的血压、血糖等信息")

# 配置CORS（跨源资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 获取API密钥和配置参数
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))

if __name__ == "__main__":
    # 启动FastAPI应用
    uvicorn.run("version.v1.app:app", host=HOST, port=PORT, reload=True)

