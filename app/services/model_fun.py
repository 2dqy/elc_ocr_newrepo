"""
支持qwen-vl-ocr-0413与gpt-4o
"""
import os
import base64
import io
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from PIL import Image, ExifTags
import dashscope
from openai import AzureOpenAI


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
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
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
            content = response.choices[0].message.content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # OpenAI返回的结果已经包含data字段，直接返回
                return result, {}
            else:
                return {"error": "未找到有效的 JSON 回應"}, {}
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
            if hasattr(img, "_getexif"):
                exif = img._getexif()
                if exif:
                    for orientation in ExifTags.TAGS:
                        if ExifTags.TAGS[orientation] == "Orientation":
                            break
                    if orientation in exif:
                        if exif[orientation] == 3:
                            img = img.rotate(180, expand=True)
                        elif exif[orientation] == 6:
                            img = img.rotate(270, expand=True)
                        elif exif[orientation] == 8:
                            img = img.rotate(90, expand=True)
            
            print(f"修正後的圖片方向: {img.getexif().get(274)}")
            return img
        except Exception:
            return Image.open(io.BytesIO(image_content))
    
    def _get_openai_prompt(self) -> str:
        """获取OpenAI模型的提示词"""
        return """​1. 圖片相關性判斷​
​判斷條件​：
影像是否包含血壓計或血糖儀的顯示器或資料。
若為無關內容（如風景、人物照等），回傳以下 JSON 並終止後續步驟：
json
复制
{
  "data": {
    "category": "Not relevant"
  }
}
​2. 錯誤狀態檢查​
​規則​：
嚴禁推測或填寫預設值，僅能根據圖片內容回傳。
若圖片顯示錯誤訊息（如 E1、Err、Error），回傳以下 JSON：
json
复制
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
​3. 設備類型與數據提取​
​嚴格要求​：
所有欄位必須基於圖片內容，無法識別時設為 null。
​血糖儀​：僅填寫 blood_sugar 值，其餘血壓欄位設為 null。
​血壓計​：填寫 sys（收縮壓）、dia（舒張壓）、pul（心率），血糖欄位設為 null。
​4. 關注訊息​
​填寫規則​：
​品牌/型號​：僅限圖片中可見的資訊。
​測量時間​：格式為 HH:mm:ss，若無則設為 null。
​健康建議​：需根據實際提取的數值提供專業建議，若數值無效則建議重新測量。
​5. 最終回傳格式​
json
复制
{
  "data": {
    "brand": "設備品牌（或 null）",
    "measure_date": "當前日期（或 null）",
    "measure_time": "圖片中的測量時間（或 null）",
    "category": "blood_pressure 或 blood_sugar",
    "blood_pressure": {
      "sys": "收縮壓值（或 null）",
      "dia": "舒張壓值（或 null）",
      "pul": "心率值（或 null）"
    },
    "blood_sugar": "血糖值（或 null）",
    "other_value": "其他資料（或 null）",
    "suggest": "基於數據的 AI 健康建議",
    "analyze_reliability": "分析可信度（0.0~1.0）",
    "status": "分析狀態（如 'completed'、'failed'）"
  }
}
​注意事項​
​嚴禁推測​：所有欄位僅能根據圖片內容填寫，否則設為 null。
​數據隔離​：
血壓數據時，blood_sugar 必須為 null。
血糖數據時，blood_pressure 所有欄位必須為 null。
​時間格式​：僅接受從圖片提取的 HH:mm:ss，否則為 null。
​錯誤優先​：若檢測到錯誤，直接回傳錯誤格式（步驟 2）。
​語言與格式​：
僅使用繁體中文。
嚴格遵守 JSON 格式，不得新增或缺少欄位。
- 如果一個大數字看起來明顯不合常理（如 179 mmol/L），請判斷是否可能是 17.9。
- 嘗試根據格式規律（血糖值通常介於 2.0 到 20.0）來做小數推論。
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

