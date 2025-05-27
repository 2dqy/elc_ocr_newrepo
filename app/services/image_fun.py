from PIL import Image, ImageEnhance
import io


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

    # # 增强亮度 - 提高10%
    # enhancer = ImageEnhance.Brightness(img)
    # img = enhancer.enhance(1.3)
    #
    # # 增强对比度 - 提高20%
    # enhancer = ImageEnhance.Contrast(img)
    # img = enhancer.enhance(1.3)
    #
    # # 锐化图像 - 轻微锐化
    # enhancer = ImageEnhance.Sharpness(img)
    # img = enhancer.enhance(1.8)

    # 保存为JPEG字节流
    output_buffer = io.BytesIO()
    img.save(output_buffer, format='JPEG', quality=95)

    return output_buffer.getvalue()


def compress_image(image_data, max_size_kb=500):
    """
    压缩图像到指定大小以下
    
    参数:
        image_data: 图像二进制数据
        max_size_kb: 最大文件大小（KB），默认500KB
    返回:
        压缩后的图像数据，如果压缩失败返回None
    """
    max_size_bytes = max_size_kb * 1024
    
    try:
        # 使用PIL打开图像
        img = Image.open(io.BytesIO(image_data))
        
        # 如果是 PNG 或带 alpha 通道，转换为 RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # 初始压缩质量（逐步尝试降低）
        quality = 98
        step = 2
        
        while quality > 10:
            # 创建内存缓冲区
            output_buffer = io.BytesIO()
            img.save(output_buffer, "JPEG", quality=quality)
            compressed_data = output_buffer.getvalue()
            
            # 检查压缩后的大小
            if len(compressed_data) <= max_size_bytes:
                print(f"图像压缩成功：质量{quality}% -> {len(compressed_data)/1024:.1f}KB")
                return compressed_data
            
            quality -= step
        
        # 如果无法压缩到目标大小
        print(f"图像无法压缩到 {max_size_kb}KB 以下，最小已尝试 {quality+step}%")
        return None
        
    except Exception as e:
        print(f"图像压缩失败: {e}")
        return None
