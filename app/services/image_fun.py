from PIL import Image,  ExifTags
import numpy as np
import io
import base64


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