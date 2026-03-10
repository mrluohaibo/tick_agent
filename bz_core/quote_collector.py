#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 实时行情采集模块
盘中每1分钟拉取板块实时涨幅、资金流向，存储到Redis+MySQL
"""

import time
from datetime import datetime, date
from typing import Dict, List, Optional

import akshare as ak
import pandas as pd

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_init import application_conf
from utils.logger_config import logger
from utils.db_tool_init import mysql_client, redis_client
from utils.datetime_util import DateTimeUtil


class QuoteCollector:
    """实时行情采集器"""

    def __init__(self):
        self.retry_times = 3
        self.retry_interval = 10  # seconds

    def run(self) -> Dict[str, int]:
        """运行行情采集（供scheduler调用）"""
        return self.collect_and_save_quotes()

    def is_trading_time(self) -> bool:
        """
        判断当前是否为交易时间

        :return: 是否为交易时间
        """
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()

        # 周末不交易
        if now.weekday() >= 5:  # 5=周六, 6=周日
            return False

        # 定义交易时间段
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()

        # 判断是否在交易时间内
        is_morning = morning_start <= current_time <= morning_end
        is_afternoon = afternoon_start <= current_time <= afternoon_end

        return is_morning or is_afternoon

    def collect_industry_quotes(self) -> pd.DataFrame:
        """
        采集行业板块实时行情

        :return: 行业板块行情DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                logger.debug(f"第 {attempt + 1} 次尝试采集行业板块行情...")
                # 使用东方财富行业板块实时行情接口
                quote_df = ak.stock_board_industry_spot_em()
                if quote_df is not None and not quote_df.empty:
                    logger.debug(f"成功采集到 {len(quote_df)} 个行业板块行情")
                    return quote_df
                else:
                    logger.debug("行业板块行情数据为空")
                    return pd.DataFrame()
            except Exception as e:
                logger.debug(f"采集行业板块行情失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    return pd.DataFrame()

    def collect_concept_quotes(self) -> pd.DataFrame:
        """
        采集概念板块实时行情

        :return: 概念板块行情DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                logger.debug(f"第 {attempt + 1} 次尝试采集概念板块行情...")
                # 使用东方财富概念板块实时行情接口
                quote_df = ak.stock_board_concept_spot_em()
                if quote_df is not None and not quote_df.empty:
                    logger.debug(f"成功采集到 {len(quote_df)} 个概念板块行情")
                    return quote_df
                else:
                    logger.debug("概念板块行情数据为空")
                    return pd.DataFrame()
            except Exception as e:
                logger.debug(f"采集概念板块行情失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    return pd.DataFrame()

    def process_quote_data(self, quote_df: pd.DataFrame) -> List[Dict]:
        """
        处理行情数据，转换为统一的字典格式

        :param quote_df: 原始行情DataFrame
        :return: 处理后的行情数据列表
        """
        if quote_df.empty:
            return []

        documents = []
        quote_time = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()

        # 字段映射（根据实际接口返回的字段调整）
        column_mapping = {
            '板块名称': 'board_name',
            '最新价': 'latest_price',
            '涨跌幅': 'change_rate',
            '涨跌额': 'change_amount',
            '成交量': 'volume',
            '成交额': 'turnover_amount',
            '换手率': 'turnover_rate',
            '量比': 'volume_ratio',
            '上涨家数': 'up_count',
            '下跌家数': 'down_count',
        }

        # 获取实际存在的列
        available_columns = [col for col in column_mapping.keys() if col in quote_df.columns]

        if not available_columns:
            logger.error("行情数据缺少必要字段")
            return []

        for _, row in quote_df.iterrows():
            try:
                doc = {}
                for zh_col in available_columns:
                    en_col = column_mapping[zh_col]
                    doc[en_col] = row.get(zh_col, 0)

                doc['quote_time'] = quote_time

                # 确保数值类型正确
                numeric_fields = ['latest_price', 'change_rate', 'change_amount', 'volume',
                               'turnover_amount', 'turnover_rate', 'volume_ratio', 'up_count', 'down_count']
                for field in numeric_fields:
                    if field in doc:
                        try:
                            doc[field] = float(doc[field])
                        except (ValueError, TypeError):
                            doc[field] = 0.0

                documents.append(doc)
            except Exception as e:
                logger.warning(f"处理行情数据失败: {e}")
                continue

        return documents

    def save_quote_to_redis(self, quotes: List[Dict]) -> int:
        """
        保存实时行情到Redis缓存

        :param quotes: 行情数据列表
        :return: 保存的数量
        """
        count = 0
        for quote in quotes:
            try:
                board_name = quote.get('board_name', '')
                if not board_name:
                    continue

                # Redis键格式: board:realtime:{board_name}
                redis_key = f"board:realtime:{board_name}"

                # 使用Hash存储行情数据
                quote_hash = {
                    'quote_time': str(quote.get('quote_time', '')),
                    'change_rate': str(quote.get('change_rate', 0)),
                    'turnover_amount': str(quote.get('turnover_amount', 0)),
                    'volume_ratio': str(quote.get('volume_ratio', 0)),
                    'limit_up_count': str(quote.get('up_count', 0)),
                    'limit_down_count': str(quote.get('down_count', 0)),
                    'turnover_rate': str(quote.get('turnover_rate', 0)),
                    'latest_price': str(quote.get('latest_price', 0)),
                }

                # 设置过期时间为5分钟
                redis_client.client.hset(redis_key, mapping=quote_hash)
                redis_client.client.expire(redis_key, 300)  # 5分钟 = 300秒

                count += 1
            except Exception as e:
                logger.error(f"保存行情到Redis失败: {e}")

        logger.debug(f"成功保存 {count} 条行情到Redis")
        return count

    def save_quote_to_mysql(self, quotes: List[Dict]) -> int:
        """
        保存实时行情到MySQL

        :param quotes: 行情数据列表
        :return: 保存的数量
        """
        if not quotes:
            return 0

        count = 0
        current_time = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()

        for quote in quotes:
            try:
                board_name = quote.get('board_name', '')
                if not board_name:
                    continue

                insert_sql = """
                    INSERT INTO board_quote_realtime
                    (board_name, quote_time, change_rate, turnover_amount, volume_ratio,
                     limit_up_count, limit_down_count, turnover_rate, latest_price, create_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                values = (
                    board_name,
                    quote.get('quote_time', current_time),
                    quote.get('change_rate', 0),
                    quote.get('turnover_amount', 0),
                    quote.get('volume_ratio', 0),
                    quote.get('up_count', 0),
                    quote.get('down_count', 0),
                    quote.get('turnover_rate', 0),
                    quote.get('latest_price', 0),
                    current_time,
                )

                mysql_client.execute(insert_sql, values)
                count += 1
            except Exception as e:
                logger.error(f"保存行情到MySQL失败: {e}")

        logger.info(f"成功保存 {count} 条行情到MySQL")
        return count

    def archive_daily_quotes(self) -> int:
        """
        归档当日行情数据到历史表

        :return: 归档的数量
        """
        try:
            today = date.today()

            # 从实时行情表中查询今日数据
            # 取每个板块的最后一条记录作为收盘数据
            query_sql = """
                SELECT board_name,
                       MIN(latest_price) as open_price,
                       MAX(latest_price) as high_price,
                       MIN(latest_price) as low_price,
                       MAX(latest_price) as close_price,
                       MAX(change_rate) as change_rate,
                       SUM(turnover_amount) as turnover_amount,
                       SUM(net_inflow) as net_inflow,
                       SUM(volume) as volume
                FROM board_quote_realtime
                WHERE DATE(quote_time) = %s
                GROUP BY board_name
            """

            results = mysql_client.query(query_sql, (today,))

            count = 0
            for row in results:
                try:
                    insert_sql = """
                        INSERT INTO board_quote_history
                        (board_name, quote_date, open_price, high_price, low_price, close_price,
                         change_rate, turnover_amount, net_inflow, volume, create_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            open_price = VALUES(open_price),
                            high_price = VALUES(high_price),
                            low_price = VALUES(low_price),
                            close_price = VALUES(close_price),
                            change_rate = VALUES(change_rate),
                            turnover_amount = VALUES(turnover_amount),
                            net_inflow = VALUES(net_inflow),
                            volume = VALUES(volume)
                    """

                    values = (
                        row['board_name'],
                        today,
                        row['open_price'],
                        row['high_price'],
                        row['low_price'],
                        row['close_price'],
                        row['change_rate'],
                        row['turnover_amount'],
                        row['net_inflow'],
                        row['volume'],
                        DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss(),
                    )

                    mysql_client.execute(insert_sql, values)
                    count += 1
                except Exception as e:
                    logger.error(f"归档行情数据失败: {e}")

            logger.info(f"成功归档 {count} 个板块的当日行情")
            return count

        except Exception as e:
            logger.error(f"归档当日行情失败: {e}")
            return 0

    def collect_and_save_quotes(self) -> Dict[str, int]:
        """
        采集并保存实时行情的主方法

        :return: 采集结果统计
        """
        result = {
            'industry_count': 0,
            'concept_count': 0,
            'redis_count': 0,
            'mysql_count': 0,
        }

        # 检查是否为交易时间
        if not self.is_trading_time():
            logger.info("当前不在交易时间，跳过行情采集")
            return result

        # 采集行业板块行情
        industry_quotes = self.process_quote_data(self.collect_industry_quotes())
        result['industry_count'] = len(industry_quotes)

        # 采集概念板块行情
        concept_quotes = self.process_quote_data(self.collect_concept_quotes())
        result['concept_count'] = len(concept_quotes)

        # 合并所有行情
        all_quotes = industry_quotes + concept_quotes

        if all_quotes:
            # 保存到Redis
            result['redis_count'] = self.save_quote_to_redis(all_quotes)

            # 保存到MySQL
            result['mysql_count'] = self.save_quote_to_mysql(all_quotes)

        logger.debug(f"实时行情采集完成: {result}")
        return result

    def get_top_boards(self, limit: int = 10) -> List[Dict]:
        """
        获取涨跌幅最大的板块

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


def main():
    """测试主函数"""
    collector = QuoteCollector()

    # 采集并保存行情
    result = collector.collect_and_save_quotes()
    print(f"采集结果: {result}")

    # 获取领涨板块
    top_boards = collector.get_top_boards(limit=5)
    print(f"领涨板块: {top_boards}")


if __name__ == "__main__":
    main()
