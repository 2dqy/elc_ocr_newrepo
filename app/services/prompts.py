"""
OCR模型提示词配置文件
包含千问、OpenAI和Gemini模型的提示词
"""
def get_openai_prompt() -> str:
    """获取OpenAI模型的提示词"""
    return """Extract the three most important LCD font digits values in this image. Pay attention to the following rules:
1. Correct placement of decimal points is critical. Do not ignore decimal points.
2. Extract the numbers explicitly based on their **row position on the screen**, following this exact logic:
   - Assign the **top-most row value (SYS)** to 'primary'.
   - Assign the **middle row value (DIA)** to 'secondary'.
   - Assign the **bottom-most row value (PUL)** to 'tertiary'.
3. Ignore small numbers displayed as part of time, date(e.g., 18:31).
4. The value of category can only be "blood_pressure", "blood_sugar" or "Not relevant".
5. If an error code (e.g., E20, E4, Err) is detected, return the following error: {"error": "There seems to be an issue with the device"}.
Output format:
- For three values: {"name": if detected, "SYS": top row number (integer), "DIA": middle row number (integer), "PUL": bottom row number (integer)}
- For one value: {"name": if detected the brand name, "glucose": detected value (formatted as float)}
- For error codes: {"error": "There seems to be an issue with the device"}
- Pay attention to decimal points. If you get it wrong, it will be the end of the world.
- Seven-segment number processing:
a. Pay attention to the confusion of the number form (1 vs 7, 2 vs 5).
b. The decimal point may be an independent dot symbol. If it is difficult to identify, guess it based on the normal blood sugar range (2.0–20.0 mmol/L):
c. For example, "15" may be "1.5", and "179" may be "17.9".
If the image does not contain a seven-segment display or relevant data, set the category to "Not relevant".
If the image does not contain a seven-segment display or relevant data, set the category to "Not relevant".
"""


def get_qwen_prompt() -> str:
    """获取千问模型的提示词"""
    return """请仔细分析上传的图像，执行以下步骤并返回结果：

1. 图片相关性判断：
   - 首先判断图像是否包含血压计或血糖仪的显示屏或数据。
   - 如果图像不包含血压计或血糖仪相关内容（例如，风景照、人物照或其他无关图片），请按照以下JSON格式返回数据：
        "data": {
                "category": "Not relevant"，
                }后续提示词可忽略                                 

2. 设备类型判断：
   - 血压计数据：收缩压(SYS)、舒张压(DIA)、心率(PUL)
   - 血糖仪数据：血糖值

3. 关注信息：
   - 医疗设备品牌和型号
   - 测量时间（从图片中提取，格式 HH:mm:ss，如果无法提取则返回 null）
   - 测量数值            

请按照以下JSON格式返回数据：
"data": {
        "brand": "设备品牌",
        "measure_date": "当前日期",
        "measure_time": "图片中的测量时间",
        "category": "blood_pressure 或 blood_sugar",
        "blood_pressure": {
            "sys": "收缩压值",
            "dia": "舒张压值",
            "pul": "心率值"
        },
        "blood_sugar": "血糖值",
        "other_value": "其他数据",
        "suggest": "基于数据的 AI 健康建议",
        "analyze_reliability": 0.95,
        "status": "分析状态（例如 'completed', 'failed'）",
        }
注意事项：
    1. 如果是血压数据，blood_sugar字段设为null
    2. 如果是血糖数据，blood_pressure对象的所有字段设为null
    3. 时间必须从图片中提取，如果无法提取则返回null
    4. 请根据数值给出专业的健康建议
    5. 确保分析准确，不要捏造数据
    6. 如果图片不包含血压计或血糖仪数据，设置category 为 "error"，其他值为空。
    7. 如果一個大數字看起來明顯不合常理（如 179 mmol/L），請判斷是否可能是 17.9。
    8. 嘗試根據格式規律（血糖值通常介於 2.0 到 20.0）來做小數推論。
    9. 如果一個大數字看起來明顯不合常理（如 179 mmol/L），請判斷是否可能是 17.9。
    10. 注意小數點，錯了會世界末日。
    11. 嘗試根據格式規律（血糖值通常介於 0.0 到 20.0）來做小數推論。
    12. 這可能一張血糖測試儀的螢幕照片。請辨識畫面中的數字值，並注意數字中可能有小數點，尤其數值應該合理在 0 到 20 之間。請特別檢查「1.5」和「15」的差別，小數點若難以分辨，也請根據螢幕樣式或格式合理推斷
"""


def get_gemini_prompt() -> str:
    """获取Gemini模型的提示词"""
    return """Please carefully analyze the uploaded image, perform the following steps and return the result:

1. Image relevance judgment:
- First determine whether the image contains the display or data of a blood pressure meter or blood glucose meter.
- If the image does not contain blood pressure meter or blood glucose meter related content (for example, landscape photos, portrait photos or other irrelevant pictures), please return the data in the following JSON format:
"data": {
"category": "Not relevant"
}
Subsequent prompt words can be ignored

2. Device type judgment:
- Blood pressure meter data: systolic pressure (SYS), diastolic pressure (DIA), heart rate (PUL)
- Blood glucose meter data: blood glucose value

3. Information of interest:
- Medical device brand and model
- Measurement time (extracted from the image, format HH:mm:ss, if it cannot be extracted, null is returned)
- Measurement value

Please return the data in the following JSON format:
"data": {
"brand": "Device brand",
"measure_date": "Current date",
"measure_time": "Measurement time in the image",
"category": "blood_pressure or blood_sugar or Not relevant",
"blood_pressure": {
"sys": "Systolic pressure value",
"dia": "Diastolic pressure value",
"pul": "heart rate value"
},
"blood_sugar": "blood sugar value",
"other_value": "other data",
"suggest": "data-based AI health advice",
"analyze_reliability": 0.95,
"status": "analysis status (e.g. 'completed', 'failed')"
}
Notes:
1. If it is blood pressure data, the blood_sugar field is set to null
2. If it is blood sugar data, all fields of the blood_pressure object are set to null
3. The time must be extracted from the image, and null is returned if it cannot be extracted
4. Please give professional health advice based on the value
5. Ensure that the analysis is accurate and do not fabricate data
6. If the image does not contain blood pressure meter or blood glucose meter data, set category to "Not relevant".
7. If a large number looks obviously unreasonable (such as 179 mmol/L), please judge whether it is likely to be 17.9.
8. Try to make decimal inferences based on the format (blood sugar values are usually between 2.0 and 20.0).
9. If a large number seems obviously unreasonable (such as 179 mmol/L), please judge whether it is likely to be 17.9.
10. Pay attention to decimal points. If you get it wrong, it will be the end of the world.
11. Try to make decimal inferences based on the format (blood sugar values are usually between 0.0 and 20.0).
12. This may be a picture of a blood sugar tester screen. Please identify the numerical value on the screen and pay attention to the possibility of decimal points in the number, especially the number should be reasonably between 0 and 20. Please check the difference between "1.5" and "15" in particular. If the decimal point is difficult to distinguish, please make a reasonable inference based on the screen style or format.
"""


