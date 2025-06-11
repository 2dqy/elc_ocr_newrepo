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
import dashscope
from openai import AzureOpenAI
from pydantic import BaseModel
import google.generativeai as genai

# 导入图像处理函数和提示词
from .image_fun import compress_image, correct_image_orientation, enhance_image_for_ocr
from .prompts import get_qwen_prompt, get_openai_prompt, get_gemini_prompt


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
            # 检查是否启用图像增强
            # os.getenv("ENABLE_IMAGE_ENHANCEMENT", "true") 确保如果环境变量未设置，默认为 "true"
            enable_enhancement = os.getenv("ENABLE_IMAGE_ENHANCEMENT", "true").lower() == "true"
            # 声明 compressed_image 变量，以便在if/else之外使用
            compressed_image_final = None  # 或者直接在各分支内赋值

            if enable_enhancement:
                # 启用图像增强处理
                print("启用图像增强处理")
                # 1. 增强图像
                enhanced_image = enhance_image_for_ocr(image_content, filename)
                # 2. 压缩增强后的图像
                compressed_image_final = compress_image(enhanced_image, filename)

                # 保存处理后的图像到本地output文件夹 (可选，调试用)
                # os.makedirs("output", exist_ok=True)  # 确保output文件夹存在
                # with open(f"output/enhanced_{filename}", "wb") as f:
                #     f.write(enhanced_image)
            else:
                # 不启用增强时，直接压缩原始图像
                print("使用原始图像处理 (图像增强已禁用)")
                compressed_image_final = compress_image(image_content, filename)

            # 确保 compressed_image_final 在这里已经被赋值
            image_data_uri = f"data:image/jpeg;base64,{compressed_image_final}"
            
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
                            {"type": "text", "text": get_openai_prompt()},
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
                        "text": get_qwen_prompt()
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


class GeminiOCRModel(BaseOCRModel):
    """Gemini OCR模型"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model_name = "gemini-2.5-flash-preview-05-20"

    def analyze_image(self, image_content: bytes, filename: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """使用Gemini模型分析图像"""
        try:
            # Gemini直接使用原始图像，不需要压缩和预处理
            prompt_parts = [
                {"mime_type": "image/jpeg", "data": image_content},
                get_gemini_prompt()
            ]

            model = genai.GenerativeModel(model_name=self.model_name)
            response = model.generate_content(prompt_parts)

            ocr_result, _ = self.extract_result(response)

            # 提取Gemini模型的usage信息
            usage_info = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_info = {
                    "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0)
                }

            return ocr_result, usage_info

        except Exception as e:
            return {"error": f"Gemini模型调用失败: {str(e)}"}, {}

    def extract_result(self, response: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """从Gemini API响应中提取结果"""
        try:
            if not response or not response.text:
                return {"error": "Gemini API返回空响应"}, {}

            raw_result = response.text.strip()

            # 移除代码块标记
            ocr_result = raw_result.replace('```json', '').replace('```', '').strip()

            # 解析JSON
            ocr_dict = json.loads(ocr_result)

            # 确保data字段存在
            if "data" not in ocr_dict:
                ocr_dict = {"data": ocr_dict}

            return ocr_dict, {}

        except Exception as e:
            return {"error": f"Gemini结果解析失败: {str(e)}"}, {}


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
        elif model_type.lower() == "gemini":
            return GeminiOCRModel(
                api_key=kwargs.get("gemini_api_key")
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
        "azure_openai_model": os.getenv("AZURE_OPENAI_MODEL"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY")
    }
    
    return OCRModelFactory.create_model(model_type, **config)

