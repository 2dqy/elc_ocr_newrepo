from PIL import Image,  ExifTags

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


def crop_and_compress_image(image_data, target_size_ratio=0.8):
    """
    裁剪图像中间60%区域并压缩到目标大小
    
    参数:
        image_data: 图像二进制数据
        target_size_ratio: 目标文件大小与原始大小的比例 (默认0.8，即80%)
    返回:
        处理后的图像数据
    """
    try:
        # 使用PIL打开图像
        img = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB格式
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])  # Alpha通道
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # 获取原始图像尺寸
        width, height = img.size
        print(f"📷 原始图像尺寸: {width}x{height}")
        
        # 裁剪中间60%区域（去掉外围20%）
        w_crop = int(width * 0.2)  # 左右各裁剪20%
        h_crop = int(height * 0.2)  # 上下各裁剪20%
        
        # 裁剪图像
        cropped_img = img.crop((w_crop, h_crop, width - w_crop, height - h_crop))
        print(f"✂️ 裁剪后图像尺寸: {cropped_img.size[0]}x{cropped_img.size[1]}")
        
        # 计算目标文件大小
        original_size = len(image_data)
        target_size = int(original_size * target_size_ratio)
        print(f"🎯 目标文件大小: {target_size / 1024:.1f}KB (原始: {original_size / 1024:.1f}KB)")
        
        # 压缩到目标大小
        compressed_data = compress_to_target_size(cropped_img, target_size)
        
        print(f"✅ 处理完成，最终文件大小: {len(compressed_data) / 1024:.1f}KB")
        return compressed_data
        
    except Exception as e:
        print(f"❌ 图像处理失败: {str(e)}")
        # 如果处理失败，返回原始数据
        return image_data


def compress_to_target_size(img, target_size_bytes):
    """
    将PIL图像压缩到指定的文件大小
    
    参数:
        img: PIL图像对象
        target_size_bytes: 目标文件大小（字节）
    返回:
        压缩后的图像二进制数据
    """
    quality = 95  # 初始压缩质量
    
    while quality > 10:
        # 创建内存缓冲区
        output_buffer = io.BytesIO()
        
        # 保存图像到缓冲区
        img.save(output_buffer, format='JPEG', quality=quality, optimize=True)
        
        # 获取压缩后的数据
        compressed_data = output_buffer.getvalue()
        current_size = len(compressed_data)
        
        # 检查是否满足大小要求
        if current_size <= target_size_bytes:
            print(f"🎯 压缩成功，质量: {quality}, 大小: {current_size / 1024:.1f}KB")
            return compressed_data
        
        # 降低质量继续尝试
        quality -= 5
        print(f"🔄 尝试质量: {quality}, 当前大小: {current_size / 1024:.1f}KB")
    
    # 如果已经是最低质量，返回最后的结果
    print(f"⚠️ 已尝试最低质量({quality + 5})，最终大小: {len(compressed_data) / 1024:.1f}KB")
    return compressed_data


# 修正圖片方向
def correct_image_orientation(image):
    try:
        img = Image.open(image)
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
        print("Image orientation corrected.")
        return img
    except Exception:
        return Image.open(image)