#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 风险过滤模块
过滤无效/错误数据，避免错误归因
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.config_init import application_conf
from utils.logger_config import logger
from utils.db_tool_init import mongo_client


class RiskFilter:
    """风险过滤器"""

    def __init__(self):
        # 可信新闻来源白名单
        self.trusted_sources = application_conf.get_properties("risk.news.required_sources") or [
            "东方财富",
            "巨潮资讯",
            "证券时报",
            "中国证券报",
            "上海证券报",
            "证券日报",
            "新华网",
            "人民网",
        ]

        # 最大新闻时效（小时）
        self.max_news_age = int(application_conf.get_properties("risk.news.max_age_hours") or 24)

        # 最低置信度阈值
        self.min_confidence = float(application_conf.get_properties("risk.attribution.min_confidence") or 0.4)

        # 必填字段列表
        self.required_fields = application_conf.get_properties("risk.data.required_fields") or [
            "board_name",
            "quote_time",
            "change_rate",
            "turnover_amount",
        ]

    def filter_news_by_age(self, news: Dict) -> bool:
        """
        过滤超时的新闻

        :param news: 新闻数据
        :return: 是否有效
        """
        try:
            publish_time = news.get('publish_time')
            if not publish_time:
                logger.warning("新闻缺少发布时间，过滤")
                return False

            # 如果publish_time是字符串，解析为datetime
            if isinstance(publish_time, str):
                try:
                    publish_time = datetime.fromisoformat(publish_time.replace('T', ' '))
                except ValueError:
                    try:
                        publish_time = datetime.strptime(publish_time, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        logger.warning(f"无法解析新闻发布时间: {publish_time}")
                        return False

            # 检查新闻时效
            if isinstance(publish_time, datetime):
                age = datetime.now() - publish_time
                if age.total_seconds() > self.max_news_age * 3600:
                    logger.debug(f"新闻超过时效限制 ({age.total_seconds()/3600:.1f}小时)，过滤")
                    return False

            return True
        except Exception as e:
            logger.error(f"过滤新闻时效失败: {e}")
            return False

    def filter_news_by_source(self, news: Dict) -> bool:
        """
        过滤不可信来源的新闻

        :param news: 新闻数据
        :return: 是否有效
        """
        try:
            source = news.get('source', '')
            if not source:
                logger.warning("新闻缺少来源信息，过滤")
                return False

            # 检查来源是否在白名单中
            for trusted_source in self.trusted_sources:
                if trusted_source in source:
                    return True

            logger.debug(f"新闻来源不在白名单: {source}，过滤")
            return False
        except Exception as e:
            logger.error(f"过滤新闻来源失败: {e}")
            return False

    def filter_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        过滤新闻列表

        :param news_list: 新闻列表
        :return: 过滤后的新闻列表
        """
        if not news_list:
            return []

        filtered = []
        for news in news_list:
            # 过滤时效
            if not self.filter_news_by_age(news):
                continue

            # 过滤来源
            if not self.filter_news_by_source(news):
                continue

            filtered.append(news)

        if len(filtered) != len(news_list):
            logger.info(f"新闻过滤: {len(news_list)} -> {len(filtered)}")

        return filtered

    def validate_quote_data(self, quote: Dict) -> bool:
        """
        验证行情数据完整性

        :param quote: 行情数据
        :return: 是否有效
        """
        try:
            # 检查必填字段
            for field in self.required_fields:
                if field not in quote or quote[field] is None:
                    logger.debug(f"行情数据缺少必填字段: {field}，过滤")
                    return False

            # 检查数值字段的有效性
            numeric_fields = ['change_rate', 'turnover_amount', 'volume_ratio']
            for field in numeric_fields:
                if field in quote:
                    try:
                        float(quote[field])
                    except (ValueError, TypeError):
                        logger.debug(f"行情数据字段 {field} 数值无效: {quote[field]}，过滤")
                        return False

            return True
        except Exception as e:
            logger.error(f"验证行情数据失败: {e}")
            return False

    def validate_quote_list(self, quote_list: List[Dict]) -> List[Dict]:
        """
        验证行情数据列表

        :param quote_list: 行情数据列表
        :return: 验证后的行情数据列表
        """
        if not quote_list:
            return []

        validated = []
        for quote in quote_list:
            if self.validate_quote_data(quote):
                validated.append(quote)

        if len(validated) != len(quote_list):
            logger.info(f"行情数据验证: {len(quote_list)} -> {len(validated)}")

        return validated

    def filter_attribution_by_confidence(self, attribution: Dict) -> bool:
        """
        过滤低置信度的归因结果

        :param attribution: 归因结果
        :return: 是否有效
        """
        try:
            confidence = attribution.get('confidence_score', 0)
            if confidence < self.min_confidence:
                logger.debug(f"归因结果置信度过低: {confidence}，过滤")
                return False
            return True
        except Exception as e:
            logger.error(f"过滤归因置信度失败: {e}")
            return False

    def filter_attribution_list(self, attribution_list: List[Dict]) -> List[Dict]:
        """
        过滤归因结果列表

        :param attribution_list: 归因结果列表
        :return: 过滤后的归因结果列表
        """
        if not attribution_list:
            return []

        filtered = []
        for attribution in attribution_list:
            if self.filter_attribution_by_confidence(attribution):
                filtered.append(attribution)

        if len(filtered) != len(attribution_list):
            logger.info(f"归因结果过滤: {len(attribution_list)} -> {len(filtered)}")

        return filtered

    def get_filtered_news(self, hours: int = None) -> List[Dict]:
        """
        获取过滤后的新闻列表

        :param hours: 时效限制（小时），None表示使用配置值
        :return: 过滤后的新闻列表
        """
        try:
            collection_name = "news_events"

            # 构建时间查询
            max_age = hours if hours else self.max_news_age
            cutoff_time = datetime.now() - timedelta(hours=max_age)

            query = {
                'publish_time': {'$gte': cutoff_time},
                'source': {'$in': self.trusted_sources},
            }

            news_list = list(mongo_client.find(collection_name, query, limit=10000))
            logger.info(f"获取到 {len(news_list)} 条有效新闻")

            return news_list
        except Exception as e:
            logger.error(f"获取过滤新闻失败: {e}")
            return []


def main():
    """测试主函数"""
    risk_filter = RiskFilter()

    # 测试新闻过滤
    test_news = [
        {
            'event_id': 'test1',
            'news_title': '测试新闻1',
            'news_content': '测试内容',
            'publish_time': datetime.now(),
            'source': '东方财富',
        },
        {
            'event_id': 'test2',
            'news_title': '测试新闻2',
            'news_content': '测试内容',
            'publish_time': datetime.now() - timedelta(hours=48),
            'source': '未知来源',
        },
    ]

    filtered = risk_filter.filter_news(test_news)
    print(f"过滤后新闻: {len(filtered)}")

    # 测试归因过滤
    test_attribution = [
        {
            'attribution_id': 'attr1',
            'board_name': '半导体',
            'confidence_score': 0.85,
        },
        {
            'attribution_id': 'attr2',
            'board_name': '新能源',
            'confidence_score': 0.35,
        },
    ]

    filtered_attr = risk_filter.filter_attribution_list(test_attribution)
    print(f"过滤后归因: {len(filtered_attr)}")


if __name__ == "__main__":
    main()
