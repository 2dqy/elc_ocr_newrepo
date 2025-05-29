import os
import base64
import io
import json
import re
import time
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from PIL import Image, ExifTags
from openai import AzureOpenAI

# 设置模板目录
templates = Jinja2Templates(directory="app/templates")

# 创建路由器
router = APIRouter()

# Azure OpenAI 配置
endpoint = "https://vincent-openai-2025.openai.azure.com/"
model_name = "gpt-4o"
deployment = "gpt-4o"
subscription_key = "xxxx"
api_version = "2024-12-01-preview"
client = AzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=subscription_key)


# 修正圖片方向
def correct_image_orientation(image_content):
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


# 壓縮與轉 Base64
def compress_image(image_content, filename, max_size=1024, save_path="compressed_images"):
    img = correct_image_orientation(image_content)
    img = img.convert("RGB")
    img.thumbnail((max_size, max_size))
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    compressed_file_path = os.path.join(save_path, f"compressed_{filename}")
    img.save(compressed_file_path, format="JPEG")
    
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="JPEG")
    img_base64 = base64.b64encode(img_byte_array.getvalue()).decode("utf-8")
    
    # 打印压缩后的文件大小
    print(f"壓縮後的文件大小: {os.path.getsize(compressed_file_path)} bytes")
    return img_base64, compressed_file_path


# GPT 回傳內容擷取 JSON
def extract_json_from_gpt_response(response):
    try:
        content = response.choices[0].message.content
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"error": "未找到有效的 JSON 回應"}
    except Exception as e:
        return {"error": f"擷取 JSON 錯誤: {str(e)}"}


# 上傳圖片並送出 GPT-4o
@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """
    上传并分析单张医疗图像
    
    参数:
        file: 上传的图像文件
    返回:
        图像分析结果的JSON响应
    """
    # 开始计时
    start_time = time.time()
    
    # 获取客户端IP地址
    client_ip = request.client.host if request.client else "unknown"
    
    if not file:
        return JSONResponse(
            status_code=400,
            content={"error": "未選擇檔案"}
        )
    
    # 检查文件是否为图像
    if not file.content_type.startswith("image/"):
        return JSONResponse(
            status_code=400,
            content={"error": "請上傳圖片文件"}
        )
    
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 压缩图像
        compressed_image, compressed_file_path = compress_image(file_content, file.filename)

        prompt_content = """​1. 圖片相關性判斷​
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

        image_data_uri = f"data:image/jpeg;base64,{compressed_image}"

        # Azure Chat Completions
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_content},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_uri, "detail": "low"},
                        },
                    ],
                }
            ],
            max_tokens=500,
        )

        print(response)
        result = extract_json_from_gpt_response(response)
        print(result)
        
        # 计算执行时间
        execution_time = time.time() - start_time
        print(f"处理完成，执行时间: {execution_time:.2f}秒")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        print(f"处理错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"處理失敗: {str(e)}"}
        )


@router.get("/")
async def index(request: Request):
    """返回HTML首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/html")
async def read_root():
    """返回HTML测试页面"""
    file_path = Path(__file__).resolve().parent.parent.parent / "static" / "test-openai.html"
    if file_path.exists():
        return FileResponse(file_path)
    else:
        # 如果文件不存在，返回templates中的index.html
        file_path = Path(__file__).resolve().parent.parent.parent / "templates" / "index.html"
        return FileResponse(file_path)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # 修改为正确的应用路径
        host="127.0.0.1",
        port=5000,
        reload=True
    )

