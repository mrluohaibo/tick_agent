#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: FastAPI主应用
提供WebSocket接口进行异动实时推送
"""

import os
import sys
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.config_init import application_conf
from utils.logger_config import logger
from api.websocket_manager import WebSocketManager, AnomalyMessage
from bz_agent.graph.news_nodes import NewsAnalysisAgent
from bz_agent.graph.sector_nodes import SectorMonitorAgent
from bz_agent.graph.reason_nodes import AttributionAgent
from bz_agent.graph.report_nodes import ReportAgent

# 创建FastAPI应用
app = FastAPI(
    title="智能股票板块异动分析系统",
    description="实时监控板块异动，自动归因分析，生成投资报告",
    version="1.0.0"
)

# WebSocket连接管理器
websocket_manager = WebSocketManager()

# 初始化Agent
news_agent = NewsAnalysisAgent()
sector_agent = SectorMonitorAgent()
attribution_agent = AttributionAgent()
report_agent = ReportAgent()


# ========================================================================
# 数据模型
# ========================================================================

class TaskRequest(BaseModel):
    """任务请求模型"""
    task_type: str  # 任务类型: news_analysis, sector_monitor, attribution, report
    params: dict = {}  # 任务参数


class APIResponse(BaseModel):
    """API响应模型"""
    status: str
    message: str
    data: dict = {}


# ========================================================================
# 路由定义
# ========================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "system": "智能股票板块异动分析系统",
        "version": "1.0.0",
        "status": "running",
        "websocket_endpoint": "/ws/anomaly"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/api/boards/top")
async def get_top_boards(limit: int = 10):
    """获取领涨板块"""
    try:
        # 这里需要调用QuoteCollector的方法
        # 暂时返回空数据
        return {
            "status": "success",
            "data": {
                "boards": [],
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"获取领涨板块失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/anomalies")
async def get_anomalies(limit: int = 20):
    """获取异动板块列表"""
    try:
        anomalies = sector_agent.get_anomaly_list(limit=limit)
        return {
            "status": "success",
            "data": {
                "anomalies": anomalies,
                "count": len(anomalies)
            }
        }
    except Exception as e:
        logger.error(f"获取异动板块失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/attribution/{board_name}")
async def get_attribution(board_name: str, hours: int = 24):
    """获取指定板块的归因结果"""
    try:
        attributions = attribution_agent.get_attribution_results(board_name=board_name, hours=hours)
        return {
            "status": "success",
            "data": {
                "board_name": board_name,
                "attribution": attributions[0] if attributions else None,
                "count": len(attributions)
            }
        }
    except Exception as e:
        logger.error(f"获取归因结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/news_analysis")
async def trigger_news_analysis(request: TaskRequest):
    """触发新闻分析任务"""
    try:
        # 调用新闻分析Agent
        event_id = request.params.get("event_id")

        if event_id:
            result = news_agent.analyze_news_by_id(event_id)
            return APIResponse(
                status="success",
                message="新闻分析任务已执行",
                data=result
            )
        else:
            # 批量分析
            processed = news_agent.process_unanalyzed_news(limit=50)
            return APIResponse(
                status="success",
                message=f"批量分析了 {processed} 条新闻",
                data={"processed_count": processed}
            )
    except Exception as e:
        logger.error(f"触发新闻分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/sector_monitor")
async def trigger_sector_monitor(request: TaskRequest):
    """触发板块监控任务"""
    try:
        # 调用板块监控Agent
        anomalies = sector_agent.detect_anomalies()
        return APIResponse(
            status="success",
            message=f"检测到 {len(anomalies)} 个异动板块",
            data={"anomalies": anomalies}
        )
    except Exception as e:
        logger.error(f"触发板块监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/attribution")
async def trigger_attribution(request: TaskRequest):
    """触发归因分析任务"""
    try:
        # 调用归因分析Agent
        processed = attribution_agent.process_unprocessed_anomalies(limit=20)
        return APIResponse(
            status="success",
            message=f"完成了 {processed} 个异动的归因分析",
            data={"processed_count": processed}
        )
    except Exception as e:
        logger.error(f"触发归因分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/report")
async def generate_report(request: TaskRequest):
    """生成报告"""
    try:
        report_type = request.params.get("type", "intraday")

        if report_type == "intraday":
            content = report_agent.generate_intraday_alert()
            return APIResponse(
                status="success",
                message="盘中快讯生成成功",
                data={"report_type": "intraday", "content": content}
            )
        elif report_type == "post_market":
            report_data = report_agent.generate_post_market_report()
            return APIResponse(
                status="success",
                message="盘后报告生成成功",
                data={"report_type": "post_market", "report": report_data}
            )
        else:
            raise HTTPException(status_code=400, detail="无效的报告类型")
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# WebSocket端点
# ========================================================================

@app.websocket("/ws/anomaly")
async def websocket_anomaly(websocket: WebSocket):
    """异动推送WebSocket端点"""
    await websocket_manager.connect(websocket)
    logger.info(f"WebSocket客户端已连接: {websocket.client}")

    try:
        while True:
            # 接收客户端消息（保持连接）
            data = await websocket.receive_text()
            logger.debug(f"收到WebSocket消息: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket客户端已断开: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket异常: {e}")
        websocket_manager.disconnect(websocket)


# ========================================================================
# 辅助功能
# ========================================================================

@app.post("/api/publish/anomaly")
async def publish_anomaly(message: AnomalyMessage):
    """发布异动通知（供其他服务调用）"""
    try:
        await websocket_manager.broadcast_anomaly(message.dict())
        return APIResponse(
            status="success",
            message="异动通知已推送",
            data={"message": message.dict()}
        )
    except Exception as e:
        logger.error(f"发布异动通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================================================
# 启动服务
# ========================================================================

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """启动FastAPI服务"""
    logger.info(f"正在启动FastAPI服务: http://{host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    # 从配置读取
    host = application_conf.get_properties("push.websocket.host") or "0.0.0.0"
    port = int(application_conf.get_properties("push.websocket.port") or 8000)

    start_server(host=host, port=port)
