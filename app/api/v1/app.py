# ===== 标准库 =====
import os
import time
import base64
import random
import string
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# ===== 第三方库 =====
from dotenv import load_dotenv
from fastapi import APIRouter, Request, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import dashscope  # 如果是阿里云多模态 SDK，可以留下

# ===== 本地模块（数据库 & 配置）=====
from app.core.config import settings
from app.models.database import Database, APILogRepository

# ===== 本地模块（服务函数）=====
from app.services.token_fun import (
    verify_token,
    update_token_usage,
    get_ip_prefix,
    get_token_use_times,
)
from app.services.image_fun import (
    process_image,
    correct_image_orientation,
    crop_and_compress_image

)
from app.services.check_fun import (
    check_other_value_error,
    check_blood_pressure_validity,
    check_blood_pressure_fake_data,
)
from app.services.model_fun import get_ocr_model

# ===== 日志 =====
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
        image: UploadFile = File(...),
        token: str = None
):
    """
    上传并分析单张医疗图像

    参数:
        file: 上传的图像文件
        token: 验证令牌（通过URL参数传递）
    返回:
        图像分析结果的JSON响应
    """
    # 从URL参数获取token
    if not token:
        token = request.query_params.get('token')

    if not token:
        return JSONResponse(
            status_code=400,
            content={
                "errors": [{
                    "message": "token不存在",
                    "extensions": {
                        "code": "MISSING_TOKEN"
                    }
                }]
            }
        )

    # 开始计时
    start_time = time.time()

    file = image
    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    # 获取客户端IP地址
    client_ip = request.client.host if request.client else "unknown"
    # 检查token是否有效
    try:
        verify_token(token)
    except HTTPException as e:
        # 记录API日志 - token验证失败
        try:
            error_detail = e.detail if isinstance(e.detail, dict) else {"message": str(e.detail)}
            error_message = error_detail.get("errors", [{}])[0].get("message",
                                                                    "token验证失败") if "errors" in error_detail else "token验证失败"
            error_code = error_detail.get("errors", [{}])[0].get("extensions", {}).get("code",
                                                                                       "TOKEN_ERROR") if "errors" in error_detail else "TOKEN_ERROR"

            # 获取token当前使用次数（验证失败时可能为0）
            current_use_times = get_token_use_times(token)

            APILogRepository.log_api_request(
                client_ip=client_ip,
                token=token,
                api_endpoint="/upload/image",
                status="failed",
                error_message=error_message,
                error_code=error_code,
                token_usetimes=current_use_times
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

        # 将HTTPException转换为JSONResponse
        return JSONResponse(
            status_code=e.status_code,
            content=e.detail
        )

    # 生成文件上传ID
    file_upload_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # 检查文件是否为图像
    if not file.content_type.startswith("image/"):
        # 记录API日志 - 文件格式错误
        try:
            # 获取token当前使用次数
            current_use_times = get_token_use_times(token)

            APILogRepository.log_api_request(
                client_ip=client_ip,
                token=token,
                api_endpoint="/upload/image",
                status="failed",
                file_upload_id=file_upload_id,
                file_name=file.filename,
                error_message="唯有上载图像文件",
                error_code="UPLOAD_FILE_FAIL",
                token_usetimes=current_use_times
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - 文件大小超限
        try:
            # 获取token当前使用次数
            current_use_times = get_token_use_times(token)

            APILogRepository.log_api_request(
                client_ip=client_ip,
                token=token,
                api_endpoint="/upload/image",
                status="failed",
                file_upload_id=file_upload_id,
                file_name=file.filename,
                file_size=len(file_content),
                error_message="文件大小超过1mb限制",
                error_code="UPLOAD_FILE_FAIL",
                token_usetimes=current_use_times
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

        return JSONResponse(
            status_code=400,
            content={
                "errors": [
                    {
                        "messages": "文件大小超过500KB限制",
                        "extensions": {
                            "code": "UPLOAD_FILE_FAIL"}
                    }
                ]
            }
        )
    try:
        # 获取OCR模型实例（根据环境变量MODEL_TYPE选择模型）
        ocr_model = get_ocr_model()

        # 根据模型类型处理图像
        model_type = os.getenv("MODEL_TYPE", "qwen").lower()
        if model_type == "qwen":
            # 千问模型使用处理后的图像
            processed_image = process_image(file_content, MIN_PIXELS, MAX_PIXELS)
            image_for_analysis = processed_image
        else:
            # OpenAI模型使用原始图像（在模型内部进行压缩）
            image_for_analysis = file_content

        try:
            #对图像外围20%的像素进行裁剪
            # image_for_analysis = crop_and_compress_image(image_for_analysis, target_size_ratio=0.8)


            # 使用统一的OCR模型接口进行分析
            ocr_dict, usage_info = ocr_model.analyze_image(image_for_analysis, file.filename)

            # 检查是否有错误
            if "error" in ocr_dict:
                # 记录API日志 - OCR分析失败
                try:
                    current_use_times = get_token_use_times(token)
                    APILogRepository.log_api_request(
                        client_ip=client_ip,
                        token=token,
                        api_endpoint="/upload/image",
                        status="failed",
                        file_upload_id=file_upload_id,
                        file_name=file.filename,
                        file_size=len(file_content),
                        error_message=ocr_dict["error"],
                        error_code="OCR_ERROR",
                        token_usetimes=current_use_times
                    )
                except Exception as log_error:
                    print(f"记录API日志失败: {str(log_error)}")

                response_data = {
                    "errors": [
                        {
                            "message": ocr_dict["error"],
                            "extensions": {
                                "code": "OCR_ERROR"
                            }
                        }
                    ]
                }
                return JSONResponse(content=response_data)

            # 输出日志
            logging.info(f"OCR分析结果: {ocr_dict}")
            logging.info(f"Usage信息: {usage_info}")

            # 检查category字段是否为"Not relevant"
            if ocr_dict["data"] and ocr_dict["data"].get("category") == "Not relevant":
                # 计算AI使用情况
                total_tokens = usage_info.get("total_tokens", 0)
                ai_usage_value = total_tokens * 10 if total_tokens > 0 else 100

                # 记录API日志 - 图像不相关
                try:
                    # 获取token当前使用次数
                    current_use_times = get_token_use_times(token)

                    APILogRepository.log_api_request(
                        client_ip=client_ip,
                        token=token,
                        api_endpoint="/upload/image",
                        status="not_relevant",
                        file_upload_id=file_upload_id,
                        file_name=file.filename,
                        file_size=len(file_content),
                        ai_usage=ai_usage_value,
                        error_message="图像不相关",
                        error_code="IMG__ERROR",
                        token_usetimes=current_use_times
                    )
                except Exception as log_error:
                    print(f"记录API日志失败: {str(log_error)}")

                response_data = {
                    "errors": [
                        {
                            "message": f"图像不相关",
                            "extensions": {
                                "code": "IMG__ERROR"
                            }
                        }
                    ]
                }
                return JSONResponse(content=response_data)

            # 添加后端获取的参数到data中
            if ocr_dict["data"]:
                # 计算AI使用情况
                total_tokens = usage_info.get("total_tokens", 0)
                ai_usage_value = total_tokens * 10 if total_tokens > 0 else 100

                print(f"AI Usage计算: total_tokens={total_tokens}, ai_usage_value={ai_usage_value}")

                # 检查数据有效性
                error_response = check_blood_pressure_validity(
                    ocr_dict, current_date, client_ip, ai_usage_value,
                    file_upload_id, file.filename, len(file_content), token
                )
                if error_response:
                    # 记录API日志 - 血压数据验证失败
                    try:
                        # 获取token当前使用次数
                        current_use_times = get_token_use_times(token)
                        device_type = ocr_dict["data"]["category"]

                        APILogRepository.log_api_request(
                            client_ip=client_ip,
                            token=token,
                            api_endpoint="/upload/image",
                            status="failed",
                            file_upload_id=file_upload_id,
                            file_name=file.filename,
                            file_size=len(file_content),
                            ai_usage=ai_usage_value,
                            error_message="数据验证失败",
                            error_code="BLOOD_PRESSURE_INVALID",
                            token_usetimes=current_use_times,
                            device_type=device_type,
                        )
                    except Exception as log_error:
                        print(f"记录API日志失败: {str(log_error)}")
                    return error_response

                # 检测是否是ai编造数据或非真实数据
                error_response = check_blood_pressure_fake_data(
                    ocr_dict, current_date, client_ip, ai_usage_value,
                    file_upload_id, file.filename, len(file_content), token
                )
                if error_response:
                    # 记录API日志 - 血压数据疑似编造
                    try:
                        # 获取token当前使用次数
                        current_use_times = get_token_use_times(token)
                        device_type = ocr_dict["data"]["category"]

                        APILogRepository.log_api_request(
                            client_ip=client_ip,
                            token=token,
                            api_endpoint="/upload/image",
                            status="failed",
                            file_upload_id=file_upload_id,
                            file_name=file.filename,
                            file_size=len(file_content),
                            ai_usage=ai_usage_value,
                            error_message="血压数据疑似编造",
                            error_code="BLOOD_PRESSURE_FAKE",
                            token_usetimes=current_use_times,
                            device_type=device_type,

                        )
                    except Exception as log_error:
                        print(f"记录API日志失败: {str(log_error)}")
                    return error_response

                # 替换日期为当前日期
                ocr_dict["data"]["measure_date"] = current_date

                # 添加后端参数
                ocr_dict["data"]["source_ip"] = client_ip

                # 设置AI使用情况
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

            # 规范血压命名systolic，diastolic，pulse
            if "blood_pressure" in ocr_dict["data"] and ocr_dict["data"]["blood_pressure"]:
                bp_data = ocr_dict["data"]["blood_pressure"]
                new_bp_data = {}

                # 处理收缩压 (sys -> systolic)
                if "sys" in bp_data and bp_data["sys"]:
                    sys_value = str(bp_data["sys"]).strip()
                    # 移除可能的单位
                    units_to_remove = ["mmHg", "mmhg", "kPa", "kpa", "mmol/L", "mg/dL", "mg/dl", "mmol", "mg", "/min",
                                       "min", "/"]
                    for unit in units_to_remove:
                        if unit.lower() in sys_value.lower():
                            import re
                            sys_value = re.sub(re.escape(unit), '', sys_value, flags=re.IGNORECASE).strip()
                    try:
                        new_bp_data["systolic"] = int(float(sys_value))
                    except (ValueError, TypeError):
                        new_bp_data["systolic"] = bp_data["sys"]

                # 处理舒张压 (dia -> diastolic)
                if "dia" in bp_data and bp_data["dia"]:
                    dia_value = str(bp_data["dia"]).strip()
                    # 移除可能的单位
                    for unit in units_to_remove:
                        if unit.lower() in dia_value.lower():
                            import re
                            dia_value = re.sub(re.escape(unit), '', dia_value, flags=re.IGNORECASE).strip()
                    try:
                        new_bp_data["diastolic"] = int(float(dia_value))
                    except (ValueError, TypeError):
                        new_bp_data["diastolic"] = bp_data["dia"]

                # 处理心率 (pul -> pulse)
                if "pul" in bp_data and bp_data["pul"]:
                    pul_value = str(bp_data["pul"]).strip()
                    # 移除可能的单位
                    for unit in units_to_remove:
                        if unit.lower() in pul_value.lower():
                            import re
                            pul_value = re.sub(re.escape(unit), '', pul_value, flags=re.IGNORECASE).strip()
                    try:
                        new_bp_data["pulse"] = int(float(pul_value))
                    except (ValueError, TypeError):
                        new_bp_data["pulse"] = bp_data["pul"]

                # 更新血压数据
                ocr_dict["data"]["blood_pressure"] = new_bp_data
                print(f"血压数据规范化: {bp_data} -> {new_bp_data}")

            # 处理血糖单位和转换
            if "blood_sugar" in ocr_dict["data"] and ocr_dict["data"]["blood_sugar"]:
                bs_value = ocr_dict["data"]["blood_sugar"]
                other_value = ocr_dict["data"].get("other_value", "")

                if bs_value and bs_value != "null":
                    try:
                        # 提取数值部分（去除可能的单位）
                        value_str = str(bs_value).strip()
                        print(f"原始血糖值: '{value_str}'")
                        print(f"other_value: '{other_value}'")

                        # 检查是否包含mg单位（从blood_sugar或other_value中）
                        has_mg_unit = False
                        if "mg" in value_str.lower() or (other_value and "mg" in str(other_value).lower()):
                            has_mg_unit = True
                            print(f"检测到mg单位")

                        # 移除已有的单位标识（先移除长单位，再移除短单位，避免部分匹配）
                        units_to_remove = ["mmol/L", "mg/dL", "mg/dl", "mmol", "mg", "/min", "min", "/"]
                        for unit in units_to_remove:
                            if unit.lower() in value_str.lower():
                                # 不区分大小写移除单位
                                import re
                                value_str = re.sub(re.escape(unit), '', value_str,
                                                   flags=re.IGNORECASE).strip()
                                print(f"移除单位 '{unit}' 后: '{value_str}'")

                        blood_sugar_value = float(value_str)
                        print(f"提取的数值: {blood_sugar_value}")

                        # 根据是否检测到mg单位来决定转换方式
                        if has_mg_unit:
                            # 检测到mg单位，使用标准转换（除以18）
                            blood_sugar_value = blood_sugar_value / 18
                            print(f"血糖单位转换(mg->mmol/L): {bs_value} -> {blood_sugar_value:.1f}mmol/L")

                        # 添加mmol/L单位
                        ocr_dict["data"]["blood_sugar"] = f"{blood_sugar_value:.1f}mmol/L"

                    except (ValueError, TypeError) as e:
                        print(f"血糖值转换错误: {bs_value} - {str(e)}")
                        # 如果转换失败，直接添加单位
                        if not str(bs_value).endswith("mmol/L"):
                            ocr_dict["data"]["blood_sugar"] = f"{bs_value}mmol/L"

            # 打印最终处理结果
            print("=== 最终处理结果 ===")
            import json
            print(json.dumps(ocr_dict, ensure_ascii=False, indent=2))
            print("==================")

            response_data = {
                "meta": ocr_dict.get("status", "success"),
                "data": ocr_dict["data"],
            }

            # 如果OCR识别成功，更新token使用次数
            if (ocr_dict.get("data") and
                    ocr_dict["data"].get("category") not in ["Not relevant", "error", None]):
                update_token_usage(token)
                print(f"Token使用次数已更新: {token}")
            else:
                print(f"Token使用次数未更新，条件不满足: category={ocr_dict.get('data', {}).get('category')}")

            # 记录API日志 - 成功情况
            try:
                log_status = "success"
                if ocr_dict["data"].get("category") == "Not relevant":
                    log_status = "not_relevant"
                elif ocr_dict["data"].get("category") == "error":
                    log_status = "error"

                # 获取token当前使用次数
                current_use_times = get_token_use_times(token)
                device_type = ocr_dict["data"]["category"]
                api_execution_time = time.time() - start_time
                processing_time = Decimal(api_execution_time).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                APILogRepository.log_api_request(
                    client_ip=client_ip,
                    token=token,
                    api_endpoint="/upload/image",
                    status=log_status,
                    file_upload_id=file_upload_id,
                    file_name=file.filename,
                    file_size=len(file_content),
                    ai_usage=ocr_dict["data"].get("ai_usage", 0),
                    token_usetimes=current_use_times,
                    device_type=device_type,
                    processing_time=processing_time

                )
            except Exception as log_error:
                print(f"记录API日志失败: {str(log_error)}")

        except Exception as parse_error:
            # 处理解析错误
            response_data = {
                "errors": [
                    {
                        "message": f"OCR解析失败: {str(parse_error)}",
                        "extensions": {
                            "code": "OCR_PARSE_ERROR"
                        }
                    }
                ]
            }

            # 记录API日志 - 解析失败
            try:
                # 获取token当前使用次数
                current_use_times = get_token_use_times(token)

                APILogRepository.log_api_request(
                    client_ip=client_ip,
                    token=token,
                    api_endpoint="/upload/image",
                    status="failed",
                    file_upload_id=file_upload_id,
                    file_name=file.filename,
                    file_size=len(file_content),
                    error_message=f"OCR解析失败: {str(parse_error)}",
                    error_code="OCR_PARSE_ERROR",
                    token_usetimes=current_use_times,

                )
            except Exception as log_error:
                print(f"记录API日志失败: {str(log_error)}")

        # 计算执行时间
        execution_time = time.time() - start_time
        print(f"处理完成，执行时间: {execution_time:.2f}秒")

        return JSONResponse(content=response_data)

    except Exception as e:
        # 记录API日志 - 系统异常
        try:
            # 获取token当前使用次数（如果token存在的话）
            current_use_times = 0
            if 'token' in locals() and token:
                current_use_times = get_token_use_times(token)

            APILogRepository.log_api_request(
                client_ip=client_ip if 'client_ip' in locals() else "unknown",
                token=token if 'token' in locals() else "",
                api_endpoint="/upload/image",
                status="failed",
                file_upload_id=file_upload_id if 'file_upload_id' in locals() else None,
                file_name=file.filename if 'file' in locals() and file else None,
                file_size=len(file_content) if 'file_content' in locals() else None,
                error_message=f"系统异常: {str(e)}",
                error_code="SYSTEM_ERROR",
                token_usetimes=current_use_times,
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - center_id缺失
        try:
            APILogRepository.log_api_request(
                client_ip=client_ip or "unknown",
                token="",
                api_endpoint="/upload/add_token",
                status="failed",
                error_message="center_id为必填項",
                error_code="FORBIDDEN",
                center_id=None
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - center_id不存在
        try:
            APILogRepository.log_api_request(
                client_ip=client_ip or "unknown",
                token="",
                api_endpoint="/upload/add_token",
                status="failed",
                error_message="center_id不存在",
                error_code="FORBIDDEN",
                center_id=center_id
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - 无法获取IP
        try:
            APILogRepository.log_api_request(
                client_ip="unknown",
                token="",
                api_endpoint="/upload/add_token",
                status="failed",
                error_message="無法獲取客戶端 IP",
                error_code="IP_DENY",
                center_id=center_id
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - IP受限
        try:
            APILogRepository.log_api_request(
                client_ip=client_ip,
                token="",
                api_endpoint="/upload/add_token",
                status="failed",
                error_message="IP 使用有限制",
                error_code="IP_DENY",
                center_id=center_id
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - token格式无效
        try:
            APILogRepository.log_api_request(
                client_ip=client_ip,
                token=token,
                api_endpoint="/upload/add_token",
                status="failed",
                error_message="Token只能包含字母和數字",
                error_code="TOKEN_INVALID",
                center_id=center_id
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - token已存在
        try:
            APILogRepository.log_api_request(
                client_ip=client_ip,
                token=token,
                api_endpoint="/upload/add_token",
                status="failed",
                error_message="Token 名稱重複",
                error_code="TOKEN_EXIST",
                center_id=center_id
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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
        # 记录API日志 - 插入token失败
        try:
            APILogRepository.log_api_request(
                client_ip=client_ip,
                token=token,
                api_endpoint="/upload/add_token",
                status="failed",
                error_message=str(e),
                error_code="TOKEN_EXIST",
                center_id=center_id
            )
        except Exception as log_error:
            print(f"记录API日志失败: {str(log_error)}")

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

    # 记录API日志 - 成功创建token
    try:
        APILogRepository.log_api_request(
            client_ip=client_ip,
            token=token,
            api_endpoint="/upload/add_token",
            status="success",
            token_usetimes=use_times,
            center_id=center_id
        )
    except Exception as log_error:
        print(f"记录API日志失败: {str(log_error)}")

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
