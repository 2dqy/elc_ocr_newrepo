from datetime import datetime
import os
import time
import base64
from dotenv import load_dotenv
from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import dashscope
import random
import string

from app.models.database import Database
from app.services.token_fun import verify_token, update_token_usage, get_ip_prefix
from app.services.image_fun import process_image
from app.core.config import settings
from fastapi import APIRouter
import logging

# 设置日志级别和格式（只需设置一次，通常放在脚本开头）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


router = APIRouter(prefix="/upload")

# 加载.env环境变量
load_dotenv()

# 获取API密钥和配置参数
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

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
                        "messages": "唯有上载圖像文件",
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
                        "text": """请仔细分析上传的图像，执行以下步骤并返回结果：

                    1. 图片相关性判断：
                       - 首先判断图像是否包含血压计或血糖仪的显示屏或数据。
                       - 如果图像不包含血压计或血糖仪相关内容（例如，风景照、人物照或其他无关图片），请按照以下JSON格式返回数据：
                            "data": {
                                    "category": "Not relevant"，
                                    }后续提示词可忽略                                 

                    2. 设备类型判断：
                       - 血糖仪数据：血糖值
                       - 血压计数据：收缩压(SYS)、舒张压(DIA)、心率(PUL)
                    
                    3. 关注信息：
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
                            "blood_sugar": "血糖值",
                            "other_value": "其他数据",
                            "suggest": "基于数据的 AI 健康建议",
                            "analyze_reliability": 0.95,
                            "status": "分析状态（例如 'completed', 'failed'）",
                            }
                    注意事项：
                        1. 如果是血压数据，blood_sugar字段设为null
                        2. 如果是血糖数据，blood_pressure对象的所有字段设为null
                        3. 时间必须从图片中提取，如果无法提取则返回null
                        4. 请根据数值给出专业的健康建议
                        5. 确保分析准确，不要捏造数据
                        6. 如果图片不包含血压计或血糖仪数据，设置category 为 "error"，其他值为空。

                    """
                    }]
            }]

            # 调用DashScope API，使用环境变量中的API密钥
            response = dashscope.MultiModalConversation.call(
                api_key=DASHSCOPE_API_KEY,
                model='qwen-vl-ocr-latest',
                messages=messages,
                temperature=0.2,
            )

            # 检查API响应状态
            if response.status_code == 200:
                # print(response.usage)
                # print(response.output.choices[0].message.content)
                # 输出日志
                logging.info(f"回應內容: {response}")

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

                    # 检查category字段是否为"Not relevant"
                    if ocr_dict["data"] and ocr_dict["data"].get("category") == "Not relevant":
                        response_data = {
                            "errors": [
                                {
                                    "message": f"圖像不相關",
                                    "extensions": {
                                        "code": "IMG__ERROR"
                                    }
                                }
                            ]
                        }
                        return JSONResponse(content=response_data)

                    # 添加后端获取的参数到data中
                    if ocr_dict["data"]:

                        # 判断血压是否有null值或0开头的值
                        if "category" in ocr_dict["data"] and ocr_dict["data"]["category"] == "blood_pressure":
                            if "blood_pressure" in ocr_dict["data"] and ocr_dict["data"]["blood_pressure"]:
                                bp_data = ocr_dict["data"]["blood_pressure"]
                                
                                def is_invalid_value(value):
                                    """检查值是否无效（null、空、或以0开头）"""
                                    if not value or value == "null":
                                        return True
                                    # 提取数字部分检查是否以0开头
                                    import re
                                    # 提取开头的数字部分
                                    match = re.match(r'^(\d+)', str(value).strip())
                                    if match:
                                        number_part = match.group(1)
                                        # 检查是否以0开头且不是单独的0（像00、01、02等都是无效的）
                                        if number_part.startswith('0') and len(number_part) > 1:
                                            return True
                                        # 检查是否就是0
                                        if number_part == '0':
                                            return True
                                    return False
                                
                                # 检查血压三个参数是否有无效值
                                if (is_invalid_value(bp_data.get("sys")) or 
                                    is_invalid_value(bp_data.get("dia")) or 
                                    is_invalid_value(bp_data.get("pul"))):
                                    
                                    print(f"血压数据无效: sys={bp_data.get('sys')}, dia={bp_data.get('dia')}, pul={bp_data.get('pul')}")
                                    
                                    response_data = {
                                        "errors": [
                                            {
                                                "message": f"圖像有錯誤或不清晰",
                                                "extensions": {
                                                    "code": "IMG__ERROR"
                                                }
                                            }
                                        ]
                                    }
                                    return JSONResponse(content=response_data)

                        
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

                    # 补充单位并统一
                    if "data" in ocr_dict and ocr_dict["data"]:
                        # 处理血压单位
                        if "blood_pressure" in ocr_dict["data"] and ocr_dict["data"]["blood_pressure"]:
                            bp_data = ocr_dict["data"]["blood_pressure"]
                            # 为血压值添加mmHg单位
                            if bp_data.get("sys") and bp_data["sys"] != "null":
                                if not bp_data["sys"].endswith("mmHg"):
                                    bp_data["sys"] = f"{bp_data['sys']}mmHg"
                            if bp_data.get("dia") and bp_data["dia"] != "null":
                                if not bp_data["dia"].endswith("mmHg"):
                                    bp_data["dia"] = f"{bp_data['dia']}mmHg"
                            if bp_data.get("pul") and bp_data["pul"] != "null":
                                if not bp_data["pul"].endswith("bpm"):
                                    bp_data["pul"] = f"{bp_data['pul']}bpm"

                        # 处理血糖单位和转换
                        if "blood_sugar" in ocr_dict["data"] and ocr_dict["data"]["blood_sugar"]:
                            bs_value = ocr_dict["data"]["blood_sugar"]
                            if bs_value and bs_value != "null":
                                try:
                                    # 提取数值部分（去除可能的单位）
                                    value_str = str(bs_value).strip()
                                    print(f"原始血糖值: '{value_str}'")
                                    
                                    # 移除已有的单位标识（先移除长单位，再移除短单位，避免部分匹配）
                                    units_to_remove = ["mmol/L", "mg/dL", "mg/dl", "mmol", "mg"]
                                    for unit in units_to_remove:
                                        if unit.lower() in value_str.lower():
                                            # 不区分大小写移除单位
                                            import re
                                            value_str = re.sub(re.escape(unit), '', value_str, flags=re.IGNORECASE).strip()
                                            print(f"移除单位 '{unit}' 后: '{value_str}'")

                                    blood_sugar_value = float(value_str)
                                    print(f"提取的数值: {blood_sugar_value}")

                                    # 如果血糖值大于20，认为是mg/dL单位，需要转换为mmol/L
                                    if blood_sugar_value > 20:
                                        blood_sugar_value = blood_sugar_value / 18
                                        print(f"血糖单位转换: {bs_value} -> {blood_sugar_value:.1f}mmol/L")

                                    # 添加mmol/L单位
                                    ocr_dict["data"]["blood_sugar"] = f"{blood_sugar_value:.1f}mmol/L"

                                except (ValueError, TypeError) as e:
                                    print(f"血糖值转换错误: {bs_value} - {str(e)}")
                                    # 如果转换失败，直接添加单位
                                    if not str(bs_value).endswith("mmol/L"):
                                        ocr_dict["data"]["blood_sugar"] = f"{bs_value}mmol/L"

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
                                "message": f"OCR解析失敗",
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
                            "message": f"OCR API呼叫錯誤",
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
                        "message": f"OCR API呼叫錯誤: {str(api_error)}",
                        "extensions": {
                            "code": "OCR_API_ERROR"
                        }
                    }
                ]
            }

        # 计算执行时间
        execution_time = time.time() - start_time
        print(f"處理完成，執行時間: {execution_time:.2f}秒")

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


@router.get("/html")
async def read_root():
    """返回HTML首页"""
    file_path = Path(__file__).resolve().parent.parent.parent / "static" / "index.html"
    return FileResponse(file_path)


@router.get("/config")
async def get_config():
    """获取前端配置"""
    return {
        "api_base_url": settings.API_BASE_URL
    }


# 原来的健康检查接口改为新的路径

