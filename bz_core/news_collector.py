#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 财经新闻采集模块
定时拉取东方财富财经新闻，存储到MongoDB
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import my_akshare as ak
import pandas as pd

from utils.config_init import application_conf
from utils.logger_config import logger
from utils.db_tool_init import mongo_client
from utils.datetime_util import DateTimeUtil
from utils.StringUtil import StringUtil


class NewsCollector:
    """财经新闻采集器"""

    def __init__(self):
        self.collection_name = "news_events"
        self.retry_times = 3
        self.retry_interval = 10  # seconds

    def collect_news_em(self) -> pd.DataFrame:
        """
        从东方财富采集财经新闻
        使用 stock_news_em 获取财经新闻

        :return: 新闻数据DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                logger.info(f"第 {attempt + 1} 次尝试采集东方财富新闻...")
                # 采集东方财富财经新闻
                news_df = ak.stock.news.news_stock_em()
                if news_df is not None and not news_df.empty:
                    logger.info(f"成功采集到 {len(news_df)} 条新闻")
                    return news_df
                else:
                    logger.warning("东方财富新闻数据为空")
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"采集东方财富新闻失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    logger.error("超过最大重试次数，放弃采集")
                    return pd.DataFrame()

    def collect_policy_news(self) -> pd.DataFrame:
        """
        从东方财富采集政策新闻
        使用 policy 相关接口

        :return: 政策新闻数据DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                logger.info(f"第 {attempt + 1} 次尝试采集政策新闻...")
                # 这里需要根据实际的akshare接口调整
                # news_df = ak.stock.news.news_policy_em()
                logger.info("政策新闻采集功能待实现具体接口")
                return pd.DataFrame()
            except Exception as e:
                logger.error(f"采集政策新闻失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    return pd.DataFrame()

    def process_news_data(self, news_df: pd.DataFrame) -> List[Dict]:
        """
        处理新闻数据，转换为MongoDB文档格式

        :param news_df: 原始新闻DataFrame
        :return: 处理后的新闻文档列表
        """
        if news_df.empty:
            return []

        documents = []
        current_time = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()

        for _, row in news_df.iterrows():
            try:
                # 生成事件ID
                event_id = f"evt_{int(time.time() * 1000)}_{hash(row.get('新闻标题', '')) % 10000}"

                # 判断新闻类型（简化版，后续由Agent分析）
                news_title = row.get('新闻标题', '')
                news_content = row.get('新闻内容', '')
                publish_time_str = row.get('发布时间', current_time)

                # 解析发布时间
                publish_time = self._parse_publish_time(publish_time_str)

                document = {
                    'event_id': event_id,
                    'news_title': news_title,
                    'news_content': news_content,
                    'news_url': row.get('新闻链接', ''),
                    'event_type': 'market',  # 默认类型，后续由Agent分析
                    'related_sectors': [],  # 初始为空，后续由Agent分析填充
                    'sentiment': 'neutral',  # 默认中性，后续由Agent分析
                    'sentiment_score': 0.5,
                    'publish_time': publish_time,
                    'source': '东方财富',
                    'create_time': current_time,
                    'update_time': current_time,
                }

                documents.append(document)
            except Exception as e:
                logger.warning(f"处理新闻数据失败: {e}")
                continue

        logger.info(f"成功处理 {len(documents)} 条新闻")
        return documents

    def _parse_publish_time(self, time_str: str) -> datetime:
        """
        解析发布时间字符串

        :param time_str: 时间字符串
        :return: datetime对象
        """
        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d',
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue

            # 如果都解析失败，返回当前时间
            logger.warning(f"无法解析时间格式: {time_str}，使用当前时间")
            return datetime.now()
        except Exception as e:
            logger.warning(f"解析时间失败: {e}")
            return datetime.now()

    def save_news_to_mongo(self, documents: List[Dict]) -> int:
        """
        保存新闻到MongoDB

        :param documents: 新闻文档列表
        :return: 插入/更新的数量
        """
        if not documents:
            logger.warning("没有新闻数据需要保存")
            return 0

        count = 0
        for doc in documents:
            try:
                # 使用新闻标题和发布时间作为去重条件
                query = {
                    'news_title': doc['news_title'],
                    'publish_time': doc['publish_time'],
                }

                # 检查是否已存在
                existing = mongo_client.find_one(self.collection_name, query)
                if existing:
                    logger.debug(f"新闻已存在: {doc['news_title']}")
                    continue

                # 插入新新闻
                mongo_client.insert_one(self.collection_name, doc)
                count += 1
            except Exception as e:
                logger.error(f"保存新闻到MongoDB失败: {e}")

        logger.info(f"成功保存 {count} 条新闻到MongoDB")
        return count

    def collect_and_save_news(self) -> Dict[str, int]:
        """
        采集并保存新闻的主方法

        :return: 采集结果统计
        """
        result = {
            'em_news_count': 0,
            'policy_news_count': 0,
            'total_saved': 0,
        }

        # 采集东方财富新闻
        em_news_df = self.collect_news_em()
        if not em_news_df.empty:
            em_docs = self.process_news_data(em_news_df)
            result['em_news_count'] = len(em_docs)
            result['total_saved'] += self.save_news_to_mongo(em_docs)

        # 采集政策新闻
        policy_news_df = self.collect_policy_news()
        if not policy_news_df.empty:
            policy_docs = self.process_news_data(policy_news_df)
            result['policy_news_count'] = len(policy_docs)
            result['total_saved'] += self.save_news_to_mongo(policy_docs)

        logger.info(f"新闻采集完成: {result}")
        return result

    def clean_old_news(self, days: int = 30):
        """
        清理旧新闻数据

        :param days: 保留天数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = {
                'publish_time': {'$lt': cutoff_date}
            }

            # 获取旧新闻数量
            old_news_count = mongo_client.find(self.collection_name, query, limit=0)
            if old_news_count:
                # MongoDB的find返回的是迭代器，需要转换
                count = len(list(mongo_client.find(self.collection_name, query, limit=1000000)))
                logger.info(f"发现 {count} 条超过 {days} 天的旧新闻")

                # 删除旧新闻（注意：这里简化处理，实际应该使用delete_many）
                # mongo_client.delete_many(self.collection_name, query)
                logger.info("旧新闻清理功能待实现delete_many方法")

        except Exception as e:
            logger.error(f"清理旧新闻失败: {e}")


def main():
    """测试主函数"""
    collector = NewsCollector()

    # 采集并保存新闻
    result = collector.collect_and_save_news()
    print(f"采集结果: {result}")


if __name__ == "__main__":
    main()
