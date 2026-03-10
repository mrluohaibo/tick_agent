#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: WebSocket连接管理和消息协议定义
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from utils.logger_config import logger


# ========================================================================
# 消息协议定义
# ========================================================================

class MessageType:
    """消息类型常量"""
    ANOMALY_ALERT = "anomaly_alert"
    ATTRIBUTION_RESULT = "attribution_result"
    INTRADAY_ALERT = "intraday_alert"
    SYSTEM_NOTICE = "system_notice"


class AnomalyMessage(BaseModel):
    """异动通知消息模型"""
    board_name: str = Field(..., description="板块名称")
    change_rate: float = Field(..., description="涨跌幅")
    reason: str = Field(default="", description="异动原因")
    news_title: str = Field(default="", description="相关新闻标题")
    confidence: float = Field(default=0.0, description="置信度")
    trigger_time: Optional[str] = Field(default=None, description="触发时间")


class AttributionMessage(BaseModel):
    """归因结果消息模型"""
    board_name: str = Field(..., description="板块名称")
    attribution_type: str = Field(..., description="归因类型")
    reason_description: str = Field(..., description="归因描述")
    confidence: float = Field(..., description="置信度")
    related_news: List[str] = Field(default_factory=list, description="相关新闻")


class IntradayAlertMessage(BaseModel):
    """盘中快讯消息模型"""
    alert_time: str = Field(..., description="预警时间")
    top_boards: List[Dict] = Field(default_factory=list, description="领涨板块")
    core_reason: str = Field(default="", description="核心原因")
    key_news: List[str] = Field(default_factory=list, description="关键新闻")


class WSMessage(BaseModel):
    """通用WebSocket消息"""
    type: str = Field(..., description="消息类型")
    data: Dict = Field(default_factory=dict, description="消息数据")
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), description="时间戳")


# ========================================================================
# WebSocket连接管理器
# ========================================================================

class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

        # 发送欢迎消息
        welcome_msg = WSMessage(
            type=MessageType.SYSTEM_NOTICE,
            data={
                "message": "已连接到智能股票板块异动分析系统",
                "connection_count": len(self.active_connections)
            }
        )
        await websocket.send_json(welcome_msg.dict())

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: WSMessage, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message.dict())
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: WSMessage):
        """广播消息给所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message.dict())
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)

        # 移除断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_anomaly(self, anomaly_data: Dict):
        """广播异动通知"""
        message = WSMessage(
            type=MessageType.ANOMALY_ALERT,
            data={
                "board_name": anomaly_data.get("board_name", ""),
                "change_rate": anomaly_data.get("change_rate", 0),
                "reason": anomaly_data.get("reason", ""),
                "news_title": anomaly_data.get("news_title", ""),
                "confidence": anomaly_data.get("confidence", 0),
                "trigger_time": anomaly_data.get("trigger_time")
            }
        )
        await self.broadcast(message)
        logger.info(f"已广播异动通知: {anomaly_data.get('board_name', '')}")

    async def broadcast_attribution(self, attribution_data: Dict):
        """广播归因结果"""
        message = WSMessage(
            type=MessageType.ATTRIBUTION_RESULT,
            data={
                "board_name": attribution_data.get("board_name", ""),
                "attribution_type": attribution_data.get("attribution_type", ""),
                "reason_description": attribution_data.get("reason_description", ""),
                "confidence": attribution_data.get("confidence", 0),
                "related_news": attribution_data.get("related_news", [])
            }
        )
        await self.broadcast(message)
        logger.info(f"已广播归因结果: {attribution_data.get('board_name', '')}")

    async def broadcast_intraday_alert(self, alert_data: Dict):
        """广播盘中快讯"""
        message = WSMessage(
            type=MessageType.INTRADAY_ALERT,
            data={
                "alert_time": alert_data.get("alert_time", datetime.now().strftime("%H:%M")),
                "top_boards": alert_data.get("top_boards", []),
                "core_reason": alert_data.get("core_reason", ""),
                "key_news": alert_data.get("key_news", [])
            }
        )
        await self.broadcast(message)
        logger.info("已广播盘中快讯")

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()


# ========================================================================
# 测试代码
# ========================================================================

if __name__ == "__main__":
    # 测试消息模型
    import asyncio

    async def test_messages():
        """测试消息模型"""

        # 测试异动消息
        anomaly_msg = AnomalyMessage(
            board_name="半导体",
            change_rate=3.2,
            reason="政策驱动",
            news_title="国家大基金三期成立",
            confidence=0.85
        )
        print("异动消息:")
        print(json.dumps(anomaly_msg.dict(), ensure_ascii=False, indent=2))

        # 测试归因消息
        attribution_msg = AttributionMessage(
            board_name="新能源",
            attribution_type="policy",
            reason_description="政策支持新能源发展",
            confidence=0.9
        )
        print("\n归因消息:")
        print(json.dumps(attribution_msg.dict(), ensure_ascii=False, indent=2))

    asyncio.run(test_messages())
