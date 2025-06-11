# """
# Dashboard数据分析服务
# """
# import pandas as pd
# from typing import Dict, List, Any
# from app.models.database import DashboardRepository
# from datetime import datetime
# from decimal import Decimal
#
#
# class DashboardService:
#     """Dashboard数据分析服务类"""
#
#     @staticmethod
#     def get_dashboard_analysis(year_month: str) -> Dict[str, Any]:
#         """
#         获取Dashboard分析数据
#
#         Args:
#             year_month: 年月格式 'YYYY-MM'
#
#         Returns:
#             包含各种分析结果的字典
#         """
#         # 获取原始数据
#         raw_data = DashboardRepository.get_dashboard_data(year_month)
#
#         if not raw_data:
#             return {
#                 "total_requests": 0,
#                 "success_rate_overall": 0,
#                 "center_stats": [],
#                 "error_analysis": [],
#                 "center_ranking": [],
#                 "device_analysis": [],
#                 "avg_processing_time": 0,
#                 "raw_data": []
#             }
#
#         # 转换为DataFrame
#         df = pd.DataFrame(raw_data)
#
#         # 1. OCR请求总数（按中心分组）
#         center_requests = df.groupby('center_id').size().reset_index(name='total_requests')
#
#         # 2. 成功率和失败率分析
#         # 总体成功率
#         total_requests = len(df)
#         success_count = len(df[df['status'] == 'success'])
#         overall_success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
#
#         # 按中心的成功率
#         center_success_stats = []
#         for center_id in df['center_id'].unique():
#             if pd.isna(center_id):
#                 continue
#
#             center_data = df[df['center_id'] == center_id]
#             center_total = len(center_data)
#             center_success = len(center_data[center_data['status'] == 'success'])
#             center_failed = len(center_data[center_data['status'] == 'failed'])
#
#             success_rate = (center_success / center_total * 100) if center_total > 0 else 0
#
#             center_success_stats.append({
#                 'center_id': center_id,
#                 'total_requests': center_total,
#                 'success_count': center_success,
#                 'failed_count': center_failed,
#                 'success_rate': round(success_rate, 2)
#             })
#
#         # 3. 失败原因分析
#         failed_data = df[df['status'] == 'failed']
#         error_analysis = []
#         if len(failed_data) > 0:
#             error_counts = failed_data['error_message'].value_counts()
#             for error_msg, count in error_counts.items():
#                 error_analysis.append({
#                     'error_message': error_msg if pd.notna(error_msg) else 'Unknown Error',
#                     'count': count,
#                     'percentage': round(count / len(failed_data) * 100, 2)
#                 })
#
#         # 4. 按使用情况排名的中心
#         center_ranking = df[df['status'] == 'success'].groupby('center_id').size().reset_index(name='success_count')
#         center_ranking = center_ranking.sort_values('success_count', ascending=False)
#         center_ranking_list = []
#         for idx, row in center_ranking.iterrows():
#             if pd.notna(row['center_id']):
#                 center_ranking_list.append({
#                     'rank': len(center_ranking_list) + 1,
#                     'center_id': row['center_id'],
#                     'success_count': row['success_count']
#                 })
#
#         # 5. 设备类型分析（新增）
#         device_analysis = []
#         if 'device_type' in df.columns:
#             device_stats = df.groupby('device_type').agg({
#                 'status': ['count', lambda x: (x == 'success').sum()],
#                 'processing_time': 'mean' if 'processing_time' in df.columns else lambda x: None
#             }).round(3)
#
#             for device_type in df['device_type'].unique():
#                 if pd.isna(device_type):
#                     continue
#                 device_data = df[df['device_type'] == device_type]
#                 device_total = len(device_data)
#                 device_success = len(device_data[device_data['status'] == 'success'])
#                 device_success_rate = (device_success / device_total * 100) if device_total > 0 else 0
#
#                 # 计算该设备类型的平均处理时间
#                 device_processing_times = device_data['processing_time'].dropna()
#                 avg_processing_time = 0
#                 if len(device_processing_times) > 0:
#                     # 转换Decimal到float进行计算
#                     processing_times = [float(pt) if isinstance(pt, Decimal) else pt for pt in device_processing_times if pt is not None]
#                     if processing_times:
#                         avg_processing_time = round(sum(processing_times) / len(processing_times), 3)
#
#                 device_analysis.append({
#                     'device_type': device_type,
#                     'total_requests': device_total,
#                     'success_count': device_success,
#                     'success_rate': round(device_success_rate, 2),
#                     'avg_processing_time': avg_processing_time
#                 })
#
#         # 6. 计算真实的平均处理时间
#         avg_processing_time = 0
#         if 'processing_time' in df.columns:
#             processing_times = df['processing_time'].dropna()
#             if len(processing_times) > 0:
#                 # 转换Decimal到float进行计算
#                 times = [float(pt) if isinstance(pt, Decimal) else pt for pt in processing_times if pt is not None]
#                 if times:
#                     avg_processing_time = round(sum(times) / len(times), 3)
#
#         # 如果没有真实的处理时间数据，使用估算值
#         if avg_processing_time == 0:
#             avg_processing_time = 2.5  # 默认估算值
#
#         # 7. 按中心统计的Token使用次数趋势分析（修改）
#         center_token_trends = []
#         if 'timestamp' in df.columns and 'token' in df.columns and 'center_id' in df.columns:
#             # 将timestamp转换为日期
#             df['date'] = pd.to_datetime(df['timestamp']).dt.date
#
#             # 按center和日期分组，计算每个中心每日的token使用总次数
#             center_usage_by_date = df.groupby(['center_id', 'date']).size().reset_index(name='token_usage_count')
#
#             # 为每个center创建时间序列数据
#             for center_id in df['center_id'].unique():
#                 if pd.isna(center_id):
#                     continue
#
#                 center_data = center_usage_by_date[center_usage_by_date['center_id'] == center_id]
#
#                 # 只处理有足够数据的center（总使用次数>=10）
#                 total_center_usage = len(df[df['center_id'] == center_id])
#                 if total_center_usage >= 10:
#                     time_series = []
#                     for _, row in center_data.iterrows():
#                         time_series.append({
#                             'date': row['date'].strftime('%Y-%m-%d'),
#                             'token_usage_count': row['token_usage_count']
#                         })
#
#                     if time_series:
#                         center_token_trends.append({
#                             'center_id': str(center_id),
#                             'data': time_series
#                         })
#
#         # 8. Token综合统计分析（合并原来的两个分析）
#         token_comprehensive_stats = []
#         if 'token' in df.columns:
#             for token in df['token'].unique():
#                 if pd.isna(token):
#                     continue
#
#                 token_data = df[df['token'] == token]
#                 total_usage = len(token_data)
#
#                 if total_usage >= 3:  # 只分析使用次数>=3的token
#                     # 基本统计
#                     token_success = len(token_data[token_data['status'] == 'success'])
#                     token_success_rate = (token_success / total_usage * 100) if total_usage > 0 else 0
#
#                     # 计算该token的平均处理时间
#                     token_processing_times = token_data['processing_time'].dropna()
#                     token_avg_time = 0
#                     if len(token_processing_times) > 0:
#                         times = [float(pt) if isinstance(pt, Decimal) else pt for pt in token_processing_times if pt is not None]
#                         if times:
#                             token_avg_time = round(sum(times) / len(times), 3)
#
#                     # 频率分析
#                     df_with_date = token_data.copy()
#                     df_with_date['date'] = pd.to_datetime(df_with_date['timestamp']).dt.date
#                     df_with_date['hour'] = pd.to_datetime(df_with_date['timestamp']).dt.hour
#
#                     # 计算日使用频率
#                     daily_usage = df_with_date.groupby('date').size()
#                     avg_daily_usage = round(daily_usage.mean(), 2) if len(daily_usage) > 0 else 0
#                     max_daily_usage = daily_usage.max() if len(daily_usage) > 0 else 0
#
#                     # 计算使用的中心数量和中心列表
#                     centers_used_list = token_data['center_id'].dropna().unique()
#                     centers_used_count = len(centers_used_list)
#                     centers_used_str = ', '.join([str(c) for c in centers_used_list[:3]])  # 只显示前3个
#                     if len(centers_used_list) > 3:
#                         centers_used_str += f' (+{len(centers_used_list)-3}个)'
#
#                     # 最常使用的时间段
#                     hourly_usage = df_with_date.groupby('hour').size()
#                     peak_hour = hourly_usage.idxmax() if len(hourly_usage) > 0 else 0
#
#                     token_comprehensive_stats.append({
#                         'token': str(token)[:20] + '...' if len(str(token)) > 20 else str(token),
#                         'full_token': str(token),
#                         'usage_count': total_usage,
#                         'success_rate': round(token_success_rate, 2),
#                         'avg_processing_time': token_avg_time,
#                         'avg_daily_usage': avg_daily_usage,
#                         'max_daily_usage': int(max_daily_usage),
#                         'centers_used_count': centers_used_count,
#                         'centers_used_list': centers_used_str,
#                         'peak_hour': f"{peak_hour}:00-{peak_hour+1}:00"
#                     })
#
#             # 按总使用次数排序
#             token_comprehensive_stats.sort(key=lambda x: x['usage_count'], reverse=True)
#
#         return {
#             "year_month": year_month,
#             "total_requests": total_requests,
#             "success_rate_overall": round(overall_success_rate, 2),
#             "center_stats": center_success_stats,
#             "error_analysis": error_analysis,
#             "center_ranking": center_ranking_list,
#             "device_analysis": device_analysis,
#             "avg_processing_time": avg_processing_time,
#             "center_token_trends": center_token_trends,
#             "token_comprehensive_stats": token_comprehensive_stats,
#             "raw_data": raw_data[:1000]  # 限制返回数据量，只返回前1000条
#         }
#
#     @staticmethod
#     def get_available_months() -> List[str]:
#         """
#         获取可用的年月列表
#
#         Returns:
#             年月列表
#         """
#         return DashboardRepository.get_available_months()
#
#     @staticmethod
#     def get_current_month() -> str:
#         """
#         获取当前月份
#
#         Returns:
#             当前月份，格式为 'YYYY-MM'
#         """
#         return datetime.now().strftime('%Y-%m')