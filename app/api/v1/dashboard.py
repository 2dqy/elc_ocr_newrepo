"""
Dashboard API接口
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from app.services.dashboard_service import DashboardService
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard")


@router.get("/data")
async def get_dashboard_data(year_month: Optional[str] = Query(None, description="年月格式 YYYY-MM，不提供则使用当前月份")):
    """
    获取Dashboard分析数据
    
    参数:
        year_month: 年月格式，例如 "2025-01"，不提供则默认使用当前月份
    
    返回:
        包含各种分析数据的JSON响应
    """
    try:
        # 如果没有提供year_month，使用当前月份
        if not year_month:
            year_month = DashboardService.get_current_month()
        
        # 验证年月格式
        if len(year_month) != 7 or year_month[4] != '-':
            raise HTTPException(
                status_code=400,
                detail="年月格式错误，应为 YYYY-MM 格式，例如 2025-01"
            )
        
        # 获取分析数据
        analysis_data = DashboardService.get_dashboard_analysis(year_month)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": analysis_data
            }
        )
        
    except Exception as e:
        logger.error(f"获取Dashboard数据失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取Dashboard数据失败: {str(e)}"
        )


@router.get("/months")
async def get_available_months():
    """
    获取有数据的月份列表
    
    返回:
        可用月份列表和当前月份
    """
    try:
        months = DashboardService.get_available_months()
        current_month = DashboardService.get_current_month()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "months": months,
                    "current_month": current_month
                }
            }
        )
        
    except Exception as e:
        logger.error(f"获取可用月份失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取可用月份失败: {str(e)}"
        ) 