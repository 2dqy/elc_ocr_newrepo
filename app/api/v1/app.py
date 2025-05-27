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
from app.services.image_fun import process_image, compress_image
from app.services.check_fun import check_other_value_error, check_blood_pressure_validity, check_blood_pressure_fake_data
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
    try:
        verify_token(token)
    except HTTPException as e:
        # 将HTTPException转换为JSONResponse
        return JSONResponse(
            status_code=e.status_code,
            content=e.detail
        )

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

    # 检查文件大小，如果超过限制则尝试压缩
    if len(file_content) > MAX_FILE_SIZE:
        # 尝试压缩图像
        compressed_content = compress_image(file_content, MAX_FILE_SIZE // 1024)
        if compressed_content is None:
            return JSONResponse(
                status_code=400,
                content={
                    "errors": [
                        {
                            "messages": "文件太大無法壓縮",
                            "extensions": {
                                "code": "UPLOAD_FILE_FAIL"}
                        }
                    ]
                }
            )
        # 使用压缩后的内容
        file_content = compressed_content
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
                        "text": """
                    請仔細分析上傳的圖像，執行以下步驟並傳回結果：
                    1. 圖片相關性判斷：
                    - 先判斷影像是否包含血壓計或血糖儀的顯示器或資料。 
                    - 如果影像不包含血壓計或血糖儀相關內容（例如，風景照、人物照或其他無關圖片），請依照以下JSON格式傳回資料，並忽略後續步驟：
                         {
                           "data": {
                             "category": "Not relevant"
                           }
                         }
                         
                    2. **錯誤狀態檢查**：
                    - 嚴禁根據常識、經驗或推測填寫任何資料，所有欄位只能根據圖片內容填寫，否則設為 null。
                    - 若圖片顯示錯誤訊息（如 E1、E2、Err、Error），僅回傳如下 JSON，所有數值設為 null，不要填預設值：
                         {
                           "data": {
                             "category": "error",
                             "error_message": "識別到的錯誤訊息（如 E1、Err 或無法識別）",
                             "brand": null,
                             "measure_date": null,
                             "measure_time": null,
                             "blood_pressure": {
                               "sys": null,
                               "dia": null,
                               "pul": null
                             },
                             "blood_sugar": null,
                             "other_value": null,
                             "suggest": "設備顯示錯誤訊息，請檢查設備是否正確操作或重新測量。",
                             "analyze_reliability": 0.0,
                             "status": "error_detected"
                           }
                         }
                    3. 設備類型與嚴禁根據推測或常識填寫任何數值，只能根據圖片內容識別資料，無法識別時設為 null。
                     - 嚴禁根據常識、經驗或推測填寫任何資料，所有欄位只能根據圖片內容填寫，否則設為 null。
                     - 血糖儀數據：血糖值
                     - 血壓計資料：收縮壓(SYS)、舒張壓(DIA)、心率(PUL)
                     - 如果無法從圖片中清晰識別數值，則相關字段必須設為 null。


                    4. 關注訊息：
                     - 嚴禁根據常識、經驗或推測填寫任何資料，所有欄位只能根據圖片內容填寫，否則設為 null。
                     - 醫療設備品牌和型號
                     - 測量時間（從圖片中提取，格式 HH:mm:ss，如果無法提取則返回 null）
                     - 健康建議必須根據提取到的數值給出，若數值無效則建議重新測量。
                    
                    5. 請依照以下JSON格式傳回資料，嚴禁根據常識、經驗或推測填寫任何資料，所有欄位只能根據圖片內容填寫，否則設為 null。：
                    
                         "data": {
                             "brand": "設備品牌",
                             "measure_date": "目前日期",
                             "measure_time": "圖片中的測量時間",
                             "category": "blood_pressure 或 blood_sugar",
                             "blood_pressure": {
                                 "sys": "收縮壓值",
                                 "dia": "舒張壓值",
                                 "pul": "心率值"
                             },
                             "blood_sugar": "血糖值",
                             "other_value": "其他資料",
                             "suggest": "基於數據的 AI 健康建議",
                             "analyze_reliability": ,
                             "status": "分析狀態（例如 'completed', 'failed'）",
                         }
                   注意事項：
                         1. 確保分析準確，不要捏造數據
                         2. 如果是血壓數據，blood_sugar字段設為null
                         3. 如果是血糖數據，blood_pressure物件的所有欄位設為null
                         4. 時間必須從圖片中提取，如果無法提取則返回null
                         5. 健康建議需基於提取的數值，提供專業且合理的建議
                         6. 若圖片顯示血壓計或血糖儀的錯誤訊息，則設置 category 為 "error"，並按照步驟 2 的 JSON 格式返回。
                         7. 若圖片不包含血壓計或血糖儀數據，則設置 category 為 "Not relevant"。
                         8. 用繁体中文回答
                         9. 嚴禁根據常識、經驗或推測填寫任何資料，所有欄位只能根據圖片內容填寫，否則設為 null。
                         10. 僅允許返回規定格式的 JSON，不得有多餘欄位或格式錯誤。
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
                        # 计算AI使用情况
                        usage_info = response.usage
                        total_tokens = usage_info.get("total_tokens", 0)
                        ai_usage_value = total_tokens * 10

                        # # 检查other_value字段是否包含错误代码（E或e）
                        # error_response = check_other_value_error(
                        #     ocr_dict, current_date, client_ip, ai_usage_value,
                        #     file_upload_id, file.filename, len(file_content), token
                        # )
                        # if error_response:
                        #     return error_response

                        # 检查血压数据有效性
                        error_response = check_blood_pressure_validity(
                            ocr_dict, current_date, client_ip, ai_usage_value, 
                            file_upload_id, file.filename, len(file_content), token
                        )
                        if error_response:
                            return error_response
                            
                        # 检测是否是ai编造数据或非真实数据
                        error_response = check_blood_pressure_fake_data(
                            ocr_dict, current_date, client_ip, ai_usage_value, 
                            file_upload_id, file.filename, len(file_content), token
                        )
                        if error_response:
                            return error_response

                        # 替换日期为当前日期
                        ocr_dict["data"]["measure_date"] = current_date

                        # 添加后端参数
                        ocr_dict["data"]["source_ip"] = client_ip
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
                                            value_str = re.sub(re.escape(unit), '', value_str,
                                                               flags=re.IGNORECASE).strip()
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
