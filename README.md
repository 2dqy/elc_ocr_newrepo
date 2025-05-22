# 医疗图像分析API

这是一个用于识别医疗图像中血压、血糖等信息的FastAPI应用程序。

## 项目结构

```
project_root/
│
├── app/
│   ├── api/             # API路由
│   │   └── v1/
│   │       └── endpoints/
│   │           └── token.py
│   ├── core/           # 核心配置
│   │   └── config.py
│   ├── db/             # 数据库
│   │   └── database.py
│   ├── models/         # 数据库模型
│   ├── schemas/        # Pydantic模型
│   │   └── token.py
│   ├── services/       # 业务逻辑
│   │   └── token_service.py
│   ├── static/         # 静态文件
│   └── main.py         # 应用入口
│
├── tests/              # 测试文件
├── requirements.txt    # 依赖
└── .env               # 环境变量
```

## 安装

1. 克隆项目：
```bash
git clone <repository_url>
cd <project_directory>
```

2. 创建虚拟环境：
```bash
uv init
uv venv
```

3. 安装依赖：
```bash
uv add -r requirements.txt
```

4. 配置环境变量：
复制 `.env.example` 到 `.env` 并填写必要的配置：
```bash
cp .env.example .env
```

## 运行

启动开发服务器：
```bash
python -m app.main
```

服务器将在 http://localhost:8000 运行

## API文档

访问 http://localhost:8000/docs 查看API文档

## 主要功能

1. Token管理
   - 创建新Token
   - 验证Token
   - 更新Token使用次数

2. 图像分析
   - 上传医疗图像
   - 识别血压数据
   - 识别血糖数据

## 开发指南

1. 添加新的API端点：
   - 在 `app/api/v1/endpoints/` 创建新的路由文件
   - 在 `app/schemas/` 添加相应的Pydantic模型
   - 在 `app/services/` 实现业务逻辑
   - 在 `app/main.py` 注册新的路由

2. 数据库操作：
   - 所有数据库操作都应该通过 `app/db/database.py` 中的Database类进行
   - 在 `app/models/` 定义新的数据库模型

## 贡献

欢迎提交Pull Request和Issue。

## 许可证

[MIT License](LICENSE)
