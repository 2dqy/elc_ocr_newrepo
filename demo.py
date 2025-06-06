import cv2
import os
import numpy as np  # 导入numpy用于创建数组


def compress_to_target_size(image, target_size_kb, output_path):
    """
    尝试以递减的JPEG质量压缩图像，直到达到目标文件大小或达到最低质量。
    """
    quality = 95  # 初始压缩质量
    # 确保循环条件正确，避免无限循环或过早结束
    while quality >= 10:
        # 临时保存图像以检查文件大小
        # cv2.IMWRITE_JPEG_QUALITY 参数用于设置JPEG压缩质量
        success = cv2.imwrite(output_path, image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not success:
            print("❌ 图像保存失败 (质量: %d)" % quality)
            # 如果保存失败，可能文件路径有问题或者权限问题，直接返回False
            return False

        # 检查文件大小
        size_kb = os.path.getsize(output_path) / 1024
        if size_kb <= target_size_kb:
            print(f"  压缩质量 {quality}% 达到目标大小 {size_kb:.2f} KB (目标: {target_size_kb:.2f} KB)")
            return True

        quality -= 5  # 每次降低5%的质量

    # 如果循环结束，说明即使使用最低质量也未能达到目标
    print(f"⚠️ 已尝试最低质量 (10%)，图像大小 ({size_kb:.2f} KB) 仍无法完全满足目标 ({target_size_kb:.2f} KB)。")
    return True  # 仍然返回True，因为图像已保存，只是可能超标


def process_image(image_path, output_path=None):
    """
    读取图像，将20%的边缘区域填充白色，保持尺寸不变，并压缩图像大小不超过原图。
    """
    if not os.path.isfile(image_path):
        print(f"❌ 文件不存在: {image_path}")
        return

    original_image = cv2.imread(image_path)
    if original_image is None:
        print(f"❌ 无法读取图像: {image_path}")
        return

    height, width = original_image.shape[:2]
    print(f"📷 原始图像尺寸: {width}x{height}")

    # 复制一份图像，避免修改原始加载的图像数据
    processed_image = original_image.copy()

    # 计算 20% 的边缘宽度和高度
    border_h = int(height * 0.2)
    border_w = int(width * 0.2)

    # 确保计算出的边界至少为1像素，避免0宽度/高度的切片
    # 且确保边界不会超过图像的实际尺寸的一半
    border_h = max(1, min(border_h, height // 2 - 1))  # 至少1像素，且不超过中间区域
    border_w = max(1, min(border_w, width // 2 - 1))  # 至少1像素，且不超过中间区域

    # 填充顶部边缘
    # 切片范围 [行起始:行结束, 列起始:列结束]
    # [0:border_h, 0:width] 表示从第0行到 border_h-1 行，从第0列到 width-1 列
    processed_image[0:border_h, 0:width] = [255, 255, 255]  # BGR 格式的白色

    # 填充底部边缘
    # [height - border_h:height, 0:width] 表示从倒数 border_h 行到最后一行
    processed_image[height - border_h:height, 0:width] = [255, 255, 255]

    # 填充左侧边缘
    # [border_h:height - border_h, 0:border_w] 表示在顶部和底部填充区域之间，从第0列到 border_w-1 列
    processed_image[border_h:height - border_h, 0:border_w] = [255, 255, 255]

    # 填充右侧边缘
    # [border_h:height - border_h, width - border_w:width] 表示在顶部和底部填充区域之间，从倒数 border_w 列到最后一列
    processed_image[border_h:height - border_h, width - border_w:width] = [255, 255, 255]

    print(f"🖼️ 覆盖边缘白色后图像尺寸: {processed_image.shape[1]}x{processed_image.shape[0]} (与原图尺寸相同)")

    # 原始文件大小（KB）
    original_file_size_kb = os.path.getsize(image_path) / 1024
    # 目标文件大小：不超过原图大小
    target_size_kb = original_file_size_kb
    print(f"📏 原始文件大小: {original_file_size_kb:.2f} KB, 目标大小: {target_size_kb:.2f} KB")

    if output_path is None:
        base_name, ext = os.path.splitext(os.path.basename(image_path))
        # 建议保存为JPEG以更好地控制压缩，即使原图是PNG等
        output_path = os.path.join(os.path.dirname(image_path), f"{base_name}_padded_edge.jpg")

    success = compress_to_target_size(processed_image, target_size_kb, output_path)
    if success:
        final_size_kb = os.path.getsize(output_path) / 1024
        print(f"✅ 处理后的图像已保存: {output_path}（最终大小: {final_size_kb:.2f} KB）")
    else:
        print(f"❌ 图像处理并保存失败: {output_path}")


if __name__ == "__main__":
    # 请确保这些路径存在并包含图像文件
    image_path = "/Users/2dqy003/Downloads/ocr-photo/test_aiocr_api/Keyboard-interference/test_case_040.jpg"
    # image_path = "/Users/2dqy003/Downloads/test_aiocr_api/compressed_images/test_case_021.jpg"

    # 可以在这里指定输出路径，否则会默认在原图同目录生成
    # output_directory = "/Users/2dqy003/Downloads/output_images"
    # os.makedirs(output_directory, exist_ok=True) # 确保输出目录存在
    # output_filename = "processed_image_edge.jpg"
    # process_image(image_path, os.path.join(output_directory, output_filename))

    process_image(image_path)