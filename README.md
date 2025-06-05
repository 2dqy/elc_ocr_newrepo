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

##### 2. 图像预处理
- 图像尺寸优化和压缩
- Base64编码转换
- 像素范围标准化

##### 3. AI识别分析
**使用模型**: DashScope qwen-vl-ocr-latest

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

**血压单位处理**:
- 收缩压/舒张压: 自动添加 `mmHg`
- 心率: 自动添加 `bpm`

**血糖单位处理**:
- 目标单位: `mmol/L`
- 自动单位转换: 当血糖值 > 20时，认为是mg/dL单位，自动除以18转换
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

#### 成功响应格式

**血压数据示例**:
```json
{
  "meta": "success",
  "data": {
    "brand": "Omron",
    "measure_date": "2024-01-15",
    "measure_time": "14:30:00",
    "category": "blood_pressure",
    "blood_pressure": {
      "sys": "120mmHg",
      "dia": "80mmHg", 
      "pul": "72bpm"
    },
    "suggest": "血压正常，请保持健康的生活方式",
    "analyze_reliability": 0.95,
    "status": "completed",
    "source_ip": "192.168.1.100",
    "ai_usage": 6270,
    "file_upload_id": "A1B2C3D4E5F6G7H8",
    "file_name": "blood_pressure.jpg",
    "file_size": 245760,
    "token": "abc123def456"
  }
}
```

**血糖数据示例**:
```json
{
  "meta": "success", 
  "data": {
    "brand": "Roche",
    "measure_date": "2024-01-15",
    "measure_time": "09:15:00",
    "category": "blood_sugar",
    "blood_sugar": "5.8mmol/L",
    "suggest": "血糖水平正常，建议继续保持良好的饮食习惯",
    "analyze_reliability": 0.92,
    "status": "completed",
    "source_ip": "192.168.1.100", 
    "ai_usage": 5840,
    "file_upload_id": "X9Y8Z7W6V5U4T3S2",
    "file_name": "blood_sugar.jpg",
    "file_size": 198432,
    "token": "xyz789uvw012"
  }
}
```

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

#### 技术栈
- **图像处理**: PIL/Pillow
- **API框架**: FastAPI
- **数据验证**: 多层验证机制

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

# OCR 模型切换功能说明

## 概述

本项目现在支持两种OCR模型：
- **千问模型 (Qwen)**: 阿里云百炼的 qwen-vl-ocr-0413 模型
- **OpenAI模型**: Azure OpenAI 的 gpt-4o 模型

## 配置方法

### 1. 环境变量配置

在 `.env` 文件中配置以下变量：

```bash
# 模型选择 (qwen 或 openai)
MODEL_TYPE=qwen

# 千问模型配置
DASHSCOPE_API_KEY=sk-your-dashscope-key

# OpenAI模型配置
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_MODEL=gpt-4o
```

### 2. 模型切换

#### 方法一：通过环境变量切换（推荐）
```bash
# 使用千问模型
MODEL_TYPE=qwen

# 使用OpenAI模型
MODEL_TYPE=openai
```

#### 方法二：代码中动态切换
```python
from app.services.model_fun import get_ocr_model

# 使用千问模型
qwen_model = get_ocr_model("qwen")

# 使用OpenAI模型
openai_model = get_ocr_model("openai")

# 使用默认模型（根据环境变量MODEL_TYPE）
default_model = get_ocr_model()
```

## 注意事项

1. **API密钥**: 确保相应模型的API密钥已正确配置
2. **网络连接**: 确保能够访问相应的API端点
3. **图像格式**: 支持常见的图像格式（JPEG、PNG等）
4. **文件大小**: OpenAI模型会自动压缩图像，千问模型建议控制在合理范围内
5. **错误处理**: 两种模型都有完善的错误处理机制

## 故障排除

### 常见问题

1. **模型创建失败**
   - 检查API密钥是否正确
   - 检查网络连接
   - 检查环境变量配置

2. **图像分析失败**
   - 检查图像文件是否损坏
   - 检查图像格式是否支持
   - 检查API配额是否充足

3. **返回结果格式错误**
   - 检查模型返回的原始数据
   - 查看日志中的错误信息
   - 确认提示词是否正确


# OpenAI 结构化输出实现

## 概述

本项目已将 OpenAI 模型从基于提示词的 JSON 输出转换为使用 OpenAI 的结构化输出功能。这种方法提供了更可靠和一致的数据提取。

## 主要变更

### 1. Pydantic 模型定义

在 `app/services/model_fun.py` 中添加了以下 Pydantic 模型：

```python
class BloodPressureData(BaseModel):
    sys: Optional[int] = None
    dia: Optional[int] = None
    pul: Optional[int] = None

class OCRData(BaseModel):
    brand: Optional[str] = None
    measure_date: Optional[str] = None
    measure_time: Optional[str] = None
    category: str  # "blood_pressure", "blood_sugar", "Not relevant", "error"
    blood_pressure: Optional[BloodPressureData] = None
    blood_sugar: Optional[str] = None
    other_value: Optional[str] = None
    suggest: Optional[str] = None
    analyze_reliability: Optional[float] = None
    status: Optional[str] = None

class OCRResponse(BaseModel):
    data: OCRData
```

### 2. API 调用更新

OpenAI 模型现在使用 `client.beta.chat.completions.parse()` 而不是 `client.chat.completions.create()`：

```python
response = self.client.beta.chat.completions.parse(
    model=self.deployment,
    messages=[...],
    response_format=OCRResponse,
    max_tokens=500,
)
```

### 3. 简化的提示词

由于使用了结构化输出，提示词不再需要指定 JSON 格式，而是专注于分析指令：

- 移除了 JSON 格式说明
- 简化了输出要求
- 保留了核心分析逻辑

### 4. 响应处理

`extract_result` 方法现在首先尝试从 `response.choices[0].message.parsed` 获取结构化数据，如果失败则回退到原有的 JSON 解析方法。


## 注意事项

1. 需要 OpenAI Python 库版本 >= 1.82.0
2. 结构化输出功能目前在 beta 阶段
3. 如果结构化解析失败，系统会自动回退到传统的 JSON 解析方法


## dashboard功能
OCR 请求总数（可按日期范围、中心和设备类型筛选）
成功率和失败率（总体和每个中心）
失败原因细分
按使用情况排名靠前的中心
每个请求的平均处理时间
不同center的token使用统计