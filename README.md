# 医疗图像分析API

这是一个用于识别医疗图像中血压、血糖等信息的FastAPI应用程序。

## 项目结构

```
project_root/
│
├── app/
│   ├── api/             # API路由
│   │   └── v1/
│   │       └── app.py
│   ├── core/           # 核心配置
│   │   └── config.py
│   ├── db/             # 数据库
│   │   └── database.py
│   ├── models/         # 数据库模型
│   ├── services/       # 业务逻辑
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
source .venv/bin/activate
uvicorn app.main:app --reload 
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

3. 错误监控
   - API错误自动邮件通知
   - 模型调用失败异步邮件报警

## 开发指南

1. 添加新的API端点：
   - 在 `app/api/v1/app.py` 创建新的路由文件
   - 在 `app/services/` 实现业务逻辑
   - 在 `app/main.py` 注册新的路由

2. 数据库操作：
   - 所有数据库操作都应该通过 `app/db/database.py` 中的Database类进行
   - 在 `app/models/` 定义新的数据库模型


## 核心功能详解

### 图像识别接口 `/upload/image`

#### 接口概述
- **路径**: `POST /upload/image`
- **功能**: 上传医疗设备图像，自动识别血压计或血糖仪数据
- **支持设备**: 血压计、血糖仪

#### 输入参数
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | UploadFile | 是 | 医疗设备图像文件 |
| token | string | 是 | 验证令牌 |

#### 文件限制
- **文件类型**: 仅支持图像文件 (image/*)
- **文件大小**: 最大1mb
- **像素范围**: 28×28×4 ~ 28×28×8192像素

#### 处理流程

##### 1. 前置验证
- Token有效性验证
- 文件类型检查（必须为图像）
- 文件大小检查（≤1mb）
- 生成16位随机文件上传ID
- 获取客户端IP地址

##### 2. 图像预处理（选择性使用）
- 图像尺寸优化和压缩
- Base64编码转换
- 像素范围标准化

##### 3. AI识别分析
**识别内容**:
- 设备品牌和型号
- 设备类型判断（血压计/血糖仪）
- 测量数值提取
- 测量时间提取（从图像中）
- 可靠性评估

##### 4. 数据验证与处理
**血压数据验证**:
- 检查收缩压(sys)、舒张压(dia)、心率(pul)三个参数
- 如果任何参数为null，返回"图像有错误或不清晰"错误

**数据清洗**:
- 根据设备类型删除无关字段
- 统一数据格式

##### 5. 单位标准化

**血糖单位处理**:
- 目标单位: `mmol/L`
- 自动单位转换: 自动除以18转换
- 示例: `108mg/dL` → `6.0mmol/L`

##### 6. 后端数据补充
系统自动添加以下后端参数:
- `measure_date`: 当前日期 (YYYY-MM-DD)
- `source_ip`: 客户端IP地址
- `ai_usage`: AI使用量 (total_tokens × 10)
- `file_upload_id`: 16位随机文件ID
- `file_name`: 原始文件名
- `file_size`: 文件大小(字节)
- `token`: 用户提供的认证令牌

##### 7. 错误处理与通知
- API调用失败时，系统会异步发送邮件通知
- 邮件包含错误时间、文件名和详细错误信息
- 不会影响API响应时间，邮件在后台异步发送

#### 错误响应格式

**文件格式错误**:
```json
{
  "errors": [
    {
      "messages": "唯有上载图像文件",
      "extensions": {
        "code": "UPLOAD_FILE_FAIL"
      }
    }
  ]
}
```

**文件大小超限**:
```json
{
  "errors": [
    {
      "messages": "文件大小超过1mb制",
      "extensions": {
        "code": "UPLOAD_FILE_FAIL" 
      }
    }
  ]
}
```

**图像不清晰或有错误**:
```json
{
  "errors": [
    {
      "message": "图像有错误或不清晰",
      "extensions": {
        "code": "IMG__ERROR"
      }
    }
  ]
}
```

**OCR识别失败**:
```json
{
  "errors": [
    {
      "message": "OCR解析失败",
      "extensions": {
        "code": "OCR__ERROR"
      }
    }
  ]
}
```

#### 特殊处理逻辑

1. **血压完整性验证**: 血压数据必须包含收缩压、舒张压、心率三个完整参数
2. **智能单位转换**: 自动识别血糖单位并转换为统一的mmol/L格式
3. **数据清洗**: 根据设备类型自动删除无关数据字段
4. **Token使用计数**: 成功识别后自动更新Token使用次数
5. **执行时间监控**: 记录完整处理时间用于性能监控
6. **错误邮件通知**: 模型API调用失败时异步发送邮件通知

#### 📋 日志记录的字段包括：
● client_ip: 客户端IP地址
● token: 使用的token
● api_endpoint: API端点
● status: 请求状态 ('success', 'failed', 'not_relevant', 'error')
● file_upload_id: 文件上传ID（仅图像接口）
● file_name: 文件名（仅图像接口）
● file_size: 文件大小（仅图像接口）
● ai_usage: AI使用量（仅图像接口）
● error_message: 错误消息（失败时）
● error_code: 错误代码（失败时）



## dashboard功能
OCR 请求总数（可按日期范围、中心和设备类型筛选）
成功率和失败率（总体和每个中心）
失败原因细分
按使用情况排名靠前的中心
每个请求的平均处理时间
不同center的token使用统计