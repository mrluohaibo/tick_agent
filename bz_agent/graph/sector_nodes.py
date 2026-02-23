#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 板块监控Agent节点
实时监控板块行情，识别异动板块
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from bz_agent.config import application_conf
from bz_agent.graph.types import State
from utils.logger_config import logger
from utils.db_tool_init import mysql_client, redis_client
from utils.datetime_util import DateTimeUtil


class SectorMonitorAgent:
    """板块监控Agent"""

    def __init__(self):
        # 从配置文件读取异动阈值
        self.change_rate_threshold = float(application_conf.get_properties("anomaly.change_rate_threshold") or 2.0)
        self.turnover_threshold = float(application_conf.get_properties("anomaly.turnover_threshold") or 500000000)
        self.duration_threshold = int(application_conf.get_properties("anomaly.duration_threshold") or 2)
        self.volume_ratio_threshold = float(application_conf.get_properties("anomaly.volume_ratio_threshold") or 1.5)

        # 强度评分权重
        weights = application_conf.get_properties("anomaly.strength_score_weights") or {}
        self.change_rate_weight = float(weights.get("change_rate_weight", 0.4))
        self.turnover_weight = float(weights.get("turnover_weight", 0.3))
        self.limit_up_weight = float(weights.get("limit_up_weight", 0.3))

    def get_board_quote_history(self, board_name: str, days: int = 7) -> List[Dict]:
        """
        获取板块历史行情数据

        :param board_name: 板块名称
        :param days: 查询天数
        :return: 历史行情列表
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            sql = """
                SELECT quote_date, change_rate, turnover_amount, net_inflow, limit_up_count
                FROM board_quote_history
                WHERE board_name = %s AND quote_date >= %s
                ORDER BY quote_date DESC
            """
            results = mysql_client.query(sql, (board_name, cutoff_date.date()))
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"获取板块历史行情失败: {e}")
            return []

    def get_recent_quotes(self, board_name: str, minutes: int = 5) -> List[Dict]:
        """
        获取板块最近的实时行情

        :param board_name: 板块名称
        :param minutes: 查询分钟数
        :return: 最近行情列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            sql = """
                SELECT board_name, quote_time, change_rate, turnover_amount,
                       volume_ratio, net_inflow, limit_up_count, latest_price
                FROM board_quote_realtime
                WHERE board_name = %s AND quote_time >= %s
                ORDER BY quote_time DESC
            """
            results = mysql_client.query(sql, (board_name, cutoff_time))
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"获取板块最近行情失败: {e}")
            return []

    def check_anomaly_continuity(self, board_name: str) -> bool:
        """
        检查板块是否持续异动

        :param board_name: 板块名称
        :return: 是否持续异动
        """
        try:
            recent_quotes = self.get_recent_quotes(board_name, minutes=self.duration_threshold)

            if len(recent_quotes) < self.duration_threshold:
                return False

            # 检查是否连续满足异动条件
            continuous_count = 0
            for quote in recent_quotes:
                change_rate = quote.get('change_rate', 0)
                if change_rate >= self.change_rate_threshold:
                    continuous_count += 1
                else:
                    break

            return continuous_count >= self.duration_threshold

        except Exception as e:
            logger.error(f"检查异动持续性失败: {e}")
            return False

    def filter_noise(self, board_name: str, current_change_rate: float) -> bool:
        """
        过滤噪音，对比历史数据判断是否为随机波动

        :param board_name: 板块名称
        :param current_change_rate: 当前涨跌幅
        :return: 是否为有效异动（True=有效，False=噪音）
        """
        try:
            # 获取最近7天的历史数据
            history = self.get_board_quote_history(board_name, days=7)

            if not history:
                # 没有历史数据，认为有效
                return True

            # 计算历史平均涨跌幅
            avg_change_rate = sum(h.get('change_rate', 0) for h in history) / len(history)

            # 如果当前涨幅远高于历史平均值，可能是有意义的异动
            # 这里简化判断：当前涨幅 > 历史平均值 * 2
            if current_change_rate > abs(avg_change_rate) * 2:
                return True

            # 检查是否有资金流入支持
            recent_quotes = self.get_recent_quotes(board_name, minutes=5)
            if recent_quotes:
                avg_net_inflow = sum(q.get('net_inflow', 0) for q in recent_quotes) / len(recent_quotes)
                if avg_net_inflow > 0:
                    # 有资金流入支持，认为有效
                    return True

            # 否则认为是噪音
            return False

        except Exception as e:
            logger.error(f"过滤噪音失败: {e}")
            return True  # 出错时保守处理，认为是有效异动

    def calculate_strength_score(self, quote: Dict, history: List[Dict]) -> float:
        """
        计算异动强度评分

        :param quote: 当前行情
        :param history: 历史行情
        :return: 强度评分 (0-1)
        """
        try:
            # 1. 涨幅评分 (归一化到0-1)
            # 假设涨停为10%，则change_rate/10得到比例
            change_rate = quote.get('change_rate', 0)
            change_score = min(abs(change_rate) / 10.0, 1.0)

            # 2. 成交额评分 (归一化到0-1)
            # 假设100亿为最大成交额
            turnover = quote.get('turnover_amount', 0)
            turnover_score = min(turnover / 10000000000, 1.0)

            # 3. 涨停家数评分 (归一化到0-1)
            # 假设涨停20家为最大值
            limit_up_count = quote.get('limit_up_count', 0)
            limit_up_score = min(limit_up_count / 20.0, 1.0)

            # 综合评分
            strength_score = (
                change_score * self.change_rate_weight +
                turnover_score * self.turnover_weight +
                limit_up_score * self.limit_up_weight
            )

            return round(strength_score, 2)

        except Exception as e:
            logger.error(f"计算强度评分失败: {e}")
            return 0.0

    def is_new_anomaly(self, board_name: str) -> bool:
        """
        判断是否为新异动

        :param board_name: 板块名称
        :return: 是否为新异动
        """
        try:
            # 查询最近1小时的异动记录
            cutoff_time = datetime.now() - timedelta(hours=1)
            sql = """
                SELECT COUNT(*) as count
                FROM board_anomaly
                WHERE board_name = %s AND anomaly_time >= %s
            """
            result = mysql_client.query(sql, (board_name, cutoff_time))
            if result and result[0]['count'] > 0:
                return False
            return True
        except Exception as e:
            logger.error(f"判断新异动失败: {e}")
            return True

    def detect_anomalies(self) -> List[Dict]:
        """
        检测异动板块

        :return: 异动板块列表
        """
        try:
            # 获取最近5分钟的实时行情
            cutoff_time = datetime.now() - timedelta(minutes=5)
            sql = """
                SELECT board_name, quote_time, change_rate, turnover_amount,
                       volume_ratio, net_inflow, limit_up_count, latest_price
                FROM board_quote_realtime
                WHERE quote_time >= %s
                ORDER BY change_rate DESC
            """
            results = mysql_client.query(sql, (cutoff_time,))
            quotes = [dict(row) for row in results] if results else []

            anomalies = []

            for quote in quotes:
                board_name = quote.get('board_name')
                change_rate = quote.get('change_rate', 0)
                turnover = quote.get('turnover_amount', 0)
                volume_ratio = quote.get('volume_ratio', 0)

                # 判断是否满足异动条件
                if (change_rate >= self.change_rate_threshold and
                    turnover >= self.turnover_threshold and
                    volume_ratio >= self.volume_ratio_threshold):

                    # 检查持续性
                    if not self.check_anomaly_continuity(board_name):
                        continue

                    # 过滤噪音
                    if not self.filter_noise(board_name, change_rate):
                        continue

                    # 获取历史数据
                    history = self.get_board_quote_history(board_name, days=7)

                    # 计算强度评分
                    strength_score = self.calculate_strength_score(quote, history)

                    # 判断是否为新异动
                    is_new = self.is_new_anomaly(board_name)

                    anomaly = {
                        'board_name': board_name,
                        'anomaly_time': quote.get('quote_time'),
                        'change_rate': change_rate,
                        'turnover_amount': turnover,
                        'volume_ratio': volume_ratio,
                        'net_inflow': quote.get('net_inflow', 0),
                        'limit_up_count': quote.get('limit_up_count', 0),
                        'latest_price': quote.get('latest_price', 0),
                        'strength_score': strength_score,
                        'is_new_anomaly': is_new,
                    }

                    anomalies.append(anomaly)

                    # 保存到MySQL
                    self.save_anomaly(anomaly)

            logger.info(f"检测到 {len(anomalies)} 个异动板块")
            return anomalies

        except Exception as e:
            logger.error(f"检测异动失败: {e}")
            return []

    def save_anomaly(self, anomaly: Dict) -> bool:
        """
        保存异动记录到MySQL

        :param anomaly: 异动数据
        :return: 是否保存成功
        """
        try:
            sql = """
                INSERT INTO board_anomaly
                (board_name, anomaly_time, change_rate, turnover_amount,
                 volume_ratio, net_inflow, limit_up_count, strength_score, is_new_anomaly, is_processed, create_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                anomaly['board_name'],
                anomaly['anomaly_time'],
                anomaly['change_rate'],
                anomaly['turnover_amount'],
                anomaly['volume_ratio'],
                anomaly['net_inflow'],
                anomaly['limit_up_count'],
                anomaly['strength_score'],
                anomaly['is_new_anomaly'],
                False,  # is_processed
                DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss(),
            )

            mysql_client.execute(sql, values)

            # 缓存到Redis
            date_str = anomaly['anomaly_time'].strftime('%Y-%m-%d')
            redis_key = f"board:anomaly:{anomaly['board_name']}:{date_str}"
            redis_hash = {
                "anomaly_time": str(anomaly['anomaly_time']),
                "change_rate": str(anomaly['change_rate']),
                "strength_score": str(anomaly['strength_score']),
                "is_processed": "false",
            }
            redis_client.client.hset(redis_key, mapping=redis_hash)
            redis_client.client.expire(redis_key, 86400)  # 24小时

            return True

        except Exception as e:
            logger.error(f"保存异动记录失败: {e}")
            return False

    def get_anomaly_list(self, limit: int = 20) -> List[Dict]:
        """
        获取异动板块列表

        :param limit: 返回数量
        :return: 异动板块列表
        """
        try:
            sql = """
                SELECT board_name, anomaly_time, change_rate, turnover_amount,
                       strength_score, is_new_anomaly
                FROM board_anomaly
                WHERE is_processed = false
                ORDER BY strength_score DESC, anomaly_time DESC
                LIMIT %s
            """
            results = mysql_client.query(sql, (limit,))
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"获取异动列表失败: {e}")
            return []


def sector_agent_node(state: State) -> Command:
    """
    板块监控Agent节点
    基于LangGraph工作流

    :param state: 工作流状态
    :return: Command命令
    """
    logger.info("SectorAgent 开始板块监控任务")

    agent = SectorMonitorAgent()

    # 从state中获取任务参数
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else HumanMessage(content="")

    # 执行异动检测
    anomalies = agent.detect_anomalies()

    result = {
        "status": "success",
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "message": f"检测到 {len(anomalies)} 个异动板块"
    }

    response_content = f"""<response>
{json.dumps(result, ensure_ascii=False, indent=2)}
</response>"""

    logger.info(f"SectorAgent 完成: {result}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name="sector_agent"
                )
            ]
        },
        goto="supervisor"
    )


if __name__ == "__main__":
    # 测试主函数
    agent = SectorMonitorAgent()

    # 检测异动
    anomalies = agent.detect_anomalies()
    print(f"检测到 {len(anomalies)} 个异动板块:")
    for a in anomalies[:5]:
        print(f"  - {a['board_name']}: {a['change_rate']}% (强度: {a['strength_score']})")
