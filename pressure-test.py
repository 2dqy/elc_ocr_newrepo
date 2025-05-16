#!/usr/bin/env python3
import os
import random
import time
import json
import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 手动指定matplotlib使用的字体
plt.rcParams['font.sans-serif'] = ['STFangsong']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 配置参数
BASE_URL = "https://2dqy-ocr.vercel.app/upload/image"  # 目标URL
LOCAL_URL = "http://localhost:8000/upload/image"  # 本地测试URL
TOKEN = "bobtest"  # 测试用token
BLOOD_PRESSURE_DIR = "/Users/2dqy003/Downloads/ocr-photo/blood_pressure"
BLOOD_SUGAR_DIR = "/Users/2dqy003/Downloads/ocr-photo/blood_sugar"
MAX_WORKERS = 10  # 并发线程数
TEST_ROUNDS = 3  # 测试轮次
REQUESTS_PER_ROUND = 10  # 每轮请求数
LOG_DIR = "./pressure-test_logs"  # 日志保存目录
REPORT_FILE = "压力测试报告.md"  # 报告文件名

# 创建日志目录
os.makedirs(LOG_DIR, exist_ok=True)

# 创建时间戳
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"{LOG_DIR}/pressure_test_{timestamp}.log"
result_file = f"{LOG_DIR}/results_{timestamp}.csv"


def get_image_paths():
    """获取所有测试图片路径"""
    bp_images = [str(f) for f in Path(BLOOD_PRESSURE_DIR).glob("*.[jJ][pP][gG]")]
    bp_images += [str(f) for f in Path(BLOOD_PRESSURE_DIR).glob("*.[jJ][pP][eE][gG]")]
    bp_images += [str(f) for f in Path(BLOOD_PRESSURE_DIR).glob("*.[pP][nN][gG]")]

    bs_images = [str(f) for f in Path(BLOOD_SUGAR_DIR).glob("*.[jJ][pP][gG]")]
    bs_images += [str(f) for f in Path(BLOOD_SUGAR_DIR).glob("*.[jJ][pP][eE][gG]")]
    bs_images += [str(f) for f in Path(BLOOD_SUGAR_DIR).glob("*.[pP][nN][gG]")]

    print(f"找到血压图片: {len(bp_images)}张")
    print(f"找到血糖图片: {len(bs_images)}张")

    # 如果没有图片，退出
    if not bp_images and not bs_images:
        print("错误: 未找到测试图片!")
        exit(1)

    return bp_images, bs_images


def send_request(image_path, url=BASE_URL, token=TOKEN):
    """发送单个图像识别请求"""
    start_time = time.time()

    # 准备请求数据
    file_name = os.path.basename(image_path)
    files = {
        'file': (file_name, open(image_path, 'rb'), 'image/jpeg')
    }
    data = {
        'token': token
    }

    try:
        # 发送请求
        response = requests.post(url, files=files, data=data)
        end_time = time.time()
        elapsed = end_time - start_time

        # 处理响应
        status_code = response.status_code
        response_text = response.text

        try:
            response_json = response.json()
            success = response_json.get('status') == 'success'
            api_time = response_json.get('execution_time', 'N/A')
            message = response_json.get('message', '')
            category = response_json.get('data', {}).get('category', 'unknown') if response_json.get(
                'data') else 'unknown'
        except:
            success = False
            api_time = 'N/A'
            message = '解析响应失败'
            category = 'unknown'

        # 创建结果
        result = {
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'image_path': image_path,
            'image_name': file_name,
            'status_code': status_code,
            'success': success,
            'category': category,
            'message': message,
            'api_time': api_time,
            'total_time': f"{elapsed:.2f}秒",
            'response': response_text
        }

        # 记录日志
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"===== 请求: {file_name} =====\n")
            f.write(f"时间: {result['timestamp']}\n")
            f.write(f"状态码: {status_code}\n")
            f.write(f"成功: {success}\n")
            f.write(f"类别: {category}\n")
            f.write(f"消息: {message}\n")
            f.write(f"API执行时间: {api_time}\n")
            f.write(f"总请求时间: {elapsed:.2f}秒\n")
            f.write(f"响应: {response_text}\n\n")

        return result

    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time

        # 记录错误
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"===== 错误请求: {file_name} =====\n")
            f.write(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}\n")
            f.write(f"错误: {str(e)}\n\n")

        return {
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            'image_path': image_path,
            'image_name': file_name,
            'status_code': 0,
            'success': False,
            'category': 'error',
            'message': str(e),
            'api_time': 'N/A',
            'total_time': f"{elapsed:.2f}秒",
            'response': str(e)
        }


def run_test_round(round_num, use_local=False):
    """执行一轮测试"""
    print(f"开始第 {round_num} 轮测试...")

    # 获取图片路径
    bp_images, bs_images = get_image_paths()

    # 随机选择图片
    all_images = bp_images + bs_images
    if len(all_images) > REQUESTS_PER_ROUND:
        selected_images = random.sample(all_images, REQUESTS_PER_ROUND)
    else:
        # 如果图片不够，可以重复使用
        selected_images = []
        for _ in range(REQUESTS_PER_ROUND):
            selected_images.append(random.choice(all_images))

    results = []
    url = LOCAL_URL if use_local else BASE_URL

    # 使用线程池并发发送请求
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_image = {executor.submit(send_request, image, url): image for image in selected_images}

        for future in as_completed(future_to_image):
            image = future_to_image[future]
            try:
                result = future.result()
                results.append(result)
                print(f"完成图片 {os.path.basename(image)}: 状态码={result['status_code']}, 成功={result['success']}")
            except Exception as e:
                print(f"处理图片 {os.path.basename(image)} 出错: {str(e)}")

    print(f"第 {round_num} 轮测试完成，处理了 {len(results)} 张图片")
    return results


def analyze_results(all_results):
    """分析所有测试结果并生成报告"""
    # 转换为DataFrame进行分析
    df = pd.DataFrame(all_results)

    # 转换时间列为数值型以便计算
    df['total_time_seconds'] = df['total_time'].apply(lambda x: float(x.replace('秒', '')))

    # 保存原始结果
    df.to_csv(result_file, index=False, encoding='utf-8-sig')

    # 计算统计指标
    total_requests = len(df)
    successful_requests = len(df[df['success'] == True])
    success_rate = successful_requests / total_requests * 100 if total_requests > 0 else 0

    avg_response_time = df['total_time_seconds'].mean()
    max_response_time = df['total_time_seconds'].max()
    min_response_time = df['total_time_seconds'].min()
    p95_response_time = df['total_time_seconds'].quantile(0.95)

    # 统计请求分类
    category_counts = df['category'].value_counts().to_dict()
    error_counts = len(df[df['success'] == False])

    # 生成时间序列图表
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(df)), df['total_time_seconds'], marker='o', linestyle='-')
    plt.title('请求响应时间')
    plt.xlabel('请求序号')
    plt.ylabel('响应时间(秒)')
    plt.grid(True)
    chart_file = f"{LOG_DIR}/response_time_chart_{timestamp}.png"
    plt.savefig(chart_file)

    # 创建报告
    report = f"""# OCR接口压力测试报告

## 测试概述
- 测试时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 测试目标: {BASE_URL}
- 测试轮次: {TEST_ROUNDS}
- 每轮请求数: {REQUESTS_PER_ROUND}
- 最大并发数: {MAX_WORKERS}

## 测试结果摘要
- 总请求数: {total_requests}
- 成功请求数: {successful_requests}
- 成功率: {success_rate:.2f}%
- 平均响应时间: {avg_response_time:.2f}秒
- 最大响应时间: {max_response_time:.2f}秒
- 最小响应时间: {min_response_time:.2f}秒
- 95%响应时间: {p95_response_time:.2f}秒

## 请求分类统计
"""

    for category, count in category_counts.items():
        percentage = count / total_requests * 100
        report += f"- {category}: {count}个 ({percentage:.2f}%)\n"

    report += f"- 失败请求: {error_counts}个 ({error_counts / total_requests * 100:.2f}%)\n\n"

    report += f"""## 测试详情
- 详细日志文件: {log_file}
- 结果数据文件: {result_file}
- 响应时间图表: {chart_file}

![响应时间图表]({os.path.basename(chart_file)})
"""

    # 写入报告
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"测试报告已生成: {REPORT_FILE}")
    return {
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'max_response_time': max_response_time,
        'min_response_time': min_response_time,
        'p95_response_time': p95_response_time,
    }


def main():
    """主函数"""
    print(f"=== OCR接口压力测试开始 ===")
    print(f"目标URL: {BASE_URL}")
    print(f"测试轮次: {TEST_ROUNDS}")
    print(f"每轮请求数: {REQUESTS_PER_ROUND}")
    print(f"最大并发数: {MAX_WORKERS}")
    print(f"日志文件: {log_file}")

    # 初始化日志文件
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"=== OCR接口压力测试 ===\n")
        f.write(f"开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"目标URL: {BASE_URL}\n")
        f.write(f"测试轮次: {TEST_ROUNDS}\n")
        f.write(f"每轮请求数: {REQUESTS_PER_ROUND}\n")
        f.write(f"最大并发数: {MAX_WORKERS}\n\n")

    all_results = []

    # 获取用户选择
    use_local = input("是否使用本地URL测试? (y/n): ").lower() == 'y'

    # 执行测试轮次
    for round_num in range(1, TEST_ROUNDS + 1):
        results = run_test_round(round_num, use_local)
        all_results.extend(results)

        # 轮次之间稍微暂停，避免过于频繁的请求
        if round_num < TEST_ROUNDS:
            print(f"等待3秒后开始下一轮...")
            time.sleep(3)

    # 分析结果
    stats = analyze_results(all_results)

    print("\n=== 测试完成 ===")
    print(f"总请求数: {stats['total_requests']}")
    print(f"成功率: {stats['success_rate']:.2f}%")
    print(f"平均响应时间: {stats['avg_response_time']:.2f}秒")
    print(f"95%响应时间: {stats['p95_response_time']:.2f}秒")
    print(f"详细报告: {REPORT_FILE}")


if __name__ == "__main__":
    main()