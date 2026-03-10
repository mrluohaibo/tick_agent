#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 上涨归因Agent节点
匹配异动板块与新闻事件，分析上涨原因
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bz_agent.agents.llm import get_llm_by_type
from bz_agent.config import application_conf
from bz_agent.graph.types import State
from utils.logger_config import logger
from utils.db_tool_init import mongo_client, mysql_client
from utils.risk_filter import RiskFilter


class AttributionAgent:
    """归因分析Agent"""

    def __init__(self):
        self.collection_name = "attribution_result"
        self.news_collection = "news_events"
        self.mapping_collection = "news_sector_mapping"

        # 从配置读取归因参数
        self.time_match_window = int(application_conf.get_properties("attribution.time_match_window") or 30)

        # 归因类型映射
        self.attribution_types = application_conf.get_properties("attribution.attribution_types") or {
            "policy": "政策驱动",
            "fund": "资金抱团",
            "earnings": "业绩驱动",
            "topic": "题材发酵",
            "external": "外围传导",
        }

        # 置信度阈值
        conf_thresholds = application_conf.get_properties("attribution.confidence") or {}
        self.high_threshold = float(conf_thresholds.get("high_threshold", 0.8))
        self.medium_threshold = float(conf_thresholds.get("medium_threshold", 0.5))
        self.low_threshold = float(conf_thresholds.get("low_threshold", 0.4))

    def get_unprocessed_anomalies(self, limit: int = 50) -> List[Dict]:
        """
        获取未处理的异动记录

        :param limit: 数量限制
        :return: 异动记录列表
        """
        try:
            sql = """
                SELECT id, board_name, anomaly_time, change_rate, turnover_amount,
                       volume_ratio, net_inflow, limit_up_count, strength_score
                FROM board_anomaly
                WHERE is_processed = false
                ORDER BY anomaly_time DESC
                LIMIT %s
            """
            results = mysql_client.query(sql, (limit,))
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"获取未处理异动失败: {e}")
            return []

    def get_related_news(self, board_name: str, anomaly_time: datetime) -> List[Dict]:
        """
        获取与异动相关的新闻

        :param board_name: 板块名称
        :param anomaly_time: 异动时间
        :return: 相关新闻列表
        """
        try:
            # 计算时间窗口
            start_time = anomaly_time - timedelta(minutes=self.time_match_window)
            end_time = anomaly_time + timedelta(minutes=self.time_match_window)

            # 查询新闻-板块映射
            query = {
                "board_name": board_name,
                "create_time": {"$gte": start_time, "$lte": end_time}
            }

            mappings = list(mongo_client.find(self.mapping_collection, query, limit=20))

            # 获取新闻详情
            event_ids = [m["event_id"] for m in mappings]
            news_list = []
            if event_ids:
                news_query = {"event_id": {"$in": event_ids}}
                news_list = list(mongo_client.find(self.news_collection, news_query))

            return news_list

        except Exception as e:
            logger.error(f"获取相关新闻失败: {e}")
            return []

    def verify_fund_flow(self, board_name: str) -> bool:
        """
        验证板块资金流入情况

        :param board_name: 板块名称
        :return: 是否有正向资金流入
        """
        try:
            # 查询最近5分钟的资金流入
            cutoff_time = datetime.now() - timedelta(minutes=5)
            sql = """
                SELECT AVG(net_inflow) as avg_net_inflow
                FROM board_quote_realtime
                WHERE board_name = %s AND quote_time >= %s
            """
            result = mysql_client.query(sql, (board_name, cutoff_time))

            if result and result[0]['avg_net_inflow'] > 0:
                return True
            return False

        except Exception as e:
            logger.error(f"验证资金流入失败: {e}")
            return False

    def analyze_attribution(self, anomaly: Dict) -> Dict:
        """
        使用LLM分析归因

        :param anomaly: 异动数据
        :return: 归因分析结果
        """
        try:
            # 获取相关新闻
            anomaly_time = anomaly['anomaly_time']
            if isinstance(anomaly_time, str):
                anomaly_time = datetime.strptime(anomaly_time, '%Y-%m-%d %H:%M:%S')

            related_news = self.get_related_news(anomaly['board_name'], anomaly_time)

            # 验证资金流入
            has_fund_inflow = self.verify_fund_flow(anomaly['board_name'])

            # 构建分析Prompt
            system_prompt = """你是一个专业的股市归因分析师。请分析板块异动的原因。

任务：
1. 根据异动信息和相关新闻，确定板块上涨的主要原因
2. 判断归因类型：政策驱动/资金抱团/业绩驱动/题材发酵/外围传导
3. 评估归因的置信度（0-1之间的小数）

归因类型说明：
- 政策驱动：由政府政策、法规变化等宏观因素驱动
- 资金抱团：大资金集中流入某板块
- 业绩驱动：上市公司业绩超预期或重大事件
- 题材发酵：市场热点话题或概念炒作
- 外围传导：外围市场或国际形势传导

输出格式（必须是有效的JSON）：
{{
  "attribution_type": "policy/fund/earnings/topic/external",
  "reason_description": "详细说明归因理由",
  "confidence_score": 0.85,
  "related_news_ids": ["news_id1", "news_id2"],
  "reasoning": "分析思路说明"
}}
"""

            news_summary = ""
            if related_news:
                news_summary = "\n\n相关新闻：\n"
                for news in related_news[:5]:  # 最多显示5条
                    news_summary += f"- {news.get('news_title', '')} ({news.get('publish_time', '')})\n"

            user_prompt = f"""请分析以下板块异动：

板块名称: {anomaly['board_name']}
异动时间: {anomaly_time}
涨跌幅: {anomaly['change_rate']}%
成交额: {anomaly['turnover_amount']}
量比: {anomaly['volume_ratio']}
资金净流入: {anomaly['net_inflow']}
涨停家数: {anomaly['limit_up_count']}
强度评分: {anomaly['strength_score']}
资金流入验证: {'有正向资金流入' if has_fund_inflow else '无正向资金流入'}
{news_summary}

请按上述格式输出归因分析结果。"""

            # 调用LLM进行分析
            llm = get_llm_by_type("reasoning")  # 使用推理型LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = llm.invoke(messages)
            result_text = response.content.strip()

            # 提取JSON内容
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            # 添加相关新闻ID
            result['related_news_ids'] = [news.get('event_id') for news in related_news]

            # 根据规则调整置信度
            if not related_news:
                # 无匹配新闻，置信度较低
                result['confidence_score'] = min(result['confidence_score'], self.low_threshold)
                result['attribution_type'] = 'fund'  # 默认为资金抱团
            elif not has_fund_inflow:
                # 无资金流入支持，降低置信度
                result['confidence_score'] = min(result['confidence_score'], self.medium_threshold)

            return result

        except Exception as e:
            logger.error(f"LLM归因分析失败: {e}")
            # 返回默认归因
            return {
                "attribution_type": "fund",
                "reason_description": "分析失败，默认为资金短期炒作",
                "confidence_score": 0.3,
                "related_news_ids": [],
                "reasoning": str(e)
            }

    def calculate_confidence(self, attribution: Dict, anomaly: Dict, related_news: List[Dict]) -> float:
        """
        基于规则计算置信度

        :param attribution: LLM归因结果
        :param anomaly: 异动数据
        :param related_news: 相关新闻列表
        :return: 置信度 (0-1)
        """
        try:
            score = 0.5  # 基础分数

            # 1. 新闻匹配加分
            if related_news:
                score += 0.2
                if len(related_news) > 1:
                    score += 0.1  # 多条新闻指向同一板块

            # 2. 时间匹配加分
            if related_news:
                for news in related_news:
                    news_time = news.get('publish_time')
                    if isinstance(news_time, str):
                        news_time = datetime.strptime(news_time, '%Y-%m-%d %H:%M:%S')
                    if isinstance(news_time, datetime):
                        time_diff = abs((anomaly['anomaly_time'] - news_time).total_seconds())
                        if time_diff < 1800:  # 30分钟内
                            score += 0.1
                        elif time_diff < 3600:  # 1小时内
                            score += 0.05

            # 3. 资金流入加分
            if anomaly['net_inflow'] > 0:
                score += 0.1

            # 4. 强度评分加分
            score += anomaly['strength_score'] * 0.1

            # 限制在0-1之间
            return round(min(score, 1.0), 2)

        except Exception as e:
            logger.error(f"计算置信度失败: {e}")
            return 0.3

    def save_attribution(self, attribution: Dict, anomaly: Dict) -> bool:
        """
        保存归因结果

        :param attribution: 归因结果
        :param anomaly: 异动数据
        :return: 是否保存成功
        """
        try:
            # 生成归因ID
            attribution_id = f"attr_{int(time.time() * 1000)}_{hash(anomaly['board_name']) % 10000}"

            # 验证资金流入
            fund_verified = self.verify_fund_flow(anomaly['board_name'])

            # 插入MongoDB
            doc = {
                'attribution_id': attribution_id,
                'board_name': anomaly['board_name'],
                'anomaly_time': anomaly['anomaly_time'],
                'attribution_type': attribution.get('attribution_type', 'fund'),
                'reason_description': attribution.get('reason_description', ''),
                'related_news_ids': attribution.get('related_news_ids', []),
                'confidence_score': attribution.get('confidence_score', 0.5),
                'fund_verification': fund_verified,
                'create_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            mongo_client.insert_one(self.collection_name, doc)

            # 更新异动记录状态
            update_sql = """
                UPDATE board_anomaly
                SET is_processed = true, processed_time = %s
                WHERE id = %s
            """
            mysql_client.execute(update_sql, (time.strftime("%Y-%m-%d %H:%M:%S"), anomaly['id']))

            logger.info(f"保存归因结果: {attribution_id} - {attribution.get('reason_description', '')}")
            return True

        except Exception as e:
            logger.error(f"保存归因结果失败: {e}")
            return False

    def process_unprocessed_anomalies(self, limit: int = 20) -> int:
        """
        处理未处理的异动记录

        :param limit: 数量限制
        :return: 处理成功的数量
        """
        try:
            anomalies = self.get_unprocessed_anomalies(limit=limit)
            logger.info(f"找到 {len(anomalies)} 个未处理的异动")

            # 使用风险过滤器
            risk_filter = RiskFilter()

            processed = 0
            for anomaly in anomalies:
                try:
                    # 获取相关新闻
                    related_news = self.get_related_news(anomaly['board_name'], anomaly['anomaly_time'])

                    # LLM归因分析
                    attribution = self.analyze_attribution(anomaly)

                    # 基于规则计算置信度
                    confidence = self.calculate_confidence(attribution, anomaly, related_news)
                    attribution['confidence_score'] = confidence

                    # 风险过滤
                    attr_doc = {**attribution, 'confidence_score': confidence}
                    if not risk_filter.filter_attribution_by_confidence(attr_doc):
                        logger.info(f"归因置信度过低，跳过: {anomaly['board_name']}")
                        continue

                    # 保存归因
                    if self.save_attribution(attribution, anomaly):
                        processed += 1

                except Exception as e:
                    logger.error(f"处理异动失败: {e}")

            logger.info(f"成功处理 {processed} 个异动")
            return processed

        except Exception as e:
            logger.error(f"批量处理异动失败: {e}")
            return 0

    def get_attribution_results(self, board_name: str = None, hours: int = 24) -> List[Dict]:
        """
        获取归因结果

        :param board_name: 板块名称（可选）
        :param hours: 时间范围（小时）
        :return: 归因结果列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = {
                "create_time": {"$gte": cutoff_time}
            }

            if board_name:
                query['board_name'] = board_name

            results = list(mongo_client.find(self.collection_name, query, limit=100))
            return results

        except Exception as e:
            logger.error(f"获取归因结果失败: {e}")
            return []


def reason_agent_node(state: State) -> Command:
    """
    归因分析Agent节点
    基于LangGraph工作流

    :param state: 工作流状态
    :return: Command命令
    """
    logger.info("ReasonAgent 开始归因分析任务")

    agent = AttributionAgent()

    # 从state中获取任务参数
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else HumanMessage(content="")

    # 执行归因分析
    processed = agent.process_unprocessed_anomalies(limit=20)

    result = {
        "status": "success",
        "processed_count": processed,
        "message": f"完成了 {processed} 个异动的归因分析"
    }

    response_content = f"""<response>
{json.dumps(result, ensure_ascii=False, indent=2)}
</response>"""

    logger.info(f"ReasonAgent 完成: {result}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name="reason_agent"
                )
            ]
        },
        goto="supervisor"
    )


if __name__ == "__main__":
    # 测试主函数
    agent = AttributionAgent()

    # 处理未处理的异动
    processed = agent.process_unprocessed_anomalies(limit=5)
    print(f"处理了 {processed} 个异动")

    # 获取归因结果
    results = agent.get_attribution_results(hours=24)
    print(f"最近24小时的归因结果: {len(results)} 条")
