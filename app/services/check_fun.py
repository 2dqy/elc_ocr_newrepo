from fastapi.responses import JSONResponse
import re


def check_other_value_error(ocr_dict, current_date=None, client_ip=None, ai_usage_value=0, file_upload_id=None, file_name=None, file_size=0, token=None):
    """
    检查other_value字段是否包含错误代码（E或e）
    
    参数:
        ocr_dict: OCR识别结果字典
        current_date: 当前日期
        client_ip: 客户端IP
        ai_usage_value: AI使用量
        file_upload_id: 文件上传ID
        file_name: 文件名
        file_size: 文件大小
        token: 令牌
    返回:
        如果包含错误代码返回JSONResponse错误响应，否则返回None
    """
    if "data" in ocr_dict and ocr_dict["data"]:
        if "other_value" in ocr_dict["data"] and ocr_dict["data"]["other_value"]:
            other_value = str(ocr_dict["data"]["other_value"]).strip()
            if other_value and ('E' in other_value or 'e' in other_value):
                print(f"other_value包含错误代码: {other_value}")

                response_data = {
                    "meta": "error",
                    "data": {
                        "brand": "",
                        "measure_date": current_date or "",
                        "measure_time": "",
                        "category": "",
                        "blood_presure": {
                            "systolic": "",
                            "diastolic": "",
                            "pulse": ""
                        },
                        "blood_sugar": "",
                        "other_value": other_value,
                        "suggest": "圖片中包含錯誤代碼，請檢查設備或重新測量。",
                        "analyze_reliability": 0,
                        "status": "error",
                        "source_ip": client_ip or "",
                        "ai_usage": ai_usage_value,
                        "file_upload_id": file_upload_id or "",
                        "file_name": file_name or "",
                        "file_size": file_size,
                        "token": token or ""
                    }
                }
                return JSONResponse(content=response_data)
    return None


def check_blood_pressure_validity(ocr_dict, current_date=None, client_ip=None, ai_usage_value=0, file_upload_id=None, file_name=None, file_size=0, token=None):
    """
    检查血压数据是否有效（null值或0开头的值）
    
    参数:
        ocr_dict: OCR识别结果字典
        current_date: 当前日期
        client_ip: 客户端IP
        ai_usage_value: AI使用量
        file_upload_id: 文件上传ID
        file_name: 文件名
        file_size: 文件大小
        token: 令牌
    返回:
        如果血压数据无效返回JSONResponse错误响应，否则返回None
    """
    if "data" in ocr_dict and ocr_dict["data"]:
        if "category" in ocr_dict["data"] and ocr_dict["data"]["category"] == "blood_pressure":
            if "blood_pressure" in ocr_dict["data"] and ocr_dict["data"]["blood_pressure"]:
                bp_data = ocr_dict["data"]["blood_pressure"]

                def is_invalid_value(value):
                    """检查值是否无效（null、空、或以0开头）"""
                    if not value or value == "null":
                        return True
                    # 提取数字部分检查是否以0开头
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
                    print(
                        f"血压数据无效: sys={bp_data.get('sys')}, dia={bp_data.get('dia')}, pul={bp_data.get('pul')}")

                    response_data = {
                        "meta": "error",
                        "data": {
                            "brand": "",
                            "measure_date": current_date or "",
                            "measure_time": "",
                            "category": "blood_pressure",
                            "blood_presure": {
                                "systolic": bp_data.get("sys", ""),
                                "diastolic": bp_data.get("dia", ""),
                                "pulse": bp_data.get("pul", "")
                            },
                            "blood_sugar": "",
                            "other_value": "",
                            "suggest": "圖像有錯誤或不清晰，請重新測量或檢查設備。",
                            "analyze_reliability": 0,
                            "status": "error",
                            "source_ip": client_ip or "",
                            "ai_usage": ai_usage_value,
                            "file_upload_id": file_upload_id or "",
                            "file_name": file_name or "",
                            "file_size": file_size,
                            "token": token or ""
                        }
                    }
                    return JSONResponse(content=response_data)
    return None


def check_blood_pressure_fake_data(ocr_dict, current_date=None, client_ip=None, ai_usage_value=0, file_upload_id=None, file_name=None, file_size=0, token=None):
    """
    检查血压数据是否都是10的整倍数（可能是AI编造的数据）
    
    参数:
        ocr_dict: OCR识别结果字典
        current_date: 当前日期
        client_ip: 客户端IP
        ai_usage_value: AI使用量
        file_upload_id: 文件上传ID
        file_name: 文件名
        file_size: 文件大小
        token: 令牌
    返回:
        如果血压数据疑似编造返回JSONResponse错误响应，否则返回None
    """
    if "data" in ocr_dict and ocr_dict["data"]:
        if "category" in ocr_dict["data"] and ocr_dict["data"]["category"] == "blood_pressure":
            if "blood_pressure" in ocr_dict["data"] and ocr_dict["data"]["blood_pressure"]:
                bp_data = ocr_dict["data"]["blood_pressure"]

                def extract_number(value):
                    """从血压值中提取数字部分"""
                    if not value or value == "null":
                        return None
                    # 提取数字部分
                    match = re.match(r'^(\d+)', str(value).strip())
                    if match:
                        return int(match.group(1))
                    return None

                # 提取三个血压值的数字部分
                sys_num = extract_number(bp_data.get("sys"))
                dia_num = extract_number(bp_data.get("dia"))
                pul_num = extract_number(bp_data.get("pul"))

                # 检查是否都是有效数字且都是10的整倍数
                if (sys_num is not None and dia_num is not None and pul_num is not None and
                        sys_num % 10 == 0 and dia_num % 10 == 0 and pul_num % 10 == 0):
                    print(f"血压数据疑似编造: sys={sys_num}, dia={dia_num}, pul={pul_num} (都是10的整倍数)")

                    response_data = {
                        "meta": "error",
                        "data": {
                            "brand": "",
                            "measure_date": current_date or "",
                            "measure_time": "",
                            "category": "blood_pressure",
                            "blood_presure": {
                                "systolic": bp_data.get("sys", ""),
                                "diastolic": bp_data.get("dia", ""),
                                "pulse": bp_data.get("pul", "")
                            },
                            "blood_sugar": "",
                            "other_value": "",
                            "suggest": "圖像有問題或非真實圖像，請使用真實的醫療設備圖像。",
                            "analyze_reliability": 0,
                            "status": "error",
                            "source_ip": client_ip or "",
                            "ai_usage": ai_usage_value,
                            "file_upload_id": file_upload_id or "",
                            "file_name": file_name or "",
                            "file_size": file_size,
                            "token": token or ""
                        }
                    }
                    return JSONResponse(content=response_data)
    return None
