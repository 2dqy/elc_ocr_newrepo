from datetime import datetime
import os
import time
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

import dashscope
import uvicorn
import random
import string

from app.models.database import Database
from app.services.token_fun import verify_token, update_token_usage, get_ip_prefix
from app.services.image_fun import process_image

from fastapi import APIRouter
router = APIRouter(prefix="/upload")


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

# 图像处理参数
MIN_PIXELS = int(os.getenv("MIN_PIXELS", 28 * 28 * 4))  # 最小像素阈值
MAX_PIXELS = int(os.getenv("MAX_PIXELS", 28 * 28 * 8192))  # 最大像素阈值
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 500 * 1024))  # 最大文件大小（500KB）

# 初始化数据库
db = Database()




@router.post("/image")
async def upload_image(
        request: Request,
        file: UploadFile = File(...),
        token: str = Form(...)
):
    """
    上传并分析单张医疗图像
    
    参数:
        file: 上传的图像文件
        token: 验证令牌
    返回:
        图像分析结果的JSON响应
    """
    # 开始计时
    start_time = time.time()

    # 检查token是否有效
    verify_token(token)

    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    # 获取时间戳
    timestamp = int(time.time())
    
    # 获取客户端IP地址
    client_ip = request.client.host if request.client else "unknown"
    
    # 生成文件上传ID
    file_upload_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # 检查文件是否为图像
    if not file.content_type.startswith("image/"):
        return JSONResponse(
            status_code=400,
            content={
                "errors": [
                    {
                        "messages": "唯有上载图像文件",
                        "extensions": {
                            "code": "UPLOAD_FILE_FAIL"}
                    }
                ]
            }
        )
    # 读取文件内容
    file_content = await file.read()

    # 检查文件大小
    if len(file_content) > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=400,
            content={
                "errors": [
                    {
                        "messages": "文件大小超过500KB制",
                        "extensions": {
                            "code": "UPLOAD_FILE_FAIL"}
                    }
                ]
            }
        )
    try:
        # 处理图像
        processed_image = process_image(file_content, MIN_PIXELS, MAX_PIXELS)

        # 图像的base64编码（用于API调用）
        image_base64 = base64.b64encode(processed_image).decode("utf-8")

        try:
            # 使用DashScope API进行OCR分析
            messages = [{
                "role": "user",
                "content": [{
                    "image": f"data:image/jpeg;base64,{image_base64}",
                    "min_pixels": MIN_PIXELS,
                    "max_pixels": MAX_PIXELS,
                    "enable_rotate": True
                },
                    {
                        "type": "text",
                        "text": """请仔细分析图像中的医疗数据，判断是血压计还是血糖仪的数据，并提取以下信息：

                    1. 设备类型判断：
                       - 血压计数据：收缩压(SYS)、舒张压(DIA)、心率(PUL)
                       - 血糖仪数据：血糖值
                    
                    2. 关注信息：
                       - 医疗设备品牌和型号
                       - 测量时间（从图片中提取，格式 HH:mm:ss，如果无法提取则返回 null）
                       - 测量数值
                    
                    请按照以下JSON格式返回数据：
                    "data": {
                            "brand": "设备品牌",
                            "measure_date": "当前日期",
                            "measure_time": "图片中的测量时间",
                            "category": "blood_pressure 或 blood_sugar",
                            "blood_pressure": {
                                "sys": "收缩压值",
                                "dia": "舒张压值",
                                "pul": "心率值"
                            },
                            "blood_sugar": {
                                "value": "血糖值"                           
                            },
                            "suggest": "基于数据的 AI 健康建议",
                            "analyze_reliability": 0.95,
                            "status": "分析状态（例如 'completed', 'failed'）",
                            }
                    注意事项：
                        1. 如果是血压数据，blood_sugar对象的所有字段设为null
                        2. 如果是血糖数据，blood_pressure对象的所有字段设为null
                        3. 时间必须从图片中提取，如果无法提取则返回null
                        4. 请根据数值给出专业的健康建议
                        5. 确保分析准确，不要捏造数据
                    """
                    }]
            }]

            # 调用DashScope API，使用环境变量中的API密钥
            response = dashscope.MultiModalConversation.call(
                api_key=DASHSCOPE_API_KEY,
                model='qwen-vl-ocr-latest',
                messages=messages
            )

            # 检查API响应状态
            if response.status_code == 200:
                print(response.usage)
                # print(response.output.choices[0].message.content)

                # 获取OCR结果并处理格式
                raw_result = response["output"]["choices"][0]["message"]["content"]
                # print(raw_result)

                # 处理新的返回格式：列表中包含字典，字典有'text'键
                if isinstance(raw_result, list) and len(raw_result) > 0 and 'text' in raw_result[0]:
                    # 提取text内容
                    text_content = raw_result[0]['text']
                else:
                    # 兼容旧格式，直接使用raw_result
                    text_content = raw_result

                # 移除代码块标记（如 ```json 和 ```）和多余的换行、缩进
                ocr_result = text_content.replace('```json', '').replace('```', '').strip()

                # 构建完整响应
                try:
                    # 将字符串转换为字典
                    import json
                    ocr_dict = json.loads(ocr_result)
                    # print(f"xxx\n{ocr_result}\n")
                    
                    # 确保data字段存在
                    if "data" not in ocr_dict:
                        ocr_dict = {"data": ocr_dict}
                    
                    # 添加后端获取的参数到data中
                    if ocr_dict["data"]:
                        # 替换日期为当前日期
                        ocr_dict["data"]["measure_date"] = current_date
                        
                        # 添加后端参数
                        ocr_dict["data"]["source_ip"] = client_ip
                        
                        # 计算AI使用情况
                        usage_info = response.usage
                        total_tokens = usage_info.get("total_tokens", 0)
                        ai_usage_value = total_tokens * 10
                        ocr_dict["data"]["ai_usage"] = ai_usage_value
                        
                        # 添加文件相关信息
                        ocr_dict["data"]["file_upload_id"] = file_upload_id
                        ocr_dict["data"]["file_name"] = file.filename
                        ocr_dict["data"]["file_size"] = len(file_content)
                        ocr_dict["data"]["token"] = token

                    # 根据category删除不需要的字段
                    if "data" in ocr_dict and ocr_dict["data"] and "category" in ocr_dict["data"]:
                        category = ocr_dict["data"]["category"]
                        if category == "blood_pressure":
                            # 血压数据，删除blood_sugar字段
                            if "blood_sugar" in ocr_dict["data"]:
                                del ocr_dict["data"]["blood_sugar"]
                        elif category == "blood_sugar":
                            # 血糖数据，删除blood_pressure字段
                            if "blood_pressure" in ocr_dict["data"]:
                                del ocr_dict["data"]["blood_pressure"]
                    
                    # 打印最终处理结果
                    print("=== 最终处理结果 ===")
                    print(json.dumps(ocr_dict, ensure_ascii=False, indent=2))
                    print("==================")

                    response_data = {
                        "meta": ocr_dict.get("status", "success"),
                        "data": ocr_dict["data"],

                    }

                    # 如果OCR识别成功，更新token使用次数
                    if ocr_dict.get("status") == "success" or ocr_dict["data"].get("status") == "completed":
                        update_token_usage(token)
                except Exception as parse_error:
                    # 处理API错误
                    response_data = {
                        "errors": [
                            {
                                "message": f"OCR解析失败",
                                "extensions": {
                                    "code": "OCR__ERROR"
                                }
                            }
                        ]
                    }
            else:
                # 处理API错误
                response_data = {
                    "errors": [
                        {
                            "message": f"OCR API调用错误",
                            "extensions": {
                                "code": "OCR_API_ERROR"
                            }
                        }
                    ]
                }
                print(f"API错误: {response.code} - {response.message}")

        except Exception as api_error:
            # 处理API调用错误
            response_data = {
                "errors": [
                    {
                        "message": f"OCR API调用错误: {str(api_error)}",
                        "extensions": {
                            "code": "OCR_API_ERROR"
                        }
                    }
                ]
            }

        # 计算执行时间
        execution_time = time.time() - start_time
        print(f"处理完成，执行时间: {execution_time:.2f}秒")

        # 将执行时间添加到响应中
        # response_data["execution_time"] = f"{execution_time:.2f}秒"

        return JSONResponse(content=response_data)

    except Exception as e:
        # 处理可能发生的错误
        print(f"处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"UPLOAD_FILE_FAIL: {str(e)}")


@router.post("/add_token")
async def add_token(request: Request, token_data: dict):
    """        
    - token: 可選，使用者自填token，如果為空則自動生成
    - use_times: 可選，token可使用次數，如果為空則預設為10次
    - center_id: 必填，中心ID

 返回:
 包含新建token資訊的字典
    """
    # 查询数据库中的 IP 白名单
    db = Database()
    allowed_ips = db.get_allowed_ips()
    ALLOWED_IPS = allowed_ips if allowed_ips else []
    print("ALLOWED_IPS:", ALLOWED_IPS)

    # 获取客户端 IP
    client_ip = request.client.host if request.client else None
    print("client_ip:", client_ip)

    # 验证center_id是否存在
    if "center_id" not in token_data:
        return JSONResponse(
            status_code=403,
            content={
                "errors": [{
                    "message": "center_id为必填項",
                    "extensions": {
                        "code": "FORBIDDEN",
                    }
                }]
            }
        )

    center_id = token_data["center_id"]
    if not db.center_id_exists(center_id):
        return JSONResponse(
            status_code=403,
            content={
                "errors": [
                    {
                        "message": "You don't have permission to \"create\" from collection \"tokenCreate\" or it does not exist.",
                        "extensions": {
                            "reason": "You don't have permission to \"create\" from collection \"tokenCreate\" or it does not exist.",
                            "code": "FORBIDDEN"
                        }
                    }
                ]
            })

    # IP 验证：检查前三位是否匹配
    if not client_ip:
        return JSONResponse(
            status_code=403,
            content={
                "errors": [{
                    "message": "無法獲取客戶端 IP",
                    "extensions": {"code": "IP_DENY"}
                }]
            }
        )

    client_prefix = get_ip_prefix(client_ip)
    allowed_prefixes = [get_ip_prefix(ip) for ip in ALLOWED_IPS]
    if client_prefix not in allowed_prefixes:
        return JSONResponse(
            status_code=403,
            content={
                "errors": [{
                    "message": "IP 使用有限制",
                    # "extensions": {"code": "IP_DENY", "reason": "请联系info@2dqy.com或bob@2dqy.com"}
                }]
            }
        )

    # 获取并处理token参数
    token = token_data.get("token", '')

    # 如果token为空或不存在，生成10位随机字母数字组合的token
    if not token:
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    # 如果token包含非字母数字字符，返回HTTP错误400
    elif not token.isalnum():
        return JSONResponse(
            status_code=400,
            content={
                "errors": [{
                    "message": "Token只能包含字母和數字",
                    "extensions": {
                        "code": "TOKEN_INVALID",
                    }
                }]
            }
        )

    # 获取并处理use_times参数，默认值为10
    use_times = token_data.get("use_times", 10)

    # 检查 token 是否存在
    if db.token_exists(token):
        return JSONResponse(
            status_code=400,
            content={
                "errors": [
                    {
                        "messages": "Token 名稱重複",
                        "extensions": {
                            "code": "TOKEN_EXIST"
                        }
                    }
                ]
            }
        )

    # 插入新token
    try:
        db.add_token(token, use_times, center_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "errors": [
                    {
                        "message": str(e),
                        "extensions": {
                            "code": "TOKEN_EXIST"
                        }
                    }
                ]
            }
        )

    # 返回成功创建的token信息
    return {
        "data": {
            "id": db.cursor.lastrowid,
            "token": token,
            "use_times": use_times,
        }
    }


@router.post("/html")
async def read_root():
    """返回HTML首页"""
    file_path = Path(__file__).resolve().parent.parent.parent / "static" / "index.html"
    return FileResponse(file_path)


# 原来的健康检查接口改为新的路径
@router.post("/")
async def health_check():
    from datetime import datetime
    return {
        "status": "server測試成功",
        "server_time": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # 启动FastAPI应用
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
