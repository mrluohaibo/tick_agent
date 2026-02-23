#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 报告生成Agent节点
生成盘中快讯和盘后复盘报告
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from bz_agent.agents.llm import get_llm_by_type
from bz_agent.graph.types import State
from utils.logger_config import logger
from utils.db_tool_init import mongo_client, mysql_client
from utils.datetime_util import DateTimeUtil


class ReportAgent:
    """报告生成Agent"""

    def __init__(self):
        self.attribution_collection = "attribution_result"
        self.news_collection = "news_events"

    def get_top_boards(self, limit: int = 5) -> List[Dict]:
        """
        获取领涨板块列表

        :param limit: 返回数量
        :return: 板块列表
        """
        try:
            sql = """
                SELECT board_name, change_rate, turnover_amount, limit_up_count
                FROM board_quote_realtime
                WHERE quote_time >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                ORDER BY change_rate DESC
                LIMIT %s
            """
            results = mysql_client.query(sql, (limit,))
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"获取领涨板块失败: {e}")
            return []

    def get_anomaly_attributions(self, hours: int = 1) -> List[Dict]:
        """
        获取异动归因结果

        :param hours: 时间范围（小时）
        :return: 归因结果列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            query = {
                "create_time": {"$gte": cutoff_time},
            }

            results = list(mongo_client.find(self.attribution_collection, query, limit=20))
            # 按置信度排序
            results.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
            return results
        except Exception as e:
            logger.error(f"获取归因结果失败: {e}")
            return []

    def generate_intraday_alert(self) -> str:
        """
        生成盘中快讯

        :return: 盘中快讯文本
        """
        try:
            # 获取当前时间
            now = datetime.now()
            time_str = now.strftime("%H:%M")

            # 获取领涨板块
            top_boards = self.get_top_boards(limit=3)

            # 获取异动归因
            attributions = self.get_anomaly_attributions(hours=1)

            # 构建快讯内容
            alert_lines = [
                f"【{time_str} 盘中快讯】",
                "",
                "📈 领涨板块TOP3:",
            ]

            for i, board in enumerate(top_boards, 1):
                board_name = board.get('board_name', '未知')
                change_rate = board.get('change_rate', 0)
                turnover = board.get('turnover_amount', 0)
                turnover_str = f"{turnover / 100000000:.2f}亿" if turnover > 0 else "0亿"
                alert_lines.append(f"  {i}. {board_name} +{change_rate:.2f}% (成交额: {turnover_str})")

            if attributions:
                alert_lines.append("")
                alert_lines.append("📝 核心上涨原因:")

                # 统计归因类型
                type_count = {}
                for attr in attributions[:5]:
                    attr_type = attr.get('attribution_type', '')
                    type_name = self._get_attribution_type_name(attr_type)
                    type_count[type_name] = type_count.get(type_name, 0) + 1

                # 找出最主要的归因类型
                if type_count:
                    main_type = max(type_count, key=type_count.get)
                    alert_lines.append(f"{main_type}")

                    # 显示相关新闻
                    alert_lines.append("")
                    alert_lines.append("🔑 关键催化新闻:")
                    for attr in attributions[:3]:
                        news_ids = attr.get('related_news_ids', [])
                        if news_ids:
                            news_id = news_ids[0]
                            news = mongo_client.find_one(self.news_collection, {"event_id": news_id})
                            if news:
                                alert_lines.append(f"  - {news.get('news_title', '')}")

            return "\n".join(alert_lines)

        except Exception as e:
            logger.error(f"生成盘中快讯失败: {e}")
            return f"【盘中快讯生成失败: {str(e)}】"

    def generate_post_market_report(self) -> Dict:
        """
        生成盘后复盘报告

        :return: 报告数据
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # 获取当日行情数据
            sql = """
                SELECT board_name, change_rate, turnover_amount, net_inflow, limit_up_count
                FROM board_quote_history
                WHERE quote_date = %s
                ORDER BY change_rate DESC
                LIMIT 20
            """
            results = mysql_client.query(sql, (today,))

            # 分类板块
            up_boards = [r for r in results if r['change_rate'] > 0]
            down_boards = [r for r in results if r['change_rate'] < 0]

            # 获取归因结果
            attributions = self.get_anomaly_attributions(hours=24)

            # 使用LLM生成报告
            report = self._generate_report_with_llm(today, up_boards, down_boards, attributions)

            return {
                "date": today,
                "report_content": report,
                "up_boards_count": len(up_boards),
                "down_boards_count": len(down_boards),
                "attribution_count": len(attributions),
            }

        except Exception as e:
            logger.error(f"生成盘后报告失败: {e}")
            return {"date": today, "report_content": f"报告生成失败: {str(e)}"}

    def _generate_report_with_llm(self, date: str, up_boards: List[Dict],
                                 down_boards: List[Dict], attributions: List[Dict]) -> str:
        """
        使用LLM生成报告

        :param date: 日期
        :param up_boards: 上涨板块
        :param down_boards: 下跌板块
        :param attributions: 归因结果
        :return: 报告文本
        """
        try:
            system_prompt = """你是一个专业的股市分析员。请根据提供的数据生成盘后复盘报告。

报告结构：
1. 市场概况：总结当日整体行情
2. 领涨板块：列出涨幅最大的板块
3. 领跌板块：列出跌幅最大的板块
4. 核心驱动：分析上涨的主要驱动因素
5. 归因统计：按归因类型统计

要求：
- 语言简洁专业，避免过多术语
- 重点突出核心信息
- 对关键数据进行适当解读"""

            # 准备数据摘要
            up_summary = "\n".join([
                f"{i+1}. {b['board_name']}: +{b['change_rate']:.2f}% (成交额: {b['turnover_amount']/100000000:.2f}亿)"
                for i, b in enumerate(up_boards[:5])
            ])

            down_summary = "\n".join([
                f"{i+1}. {d['board_name']}: {d['change_rate']:.2f}%"
                for i, d in enumerate(down_boards[:5])
            ])

            # 归因类型统计
            attr_type_count = {}
            for attr in attributions:
                attr_type = attr.get('attribution_type', '')
                type_name = self._get_attribution_type_name(attr_type)
                attr_type_count[type_name] = attr_type_count.get(type_name, 0) + 1

            attr_summary = "\n".join([
                f"- {type_name}: {count} 次"
                for type_name, count in attr_type_count.items()
            ])

            user_prompt = f"""请生成{date}的盘后复盘报告：

市场数据：
- 上涨板块数: {len(up_boards)}
- 下跌板块数: {len(down_boards)}

领涨板块TOP5:
{up_summary}

领跌板块TOP5:
{down_summary}

归因统计:
{attr_summary}

请按上述结构生成专业简洁的复盘报告。"""

            # 调用LLM生成报告
            llm = get_llm_by_type("basic")
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = llm.invoke(messages)
            return response.content.strip()

        except Exception as e:
            logger.error(f"LLM生成报告失败: {e}")
            # 返回简化版报告
            return f"{date} 盘后复盘\n\n生成失败，请查看原始数据。"

    def _get_attribution_type_name(self, attr_type: str) -> str:
        """
        获取归因类型中文名称

        :param attr_type: 归因类型代码
        :return: 中文名称
        """
        type_names = {
            "policy": "政策驱动",
            "fund": "资金抱团",
            "earnings": "业绩驱动",
            "topic": "题材发酵",
            "external": "外围传导",
        }
        return type_names.get(attr_type, attr_type)

    def save_report(self, report_data: Dict) -> Optional[str]:
        """
        保存报告到文件

        :param report_data: 报告数据
        :return: 文件路径
        """
        try:
            from bz_core import Constant
            import os

            date_str = report_data['date']
            report_dir = os.path.join(Constant.root_path, "reports")
            os.makedirs(report_dir, exist_ok=True)

            # 保存为文本文件
            txt_path = os.path.join(report_dir, f"report_{date_str}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(report_data['report_content'])

            logger.info(f"报告已保存: {txt_path}")
            return txt_path

        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            return None


def report_agent_node(state: State) -> Command:
    """
    报告生成Agent节点
    基于LangGraph工作流

    :param state: 工作流状态
    :return: Command命令
    """
    logger.info("ReportAgent 开始生成报告任务")

    agent = ReportAgent()

    # 从state中获取任务参数
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else HumanMessage(content="")

    # 解析任务类型
    task = last_message.content
    report_type = None

    if "盘中" in task or "intraday" in task.lower():
        report_type = "intraday"
    elif "盘后" in task or "post" in task.lower():
        report_type = "post_market"

    # 执行报告生成
    result = {}

    if report_type == "intraday":
        alert = agent.generate_intraday_alert()
        result = {
            "status": "success",
            "report_type": "intraday_alert",
            "content": alert,
            "message": "盘中快讯生成成功"
        }
    elif report_type == "post_market":
        report_data = agent.generate_post_market_report()
        file_path = agent.save_report(report_data)
        result = {
            "status": "success",
            "report_type": "post_market_report",
            "content": report_data.get('report_content', ''),
            "file_path": file_path,
            "message": "盘后报告生成成功"
        }
    else:
        result = {
            "status": "error",
            "message": "无法识别报告类型，请指定 盘中 或 盘后"
        }

    response_content = f"""<response>
{json.dumps(result, ensure_ascii=False, indent=2)}
</response>"""

    logger.info(f"ReportAgent 完成: {result}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name="report_agent"
                )
            ]
        },
        goto="supervisor"
    )


if __name__ == "__main__":
    # 测试主函数
    agent = ReportAgent()

    # 生成盘中快讯
    print("=" * 50)
    print("盘中快讯:")
    print(agent.generate_intraday_alert())

    # 生成盘后报告
    print("\n" + "=" * 50)
    print("盘后报告:")
    report_data = agent.generate_post_market_report()
    print(report_data.get('report_content', ''))
