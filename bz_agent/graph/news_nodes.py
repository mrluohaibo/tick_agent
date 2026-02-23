#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 新闻解析Agent节点
将非结构化新闻转化为机器可识别的结构化事件
"""

import json
import time
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from bz_agent.agents.llm import get_llm_by_type
from bz_agent.graph.types import State
from utils.logger_config import logger
from utils.db_tool_init import mongo_client, mysql_client


class NewsAnalysisAgent:
    """新闻分析Agent"""

    def __init__(self):
        self.collection_name = "news_events"
        self.mapping_collection_name = "news_sector_mapping"

    def get_all_boards(self) -> List[str]:
        """
        获取所有板块名称列表

        :return: 板块名称列表
        """
        try:
            sql = "SELECT board_name FROM board_basic"
            results = mysql_client.query(sql)
            if results:
                return [row['board_name'] for row in results]
            return []
        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return []

    def analyze_news(self, news_data: Dict) -> Dict:
        """
        分析单条新闻

        :param news_data: 新闻数据
        :return: 分析结果
        """
        # 获取所有板块名称
        boards = self.get_all_boards()
        boards_str = ", ".join(boards[:100])  # 限制前100个板块

        # 构建分析Prompt
        system_prompt = """你是一个专业的财经新闻分析师。请分析给定的新闻，提取关键信息。

任务：
1. 确定新闻的事件类型（政策/业绩/题材/市场）
2. 判断新闻的情绪（利好/利空/中性）
3. 评估情绪强度（0-1之间的小数，越接近1影响越大）
4. 匹配相关的板块名称（从提供的板块列表中选择）

可用板块列表：
{boards}

输出格式（必须是有效的JSON）：
{{
  "event_type": "政策/业绩/题材/市场",
  "sentiment": "positive/negative/neutral",
  "sentiment_score": 0.85,
  "related_sectors": ["板块1", "板块2"],
  "reasoning": "简要说明分析理由"
}}
""".format(boards=boards_str)

        user_prompt = f"""请分析以下新闻：

标题: {news_data.get('news_title', '')}
内容: {news_data.get('news_content', '')}
来源: {news_data.get('source', '')}
发布时间: {news_data.get('publish_time', '')}

请按上述格式输出分析结果。"""

        try:
            # 调用LLM进行分析
            llm = get_llm_by_type("basic")
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
            return result

        except Exception as e:
            logger.error(f"分析新闻失败: {e}")
            # 返回默认分析结果
            return {
                "event_type": "market",
                "sentiment": "neutral",
                "sentiment_score": 0.5,
                "related_sectors": [],
                "reasoning": "分析失败，使用默认值"
            }

    def process_unanalyzed_news(self, limit: int = 50) -> int:
        """
        处理未分析的新闻

        :param limit: 处理数量限制
        :return: 处理成功的数量
        """
        try:
            # 查询未分析的新闻（没有related_sectors字段的）
            query = {
                "related_sectors": {"$exists": False},
            }

            news_list = list(mongo_client.find(self.collection_name, query, limit=limit))
            logger.info(f"找到 {len(news_list)} 条未分析的新闻")

            processed = 0
            for news in news_list:
                try:
                    # 分析新闻
                    analysis = self.analyze_news(news)

                    # 更新新闻
                    update = {
                        "event_type": analysis.get("event_type", "market"),
                        "sentiment": analysis.get("sentiment", "neutral"),
                        "sentiment_score": analysis.get("sentiment_score", 0.5),
                        "related_sectors": analysis.get("related_sectors", []),
                        "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }

                    query = {"event_id": news.get("event_id")}
                    mongo_client.update_one(self.collection_name, query, update={"$set": update})

                    # 保存新闻-板块映射
                    for sector in analysis.get("related_sectors", []):
                        mapping = {
                            "event_id": news.get("event_id"),
                            "board_name": sector,
                            "match_score": 0.8,  # 默认匹配分数
                            "match_keywords": [],  # 可以进一步提取匹配关键词
                            "create_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        mongo_client.insert_one(self.mapping_collection_name, mapping)

                    processed += 1
                    logger.debug(f"处理新闻: {news.get('news_title', '')}")

                except Exception as e:
                    logger.error(f"处理新闻失败: {e}")

            logger.info(f"成功分析 {processed} 条新闻")
            return processed

        except Exception as e:
            logger.error(f"批量分析新闻失败: {e}")
            return 0

    def analyze_news_by_id(self, event_id: str) -> Dict:
        """
        根据ID分析指定新闻

        :param event_id: 事件ID
        :return: 分析结果
        """
        try:
            query = {"event_id": event_id}
            news = mongo_client.find_one(self.collection_name, query)
            if not news:
                return {"error": "新闻不存在"}

            analysis = self.analyze_news(news)

            # 更新新闻
            update = {
                "event_type": analysis.get("event_type", "market"),
                "sentiment": analysis.get("sentiment", "neutral"),
                "sentiment_score": analysis.get("sentiment_score", 0.5),
                "related_sectors": analysis.get("related_sectors", []),
                "update_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            mongo_client.update_one(self.collection_name, query, update={"$set": update})

            return {
                "event_id": event_id,
                "analysis": analysis,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"分析指定新闻失败: {e}")
            return {"error": str(e), "event_id": event_id}


def news_agent_node(state: State) -> Command:
    """
    新闻解析Agent节点
    基于LangGraph工作流

    :param state: 工作流状态
    :return: Command命令
    """
    logger.info("NewsAgent 开始处理新闻解析任务")

    agent = NewsAnalysisAgent()

    # 从state中获取任务参数
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else HumanMessage(content="")

    # 解析任务参数
    task = last_message.content
    event_id = None
    batch = False

    # 检查是否为批量处理
    if "批量" in task or "batch" in task.lower():
        batch = True
    elif "event_id" in task or "事件ID" in task:
        # 尝试提取事件ID
        import re
        match = re.search(r'event_id["\s:=\s"](\S+)', task)
        if match:
            event_id = match.group(1)

    # 执行分析
    result = {}
    if batch:
        processed = agent.process_unanalyzed_news(limit=50)
        result = {
            "status": "success",
            "processed_count": processed,
            "message": f"批量分析了 {processed} 条新闻"
        }
    elif event_id:
        result = agent.analyze_news_by_id(event_id)
    else:
        result = {
            "status": "error",
            "message": "无法识别任务参数，请指定 event_id 或使用批量处理"
        }

    response_content = f"""<response>
{json.dumps(result, ensure_ascii=False, indent=2)}
</response>"""

    logger.info(f"NewsAgent 完成: {result}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name="news_agent"
                )
            ]
        },
        goto="supervisor"
    )


if __name__ == "__main__":
    # 测试主函数
    agent = NewsAnalysisAgent()

    # 获取板块列表
    boards = agent.get_all_boards()
    print(f"板块列表: {len(boards)} 个")

    # 分析未处理的新闻
    processed = agent.process_unanalyzed_news(limit=5)
    print(f"处理了 {processed} 条新闻")
