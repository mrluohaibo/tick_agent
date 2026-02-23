#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: WebSocket连接管理和消息协议定义
"""

import json
from datetime import datetime
from typing import List, Dict
from fastapi import WebSocket, WebSocketDisconnect

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


class AnomalyMessage:
    """异动通知消息模型"""

    def __init__(
        self,
        board_name: str,
        change_rate: float,
        reason: str = "",
        news_title: str = "",
        confidence: float = 0.0,
        trigger_time: str = None
    ):
        self.type = MessageType.ANOMALY_ALERT
        self.data = {
            "board_name": board_name,
            "change_rate": change_rate,
            "reason": reason,
            "news_title": news_title,
            "confidence": confidence,
            "trigger_time": trigger_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }


class AttributionMessage:
    """归因结果消息模型"""

    def __init__(
        self,
        board_name: str,
        attribution_type: str,
        reason_description: str,
        confidence: float,
        related_news: List[str] = None
    ):
        self.type = MessageType.ATTRIBUTION_RESULT
        self.data = {
            "board_name": board_name,
            "attribution_type": attribution_type,
            "reason_description": reason_description,
            "confidence": confidence,
            "related_news": related_news or []
        }
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }


class IntradayAlertMessage:
    """盘中快讯消息模型"""

    def __init__(
        self,
        alert_time: str,
        top_boards: List[Dict],
        core_reason: str,
        key_news: List[str] = None
    ):
        self.type = MessageType.INTRADAY_ALERT
        self.data = {
            "alert_time": alert_time,
            "top_boards": top_boards,
            "core_reason": core_reason,
            "key_news": key_news or []
        }
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }


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
        welcome_msg = {
            "type": MessageType.SYSTEM_NOTICE,
            "data": {
                "message": "已连接到智能股票板块异动分析系统",
                "connection_count": len(self.active_connections)
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        await websocket.send_json(welcome_msg)

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict):
        """广播消息给所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)

        # 移除断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_anomaly(self, anomaly_data: Dict):
        """广播异动通知"""
        message = AnomalyMessage(
            board_name=anomaly_data.get("board_name", ""),
            change_rate=anomaly_data.get("change_rate", 0),
            reason=anomaly_data.get("reason", ""),
            news_title=anomaly_data.get("news_title", ""),
            confidence=anomaly_data.get("confidence", 0),
            trigger_time=anomaly_data.get("trigger_time")
        )

        await self.broadcast(message.dict())
        logger.info(f"已广播异动通知: {anomaly_data.get('board_name', '')}")

    async def broadcast_attribution(self, attribution_data: Dict):
        """广播归因结果"""
        message = AttributionMessage(
            board_name=attribution_data.get("board_name", ""),
            attribution_type=attribution_data.get("attribution_type", ""),
            reason_description=attribution_data.get("reason_description", ""),
            confidence=attribution_data.get("confidence", 0),
            related_news=attribution_data.get("related_news", [])
        )

        await self.broadcast(message.dict())
        logger.info(f"已广播归因结果: {attribution_data.get('board_name', '')}")

    async def broadcast_intraday_alert(self, alert_data: Dict):
        """广播盘中快讯"""
        message = IntradayAlertMessage(
            alert_time=alert_data.get("alert_time", datetime.now().strftime("%H:%M")),
            top_boards=alert_data.get("top_boards", []),
            core_reason=alert_data.get("core_reason", ""),
            key_news=alert_data.get("key_news", [])
        )

        await self.broadcast(message.dict())
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
