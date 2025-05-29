#!/usr/bin/env python3
"""
测试模型切换功能
"""
import os
from dotenv import load_dotenv
from app.services.model_fun import get_ocr_model

# 加载环境变量
load_dotenv()

def test_model_switch():
    """测试模型切换功能"""
    
    print("=== OCR 模型切换测试 ===")
    
    # 测试千问模型
    print("\n1. 测试千问模型:")
    try:
        qwen_model = get_ocr_model("qwen")
        print(f"✅ 千问模型创建成功: {type(qwen_model).__name__}")
        print(f"   模型名称: {qwen_model.model}")
        print(f"   API密钥: {qwen_model.api_key[:10]}..." if qwen_model.api_key else "   API密钥: 未设置")
    except Exception as e:
        print(f"❌ 千问模型创建失败: {str(e)}")
    
    # 测试OpenAI模型
    print("\n2. 测试OpenAI模型:")
    try:
        openai_model = get_ocr_model("openai")
        print(f"✅ OpenAI模型创建成功: {type(openai_model).__name__}")
        print(f"   部署名称: {openai_model.deployment}")
        print(f"   模型名称: {openai_model.model}")
        print(f"   端点: {openai_model.client._base_url}")
    except Exception as e:
        print(f"❌ OpenAI模型创建失败: {str(e)}")
    
    # 测试环境变量控制
    print("\n3. 测试环境变量控制:")
    current_model_type = os.getenv("MODEL_TYPE", "qwen")
    print(f"当前环境变量 MODEL_TYPE: {current_model_type}")
    
    try:
        default_model = get_ocr_model()
        print(f"✅ 默认模型创建成功: {type(default_model).__name__}")
    except Exception as e:
        print(f"❌ 默认模型创建失败: {str(e)}")
    
    print("\n=== 测试完成 ===")
    print("\n使用说明:")
    print("1. 在 .env 文件中设置 MODEL_TYPE=qwen 使用千问模型")
    print("2. 在 .env 文件中设置 MODEL_TYPE=openai 使用OpenAI模型")
    print("3. 确保相应的API密钥已正确配置")

if __name__ == "__main__":
    test_model_switch() 