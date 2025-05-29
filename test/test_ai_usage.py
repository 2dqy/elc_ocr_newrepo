#!/usr/bin/env python3
"""
测试AI Usage计算功能
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_ai_usage_calculation():
    """测试AI Usage计算功能"""
    
    print("=== AI Usage 计算测试 ===")
    
    # 模拟千问模型的usage信息
    print("\n1. 测试千问模型 Usage 计算:")
    qwen_usage = {
        "total_tokens": 1500,
        "input_tokens": 1200,
        "output_tokens": 300
    }
    
    total_tokens = qwen_usage.get("total_tokens", 0)
    ai_usage_value = total_tokens * 10 if total_tokens > 0 else 100
    print(f"   千问模型 - total_tokens: {total_tokens}")
    print(f"   千问模型 - ai_usage_value: {ai_usage_value}")
    
    # 模拟OpenAI模型的usage信息
    print("\n2. 测试OpenAI模型 Usage 计算:")
    openai_usage = {
        "total_tokens": 1187,
        "prompt_tokens": 1042,
        "completion_tokens": 145
    }
    
    total_tokens = openai_usage.get("total_tokens", 0)
    ai_usage_value = total_tokens * 10 if total_tokens > 0 else 100
    print(f"   OpenAI模型 - total_tokens: {total_tokens}")
    print(f"   OpenAI模型 - ai_usage_value: {ai_usage_value}")
    
    # 测试无usage信息的情况
    print("\n3. 测试无Usage信息的情况:")
    empty_usage = {}
    total_tokens = empty_usage.get("total_tokens", 0)
    ai_usage_value = total_tokens * 10 if total_tokens > 0 else 100
    print(f"   无Usage信息 - total_tokens: {total_tokens}")
    print(f"   无Usage信息 - ai_usage_value: {ai_usage_value} (默认值)")
    
    print("\n=== 测试完成 ===")
    print("\nUsage计算规则:")
    print("- 有token信息时: ai_usage_value = total_tokens * 10")
    print("- 无token信息时: ai_usage_value = 100 (默认值)")

if __name__ == "__main__":
    test_ai_usage_calculation() 