"""
支持qwen-vl-ocr-0413与gpt-4o
"""
import os
import base64
import io
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List
from PIL import Image, ExifTags
import dashscope
from openai import AzureOpenAI
from pydantic import BaseModel


# Pydantic models for structured output
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


class BaseOCRModel(ABC):
    """OCR模型基类"""
    
    @abstractmethod
    def analyze_image(self, image_content: bytes, filename: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """分析图像并返回结果"""
        pass
    
    @abstractmethod
    def extract_result(self, response: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """从API响应中提取结果和usage信息"""
        pass


class QwenOCRModel(BaseOCRModel):
    """千问OCR模型"""
    
    def __init__(self, api_key: str, min_pixels: int, max_pixels: int):
        self.api_key = api_key
        self.min_pixels = min_pixels
        self.max_pixels = max_pixels
        self.model = 'qwen-vl-ocr-0413'
    
    def analyze_image(self, image_content: bytes, filename: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """使用千问模型分析图像"""
        try:
            # 千问模型直接使用原始图像，不需要压缩
            image_base64 = base64.b64encode(image_content).decode("utf-8")
            
            messages = [{
                "role": "user",
                "content": [{
                    "image": f"data:image/jpeg;base64,{image_base64}",
                    "min_pixels": self.min_pixels,
                    "max_pixels": self.max_pixels,
                    "enable_rotate": True
                },
                {
                    "type": "text",
                    "text": self._get_qwen_prompt()
                }]
            }]
            
            response = dashscope.MultiModalConversation.call(
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                temperature=0.2,
            )
            
            ocr_result, _ = self.extract_result(response)
            
            # 提取千问模型的usage信息
            usage_info = {}
            if response.status_code == 200 and hasattr(response, 'usage'):
                usage_info = {
                    "total_tokens": response.usage.get("total_tokens", 0),
                    "prompt_tokens": response.usage.get("input_tokens", 0),
                    "completion_tokens": response.usage.get("output_tokens", 0)
                }
            
            return ocr_result, usage_info
            
        except Exception as e:
            return {"error": f"千问模型调用失败: {str(e)}"}, {}
    
    def extract_result(self, response: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """从千问API响应中提取结果"""
        try:
            if response.status_code != 200:
                return {"error": f"千问API调用错误: {response.code} - {response.message}"}, {}
            
            raw_result = response["output"]["choices"][0]["message"]["content"]
            
            # 处理新的返回格式：列表中包含字典，字典有'text'键
            if isinstance(raw_result, list) and len(raw_result) > 0 and 'text' in raw_result[0]:
                text_content = raw_result[0]['text']
            else:
                text_content = raw_result
            
            # 移除代码块标记
            ocr_result = text_content.replace('```json', '').replace('```', '').strip()
            
            # 解析JSON
            ocr_dict = json.loads(ocr_result)
            
            # 确保data字段存在
            if "data" not in ocr_dict:
                ocr_dict = {"data": ocr_dict}
            
            return ocr_dict, {}
            
        except Exception as e:
            return {"error": f"千问结果解析失败: {str(e)}"}, {}
    
    def _get_qwen_prompt(self) -> str:
        """获取千问模型的提示词"""
        return """请仔细分析上传的图像，执行以下步骤并返回结果：

1. 图片相关性判断：
   - 首先判断图像是否包含血压计或血糖仪的显示屏或数据。
   - 如果图像不包含血压计或血糖仪相关内容（例如，风景照、人物照或其他无关图片），请按照以下JSON格式返回数据：
        "data": {
                "category": "Not relevant"，
                }后续提示词可忽略                                 

2. 设备类型判断：
   - 血压计数据：收缩压(SYS)、舒张压(DIA)、心率(PUL)
   - 血糖仪数据：血糖值

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
    7. 如果一個大數字看起來明顯不合常理（如 179 mmol/L），請判斷是否可能是 17.9。
    8. 嘗試根據格式規律（血糖值通常介於 2.0 到 20.0）來做小數推論。
    9. 如果一個大數字看起來明顯不合常理（如 179 mmol/L），請判斷是否可能是 17.9。
    10. 注意小數點，錯了會世界末日。
    11. 嘗試根據格式規律（血糖值通常介於 0.0 到 20.0）來做小數推論。
    12. 這可能一張血糖測試儀的螢幕照片。請辨識畫面中的數字值，並注意數字中可能有小數點，尤其數值應該合理在 0 到 20 之間。請特別檢查「1.5」和「15」的差別，小數點若難以分辨，也請根據螢幕樣式或格式合理推斷
"""


class OpenAIOCRModel(BaseOCRModel):
    """OpenAI OCR模型"""
    
    def __init__(self, endpoint: str, api_key: str, api_version: str, deployment: str, model: str):
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key
        )
        self.deployment = deployment
        self.model = model
    
    def analyze_image(self, image_content: bytes, filename: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """使用OpenAI模型分析图像"""
        try:
            # OpenAI模型需要压缩图像
            compressed_image = self._compress_image(image_content, filename)
            image_data_uri = f"data:image/jpeg;base64,{compressed_image}"
            
            # 使用结构化输出
            response = self.client.beta.chat.completions.parse(
                model=self.deployment,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个专业的医疗设备图像分析助手。请仔细分析上传的图像并提取相关信息。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._get_openai_prompt()},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_data_uri, "detail": "low"},
                            },
                        ],
                    }
                ],
                response_format=OCRResponse,
                max_tokens=500,
            )
            
            ocr_result, _ = self.extract_result(response)
            
            # 提取OpenAI模型的usage信息
            usage_info = {}
            if hasattr(response, 'usage') and response.usage:
                usage_info = {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            
            return ocr_result, usage_info
            
        except Exception as e:
            return {"error": f"OpenAI模型调用失败: {str(e)}"}, {}
    
    def extract_result(self, response: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """从OpenAI API响应中提取结果"""
        try:
            # 从结构化输出中提取数据
            parsed_response = response.choices[0].message.parsed
            if parsed_response:
                # 将Pydantic模型转换为字典
                result_dict = parsed_response.model_dump()
                return result_dict, {}
            else:
                # 如果解析失败，尝试从content中提取
                content = response.choices[0].message.content
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result, {}
                else:
                    return {"error": "未找到有效的响应数据"}, {}
        except Exception as e:
            return {"error": f"OpenAI结果解析失败: {str(e)}"}, {}
    
    def _compress_image(self, image_content: bytes, filename: str, max_size: int = 1024) -> str:
        """压缩图像并转换为base64"""
        try:
            img = self._correct_image_orientation(image_content)
            img = img.convert("RGB")
            img.thumbnail((max_size, max_size))
            
            # 保存压缩后的图像（可选）
            # save_path = "compressed_images"
            # if not os.path.exists(save_path):
            #     os.makedirs(save_path)
            
            # compressed_file_path = os.path.join(save_path, f"compressed_{filename}")
            # img.save(compressed_file_path, format="JPEG")
            
            # 转换为base64
            img_byte_array = io.BytesIO()
            img.save(img_byte_array, format="JPEG")
            img_base64 = base64.b64encode(img_byte_array.getvalue()).decode("utf-8")

            # 打印压缩后的文件大小
            print(f"压缩后的文件大小: {len(img_base64)} bytes")
            return img_base64
            
        except Exception as e:
            print(f"图像压缩失败: {str(e)}")
            # 如果压缩失败，直接返回原始图像的base64
            return base64.b64encode(image_content).decode("utf-8")
    
    def _correct_image_orientation(self, image_content: bytes) -> Image.Image:
        """修正图片方向"""
        try:
            img = Image.open(io.BytesIO(image_content))
            # if hasattr(img, "_getexif"):
            #     exif = img._getexif()
            #     if exif:
            #         for orientation in ExifTags.TAGS:
            #             if ExifTags.TAGS[orientation] == "Orientation":
            #                 break
            #         if orientation in exif:
            #             if exif[orientation] == 3:
            #                 img = img.rotate(180, expand=True)
            #             elif exif[orientation] == 6:
            #                 img = img.rotate(270, expand=True)
            #             elif exif[orientation] == 8:
            #                 img = img.rotate(90, expand=True)
            #
            # print(f"修正後的圖片方向: {img.getexif().get(274)}")
            return img
        except Exception:
            return Image.open(io.BytesIO(image_content))
    
    def _get_openai_prompt(self) -> str:
        """获取OpenAI模型的提示词"""
        return """请仔细分析上传的图像，执行以下步骤：
1. **图片相关性判断**：
   - 判断图像是否包含血压计或血糖仪的显示屏或数据。
   - 重点识别七段数字显示屏（7-segment display），这是血压计和血糖仪常用的数字显示方式，具有以下特征：
     - 数字由七个线段组成（a: 顶部, b: 右上, c: 右下, d: 底部, e: 左下, f: 左上, g: 中间），可能包含小数点（通常显示为一个单独的点）。
     - 显示屏通常为单色（如红色、绿色、蓝色），对比度高，数字清晰。
     - 可能包含单位（如“mmHg”或“mmol/L”），但单位文字不是目标。
   - 忽略无关文字和数字，例如键盘上的按键数字（如“1”、“2”）、设备标签、品牌文字（非七段数字样式的文字）。
   - 如果图像不包含七段数字显示屏或相关数据，设置 category 为 "Not relevant"。

2. **设备类型判断**：
   - 血压计数据：通常显示三组数字，分别为收缩压（SYS）、舒张压（DIA）、心率（PUL），单位为 mmHg（SYS 和 DIA）和次/分钟（PUL）。
   - 血糖仪数据：通常显示单一血糖值，单位为 mmol/L。
   - 根据七段数字显示屏上的数据模式判断：
     - 如果显示三组数字（SYS、DIA、PUL），则为血压计，设置 category 为 "blood_pressure"。
     - 如果显示一组数字（血糖值），则为血糖仪，设置 category 为 "blood_sugar"。
   - 如果无法判断设备类型，设置 category 为 "error"。

3. **数据提取要求**：
   - **医疗设备品牌和型号**：
     - 从图像中提取品牌和型号（可能为非七段数字的文字，如“Omron”或“Accu-Chek”）。
     - 如果无法提取，设为 null。
   - **测量时间**：
     - 从图片中提取测量时间，格式为 HH:mm:ss。
     - 时间可能显示在七段数字显示屏附近（例如“12:34:56”）。
     - 如果无法提取时间，设为 null。
   - **测量数值**：
     - 聚焦于七段数字显示屏上的数字，忽略其他区域的数字或文字（例如键盘上的按键数字）。
     - 对于血压计：提取收缩压（SYS）、舒张压（DIA）、心率（PUL），单位分别为 mmHg 和次/分钟。
     - 对于血糖仪：提取血糖值，单位为 mmol/L。
     - **七段数字识别（特别注意 1 与 7、2 与 5 的混淆）**：
     - **小数点识别**：
       - 七段数字显示屏上的小数点通常为一个单独的点，位于数字之间（例如“1.5”显示为“1 . 5”）。
       - 血糖值通常在 2.0 到 20.0 mmol/L 之间，据此推断小数点位置：
         - 如果识别到“15”，但血糖值应在 2.0 到 20.0 之间，推断可能为“1.5”。
         - 如果识别到“179”，推断可能为“17.9”。
       - 注意：小数点识别错误会导致数值偏差（例如“1.5”误认为“15”），请根据血糖值范围和七段数字显示屏的点样式仔细判断。
       - 如果小数点难以分辨，根据七段数字的显示规律（点是否独立、点与数字的间距）合理推断。
     - 确保数值准确，不要编造数据。

4. **注意事项**：
   - 如果是血压数据，blood_sugar 字段设为 null。
   - 如果是血糖数据，blood_pressure 对象的所有字段（SYS、DIA、PUL）设为 null。
   - 时间必须从图片中提取，无法提取则返回 null。
   - 根据数值给出专业的健康建议：
     - 血压建议：参考正常范围（SYS: 90-120 mmHg，DIA: 60-80 mmHg，PUL: 60-100 次/分钟）。
     - 血糖建议：参考正常范围（空腹 3.9-6.1 mmol/L，餐后 <7.8 mmol/L）。
   - 如果图片不包含血压计或血糖仪的七段数字显示屏数据，设置 category 为 "error"。
   - 如果一个大数字明显不合常理（如“13-200 mmol/L”），根据血糖值范围（2.0 到 20.0 mmol/L）推断小数点位置：
     - 例如“15”可能是“1.5”，“179”可能是“17.9”。
   - 特别注意小数点和数字形态（1 与 7、2 与 5），错误识别可能导致严重偏差。
   - 优先识别七段数字显示屏上的数字，避免被其他区域的文字或数字干扰。
"""
class OCRModelFactory:
    """OCR模型工厂类"""
    
    @staticmethod
    def create_model(model_type: str, **kwargs) -> BaseOCRModel:
        """创建OCR模型实例"""
        if model_type.lower() == "qwen":
            return QwenOCRModel(
                api_key=kwargs.get("dashscope_api_key"),
                min_pixels=kwargs.get("min_pixels", 3136),
                max_pixels=kwargs.get("max_pixels", 6422528)
            )
        elif model_type.lower() == "openai":
            return OpenAIOCRModel(
                endpoint=kwargs.get("azure_openai_endpoint"),
                api_key=kwargs.get("azure_openai_api_key"),
                api_version=kwargs.get("azure_openai_api_version"),
                deployment=kwargs.get("azure_openai_deployment"),
                model=kwargs.get("azure_openai_model")
            )
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")


def get_ocr_model(model_type: str = None) -> BaseOCRModel:
    """获取OCR模型实例"""
    if model_type is None:
        model_type = os.getenv("MODEL_TYPE", "qwen")
    
    config = {
        "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY"),
        "min_pixels": int(os.getenv("MIN_PIXELS", 3136)),
        "max_pixels": int(os.getenv("MAX_PIXELS", 6422528)),
        "azure_openai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "azure_openai_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
        "azure_openai_api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        "azure_openai_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        "azure_openai_model": os.getenv("AZURE_OPENAI_MODEL")
    }
    
    return OCRModelFactory.create_model(model_type, **config)

