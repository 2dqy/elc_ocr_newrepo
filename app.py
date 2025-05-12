import os
import time
import io
import base64
from PIL import Image, ImageEnhance
import dashscope
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
from database import Database
import uuid
# 加载.env环境变量
load_dotenv()

# 获取API密钥和配置参数
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))

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
app.mount("/static", StaticFiles(directory="static"), name="static")

# 图像处理参数
MIN_PIXELS = int(os.getenv("MIN_PIXELS", 28 * 28 * 4))  # 最小像素阈值
MAX_PIXELS = int(os.getenv("MAX_PIXELS", 28 * 28 * 8192))  # 最大像素阈值
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 500 * 1024))  # 最大文件大小（500KB）

# 创建上传目录
os.makedirs("uploads", exist_ok=True)

# 初始化数据库
db = Database()

# 验证token
def verify_token(token: str = Form(...)):
    """验证用户的token是否有效"""
    try:
        # 使用Database类连接MySQL
        db = Database()
        
        # 查询token是否存在及其使用次数
        db.cursor.execute("SELECT use_times FROM tokens WHERE token=%s", (token,))
        print("token:", token)
        result = db.cursor.fetchone()
        print("result:", result)
        
        if not result:
            raise HTTPException(status_code=401, detail="TOKEN_NOT_FOUND")
        
        if result[0] <= 0:
            raise HTTPException(status_code=403, detail="TOKEN_USED_UP")
        
        return token
    except Exception as e:
        print(f"Token验证错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"TOKEN_VERIFY_ERROR: {str(e)}")

# 更新token使用次数
def update_token_usage(token: str):
    """更新token的使用次数"""
    try:
        # 使用Database类连接MySQL
        db = Database()
        
        # 更新使用次数
        db.cursor.execute("UPDATE tokens SET use_times = use_times - 1 WHERE token=%s", (token,))
        db.conn.commit()
        
        print(f"Token {token} 使用次数已更新")
    except Exception as e:
        print(f"更新Token使用次数错误: {str(e)}")


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    """处理网站图标请求"""
    # 检查是否存在favicon.ico文件
    favicon_path = "static/images/favicon.ico"
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    else:
        # 如果没有图标，返回404
        raise HTTPException(status_code=404, detail="Favicon not found")

def process_image(image_data):
    """
    处理图像 - 调整大小、对比度和亮度，使用PIL
    
    参数:
        image_data: 图像二进制数据
    返回:
        处理后的图像数据
    """
    # 使用PIL打开图像
    img = Image.open(io.BytesIO(image_data))

    # 针对png的处理
    # 若为带透明通道的图像（如PNG），先转换为RGB
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])  # Alpha通道
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")


    # 计算当前图像的像素总数
    width, height = img.size
    total_pixels = width * height
    
    # 调整图像大小以符合像素要求
    if total_pixels < MIN_PIXELS:
        # 放大图像
        scale_factor = (MIN_PIXELS / total_pixels) ** 0.5
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        img = img.resize((new_width, new_height), Image.BICUBIC)
    elif total_pixels > MAX_PIXELS:
        # 缩小图像
        scale_factor = (MAX_PIXELS / total_pixels) ** 0.5
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # 增强亮度 - 提高20%
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)
    
    # 增强对比度 - 提高30%
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)
    
    # 锐化图像 - 轻微锐化
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    
    # 保存为JPEG字节流
    output_buffer = io.BytesIO()
    img.save(output_buffer, format='JPEG', quality=95)
    
    return output_buffer.getvalue()

@app.post("/upload/image")
async def upload_image(
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
    # 检查token是否有效
    verify_token(token)
    
    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 检查文件是否为图像
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图像文件")
    
    # 读取文件内容
    file_content = await file.read()
    
    # 检查文件大小
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过500KB限制")
    
    try:
        # 处理图像
        processed_image = process_image(file_content)
        
        # 保存处理后的图像到临时文件
        timestamp = int(time.time())
        temp_filename = f"uploads/temp_{timestamp}.jpg"
        with open(temp_filename, "wb") as f:
            f.write(processed_image)
        
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
                       - 测量时间（从图片中提取，格式.py：HH:mm）
                       - 测量数值
                    
                    请按照以下JSON格式返回数据：
                    {
                        "status": "success/error",
                        "message": "成功/错误信息",
                        "data": {
                            "brand": "设备品牌",
                            "measure_date": "当前日期",
                            "measure_time": "图片中的测量时间",
                            "category": "blood_pressure/blood_sugar",
                            "blood_pressure": {
                                "sys": "收缩压值",
                                "dia": "舒张压值",
                                "pul": "心率值"
                            },
                            "blood_sugar": {
                                "value": "血糖值",                            },
                            "suggest": "基于数据的AI健康建议"
                        }
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
                # 获取OCR结果并处理格式
                raw_result = response["output"]["choices"][0]["message"]["content"][0]["text"]
                # 移除JSON格式标记和换行符，并转换为字典
                ocr_result = raw_result.replace('\n', '').replace('    ', '').replace('```json', '').replace('```', '')
                
                # 构建完整响应
                try:
                    # 将字符串转换为字典
                    import json
                    ocr_dict = json.loads(ocr_result)
                    # 替换日期为当前日期
                    if "data" in ocr_dict and ocr_dict["data"]:
                        ocr_dict["data"]["measure_date"] = current_date
                    
                    response_data = {
                        "status": ocr_dict["status"],
                        "message": ocr_dict["message"],
                        "data": ocr_dict["data"],
                        "file_info": {
                            "filename": file.filename,
                            "content_type": file.content_type,
                            "size": len(file_content),
                            "processed_size": len(processed_image)
                        },
                        "source_ip": "127.0.0.1",
                        "timestamp": timestamp
                    }
                    
                    # 如果OCR识别成功，更新token使用次数
                    if ocr_dict["status"] == "success":
                        update_token_usage(token)
                except Exception as parse_error:
                    response_data = {
                        "status": "error",
                        "message": f"解析OCR结果失败: {str(parse_error)}",
                        "data": None,
                        "file_info": {
                            "filename": file.filename,
                            "content_type": file.content_type,
                            "size": len(file_content),
                            "processed_size": len(processed_image)
                        },
                        "source_ip": "127.0.0.1",
                        "timestamp": timestamp
                    }
            else:
                # 处理API错误
                response_data = {
                    "status": "error",
                    "message": f"API调用失败: {response.code} - {response.message}",
                    "data": None,
                    "file_info": {
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "size": len(file_content),
                        "processed_size": len(processed_image)
                    },
                    "source_ip": "127.0.0.1",
                    "timestamp": timestamp
                }
                print(f"API错误: {response.code} - {response.message}")
                
        except Exception as api_error:
            # 处理API调用错误
            response_data = {
                "status": "error",
                "message": f"OCR API调用错误: {str(api_error)}",
                "data": None,
                "file_info": {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(file_content),
                    "processed_size": len(processed_image)
                },
                "source_ip": "127.0.0.1",
                "timestamp": timestamp
            }
            print(f"OCR API调用错误: {str(api_error)}")
        
        # 清理临时文件
        # os.remove(temp_filename)
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        # 处理可能发生的错误
        print(f"处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"UPLOAD_FILE_FAIL: {str(e)}")


@app.post("/upload/add_token")
async def add_token(request: Request, token_data: dict):
    # 查询数据库中的ip白名单，返回一个列表，从mysql中查询
    db = Database()
    allowed_ips = db.get_allowed_ips()
    ALLOWED_IPS = allowed_ips[0] if allowed_ips else []
    print(ALLOWED_IPS)
    # IP验证
    if request.client:
        client_ip = request.client.host
    else:
        client_ip = None
        if client_ip not in ALLOWED_IPS:
            raise HTTPException(
                status_code=403,
                detail={
                    "errors": [{
                        "message": "IP 使用有限制",
                        "extensions": {
                            "code": "IP_DENY",
                            "reason": "IP 使用有限制"
                        }
                    }]
                }
            )



    # 设置默认值
    token = token_data.get("token",'')
    # 如果token包含非字母数字字符，返回HTTP错误400
    if not token.isalnum():
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [{
                    "message": "Token 名稱不能为空且包含非字母数字字符",
                    "extensions": {
                        "code": "TOKEN_INVALID",
                        "reason": "Token 名稱不能为空且包含非字母数字字符"
                    }
                }]
            }
        )
    if not token or not token.isalnum():
        token = str(uuid.uuid4().hex[:8])

    db = Database()
    # 检查token是否已存在

    if db.token_exists(token):
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [{
                    "message": "Token 名稱重複",
                    "extensions": {
                        "code": "TOKEN_EXIST",
                        "reason": "Token 名稱重複"
                    }
                }]
            }
        )

    use_times = token_data.get("use_times", 90)
    center_id = token_data["center_id"]
    # 必填字段验证
    if "center_id" not in token_data:
        raise HTTPException(
            status_code=403,
            detail={
                "errors": [{
                    "message": "You don't have permission to \"create\" from collection \"tokenCreate\" or it does not exist.",
                    "extensions": {
                        "code": "FORBIDDEN",
                        "reason": "center_id is required"
                    }
                }]
            }
        )


    if not db.center_id_exists(center_id):
        raise HTTPException(
            status_code=403,
            detail={
                "errors": [{
                    "message": "Invalid center_id",
                    "extensions": {
                        "code": "FORBIDDEN",
                        "reason": "center_id not found"
                    }
                }]
            }
        )

    # 检查token是否已存在
    if db.token_exists(token):
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [{
                    "message": "Token 名稱重複",
                    "extensions": {
                        "code": "TOKEN_EXIST",
                        "reason": "Token 名稱重複"
                    }
                }]
            }
        )

    # 插入新token
    try:
        db.add_token(token, use_times, center_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [{
                    "message": str(e),
                    "extensions": {
                        "code": "TOKEN_EXIST",
                        "reason": str(e)
                    }
                }]
            }
        )

    return {
        "data": {
            "id": db.cursor.lastrowid,
            "token": token,
            "use_times": use_times,
            "center_id": center_id
        }
    }

@app.get("/")
async def health_check():
    from datetime import datetime
    return {
        "status": "server測試成功",
        "server_time": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # 启动FastAPI应用
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)