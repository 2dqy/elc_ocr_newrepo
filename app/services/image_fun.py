from PIL import Image,  ExifTags, ImageEnhance
# import numpy as np
import io
import base64
# import cv2


def process_image(image_data, MIN_PIXELS, MAX_PIXELS):
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
    # width, height = img.size
    # total_pixels = width * height

    # # 调整图像大小以符合像素要求
    # if total_pixels < MIN_PIXELS:
    #     # 放大图像
    #     scale_factor = (MIN_PIXELS / total_pixels) ** 0.5
    #     new_width = int(width * scale_factor)
    #     new_height = int(height * scale_factor)
    #     img = img.resize((new_width, new_height), Image.BICUBIC)
    # elif total_pixels > MAX_PIXELS:
    #     # 缩小图像
    #     scale_factor = (MAX_PIXELS / total_pixels) ** 0.5
    #     new_width = int(width * scale_factor)
    #     new_height = int(height * scale_factor)
    #     img = img.resize((new_width, new_height), Image.LANCZOS)

    # # 增强亮度 - 提高20%
    # enhancer = ImageEnhance.Brightness(img)
    # img = enhancer.enhance(1.2)
    #
    # # 增强对比度 - 提高30%
    # enhancer = ImageEnhance.Contrast(img)
    # img = enhancer.enhance(1.2)
    #
    # # 锐化图像 - 轻微锐化
    # enhancer = ImageEnhance.Sharpness(img)
    # img = enhancer.enhance(1.2)

    # 保存为JPEG字节流
    output_buffer = io.BytesIO()
    img.save(output_buffer, format='JPEG', quality=95)

    return output_buffer.getvalue()


def correct_image_orientation(image_content: bytes) -> Image.Image:
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


def compress_image(image_content: bytes, filename: str, max_size: int = 1024) -> str:
    """压缩图像并转换为base64"""
    try:
        img = correct_image_orientation(image_content)
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


# def enhance_image_for_ocr(image_content: bytes, filename: str) -> bytes:
#     """
#     针对OCR优化的图像增强处理
#     包括血糖设备特殊处理、噪点去除、显示屏区域分割等
#     """
#     try:
#         # 转换为OpenCV格式
#         img_array = np.frombuffer(image_content, np.uint8)
#         img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
#
#         if img is None:
#             print("图像解码失败，返回原始图像")
#             return image_content
#
#         # 修正图像方向
#         pil_img = correct_image_orientation(image_content)
#         img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
#
#         print(f"原始图像尺寸: {img.shape}")
#
#         # 1. 自适应亮度调整
#         img = adaptive_brightness_adjustment(img)
#
#         # 2. CLAHE对比度增强
#         img = apply_clahe_enhancement(img)
#
#         # 3. 边缘检测和显示屏区域分割
#         img = detect_and_crop_display_area(img)
#
#         # 4. 血糖设备特殊处理（基于文件名或图像特征判断）
#         if is_blood_sugar_device(img, filename):
#             img = enhance_for_blood_sugar(img)
#
#         # 5. 形态学操作去噪
#         img = morphological_denoising(img)
#
#         # 6. 最终锐化处理
#         img = apply_sharpening(img)
#
#         # 转换回PIL格式并保存为字节流
#         img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#         pil_img = Image.fromarray(img_rgb)
#
#         output_buffer = io.BytesIO()
#         pil_img.save(output_buffer, format='JPEG', quality=95)
#
#         print(f"图像增强完成，处理后大小: {len(output_buffer.getvalue())} bytes")
#         return output_buffer.getvalue()
#
#     except Exception as e:
#         print(f"图像增强失败: {str(e)}")
#         return image_content
#
#
# def adaptive_brightness_adjustment(img: np.ndarray) -> np.ndarray:
#     """自适应亮度调整"""
#     try:
#         # 转换为灰度图分析亮度
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         mean_brightness = np.mean(gray)
#
#         print(f"图像平均亮度: {mean_brightness}")
#
#         # 根据亮度调整参数
#         if mean_brightness < 80:  # 图像过暗
#             # 伽马校正提亮
#             gamma = 1.5
#             img = adjust_gamma(img, gamma)
#             print("应用伽马校正提亮")
#         elif mean_brightness > 180:  # 图像过亮
#             # 伽马校正变暗
#             gamma = 0.7
#             img = adjust_gamma(img, gamma)
#             print("应用伽马校正变暗")
#
#         return img
#     except Exception as e:
#         print(f"自适应亮度调整失败: {str(e)}")
#         return img
#
#
# def adjust_gamma(img: np.ndarray, gamma: float) -> np.ndarray:
#     """伽马校正"""
#     inv_gamma = 1.0 / gamma
#     table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
#     return cv2.LUT(img, table)
#
#
# def apply_clahe_enhancement(img: np.ndarray) -> np.ndarray:
#     """CLAHE对比度限制自适应直方图均衡化"""
#     try:
#         # 转换到LAB色彩空间，只对L通道应用CLAHE
#         lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
#         l_channel, a_channel, b_channel = cv2.split(lab)
#
#         # 创建CLAHE对象
#         clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
#         l_channel = clahe.apply(l_channel)
#
#         # 合并通道并转换回BGR
#         lab = cv2.merge([l_channel, a_channel, b_channel])
#         img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
#
#         print("应用CLAHE对比度增强")
#         return img
#     except Exception as e:
#         print(f"CLAHE增强失败: {str(e)}")
#         return img
#
#
# def detect_and_crop_display_area(img: np.ndarray) -> np.ndarray:
#     """边缘检测和显示屏区域分割"""
#     try:
#         original_img = img.copy()
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#
#         # 高斯模糊
#         blurred = cv2.GaussianBlur(gray, (5, 5), 0)
#
#         # 边缘检测
#         edges = cv2.Canny(blurred, 50, 150)
#
#         # 形态学操作连接边缘
#         kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
#         edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
#
#         # 查找轮廓
#         contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#
#         if not contours:
#             print("未找到显示区域轮廓，返回原图")
#             return original_img
#
#         # 找到面积最大且形状合理的矩形区域（可能是显示屏）
#         height, width = img.shape[:2]
#         min_area = (width * height) * 0.05  # 最小面积阈值
#         max_area = (width * height) * 0.8   # 最大面积阈值
#
#         best_contour = None
#         best_area = 0
#
#         for contour in contours:
#             area = cv2.contourArea(contour)
#             if min_area < area < max_area:
#                 # 检查轮廓的矩形度
#                 x, y, w, h = cv2.boundingRect(contour)
#                 aspect_ratio = w / h
#
#                 # 显示屏通常是横向矩形
#                 if 0.5 < aspect_ratio < 4.0 and area > best_area:
#                     best_contour = contour
#                     best_area = area
#
#         if best_contour is not None:
#             # 裁剪到检测到的显示区域
#             x, y, w, h = cv2.boundingRect(best_contour)
#             # 添加一些边距
#             margin = 10
#             x = max(0, x - margin)
#             y = max(0, y - margin)
#             w = min(width - x, w + 2 * margin)
#             h = min(height - y, h + 2 * margin)
#
#             cropped_img = original_img[y:y+h, x:x+w]
#             print(f"检测到显示区域并裁剪: ({x},{y},{w},{h})")
#             return cropped_img
#
#         print("未找到合适的显示区域，返回原图")
#         return original_img
#
#     except Exception as e:
#         print(f"显示区域检测失败: {str(e)}")
#         return img
#
#
# def is_blood_sugar_device(img: np.ndarray, filename: str) -> bool:
#     """判断是否为血糖设备图像"""
#     try:
#         # 基于文件名的简单判断
#         filename_lower = filename.lower() if filename else ""
#         blood_sugar_keywords = ['血糖', 'glucose', 'sugar', 'bg', 'gluc']
#
#         for keyword in blood_sugar_keywords:
#             if keyword in filename_lower:
#                 return True
#
#         # 基于图像特征的判断（简化版）
#         # 血糖设备通常显示带小数点的数值
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#
#         # 检测小圆点（可能是小数点）
#         circles = cv2.HoughCircles(
#             gray, cv2.HOUGH_GRADIENT, 1, 20,
#             param1=50, param2=30, minRadius=1, maxRadius=10
#         )
#
#         if circles is not None and len(circles[0]) > 0:
#             print(f"检测到{len(circles[0])}个小圆点，可能是血糖设备")
#             return True
#
#         return False
#
#     except Exception as e:
#         print(f"血糖设备判断失败: {str(e)}")
#         return False
#
#
# def enhance_for_blood_sugar(img: np.ndarray) -> np.ndarray:
#     """血糖设备特殊增强处理"""
#     try:
#         print("应用血糖设备特殊增强")
#
#         # 1. 增强对比度，突出数字和小数点
#         lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
#         l_channel, a_channel, b_channel = cv2.split(lab)
#
#         # 更强的对比度增强
#         clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
#         l_channel = clahe.apply(l_channel)
#
#         lab = cv2.merge([l_channel, a_channel, b_channel])
#         img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
#
#         # 2. 特殊的锐化滤波器，增强小数点
#         kernel = np.array([
#             [-1, -1, -1],
#             [-1,  9, -1],
#             [-1, -1, -1]
#         ])
#         img = cv2.filter2D(img, -1, kernel)
#
#         # 3. 形态学操作，突出小点特征
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#
#         # 开运算去除噪点但保留小数点
#         kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
#         gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_small)
#
#         # 转换回彩色
#         img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
#
#         return img
#
#     except Exception as e:
#         print(f"血糖设备增强失败: {str(e)}")
#         return img
#
#
# def morphological_denoising(img: np.ndarray) -> np.ndarray:
#     """形态学操作去噪"""
#     try:
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#
#         # 开运算去除小噪点
#         kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
#         gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel_open)
#
#         # 闭运算连接断开的数字部分
#         kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
#         gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel_close)
#
#         # 转换回彩色
#         img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
#
#         print("应用形态学去噪")
#         return img
#
#     except Exception as e:
#         print(f"形态学去噪失败: {str(e)}")
#         return img
#
#
# def apply_sharpening(img: np.ndarray) -> np.ndarray:
#     """应用锐化滤波器"""
#     try:
#         # 拉普拉斯锐化
#         kernel = np.array([
#             [0, -1, 0],
#             [-1, 5, -1],
#             [0, -1, 0]
#         ])
#         sharpened = cv2.filter2D(img, -1, kernel)
#
#         # 与原图混合，避免过度锐化
#         img = cv2.addWeighted(img, 0.6, sharpened, 0.4, 0)
#
#         print("应用锐化处理")
#         return img
#
#     except Exception as e:
#         print(f"锐化处理失败: {str(e)}")
#         return img
#
#
# def remove_keyboard_interference(img: np.ndarray) -> np.ndarray:
#     """移除键盘干扰（备用函数）"""
#     try:
#         # 这个函数可以用于专门处理键盘干扰的情况
#         # 通过检测按钮轮廓并遮罩非显示区域
#         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#
#         # 检测圆形按钮（键盘按键通常是圆形或方形）
#         circles = cv2.HoughCircles(
#             gray, cv2.HOUGH_GRADIENT, 1, 30,
#             param1=50, param2=30, minRadius=10, maxRadius=50
#         )
#
#         if circles is not None:
#             circles = np.round(circles[0, :]).astype("int")
#             mask = np.ones(gray.shape, dtype=np.uint8) * 255
#
#             # 在检测到的按钮位置创建遮罩
#             for (x, y, r) in circles:
#                 cv2.circle(mask, (x, y), r, 0, -1)
#
#             # 应用遮罩
#             img = cv2.bitwise_and(img, img, mask=mask)
#             print(f"移除了{len(circles)}个可能的键盘按钮")
#
#         return img
#
#     except Exception as e:
#         print(f"键盘干扰移除失败: {str(e)}")
#         return img