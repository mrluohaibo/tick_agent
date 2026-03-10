#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 板块基础数据采集模块
定时拉取行业/概念板块成分股列表，存储到MySQL
"""

import time
from typing import Dict, List, Optional

import akshare as ak
import pandas as pd

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_init import application_conf
from utils.logger_config import logger
from utils.db_tool_init import mysql_client
from utils.datetime_util import DateTimeUtil


class BoardDataCollector:
    """板块基础数据采集器"""

    def __init__(self):
        self.retry_times = 3
        self.retry_interval = 10  # seconds

    def run(self) -> Dict[str, int]:
        """运行板块数据采集（供scheduler调用）"""
        return self.collect_and_save_boards()

    def collect_industry_boards(self) -> pd.DataFrame:
        """
        采集行业板块数据

        :return: 行业板块DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                logger.info(f"第 {attempt + 1} 次尝试采集行业板块数据...")
                # 使用东方财富行业板块接口
                board_df = ak.stock_board_industry_name_em()
                if board_df is not None and not board_df.empty:
                    logger.info(f"成功采集到 {len(board_df)} 个行业板块")
                    return board_df
                else:
                    logger.warning("行业板块数据为空")
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"采集行业板块失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    logger.error("超过最大重试次数，放弃采集")
                    return pd.DataFrame()

    def collect_concept_boards(self) -> pd.DataFrame:
        """
        采集概念板块数据

        :return: 概念板块DataFrame
        """
        for attempt in range(self.retry_times):
            try:
                logger.info(f"第 {attempt + 1} 次尝试采集概念板块数据...")
                # 使用东方财富概念板块接口
                board_df = ak.stock_board_concept_name_em()
                if board_df is not None and not board_df.empty:
                    logger.info(f"成功采集到 {len(board_df)} 个概念板块")
                    return board_df
                else:
                    logger.warning("概念板块数据为空")
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"采集概念板块失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    logger.error("超过最大重试次数，放弃采集")
                    return pd.DataFrame()

    def save_board_basic(self, board_df: pd.DataFrame, board_type: str) -> int:
        """
        保存板块基础数据到MySQL

        :param board_df: 板块数据DataFrame
        :param board_type: 板块类型 (industry/concept)
        :return: 插入/更新的数量
        """
        if board_df.empty:
            logger.warning(f"{board_type} 板块数据为空")
            return 0

        count = 0
        current_time = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()

        # 字段映射（根据实际接口返回的字段调整）
        column_mapping = {
            '板块名称': 'board_name',
            '板块代码': 'board_code',
        }

        # 获取实际存在的列
        available_columns = [col for col in column_mapping.keys() if col in board_df.columns]
        if not available_columns:
            logger.error(f"{board_type} 板块数据缺少必要字段")
            return 0

        for _, row in board_df.iterrows():
            try:
                # 构建板块基础数据
                board_name = row.get('板块名称', '')
                board_code = row.get('板块代码', '')

                if not board_name:
                    continue

                # 检查是否存在
                query_sql = "SELECT board_name FROM board_basic WHERE board_name = %s"
                existing = mysql_client.query(query_sql, (board_name,))

                if existing:
                    # 更新
                    update_sql = """
                        UPDATE board_basic
                        SET board_code = %s,
                            update_time = %s
                        WHERE board_name = %s
                    """
                    mysql_client.execute(update_sql, (board_code, current_time, board_name))
                else:
                    # 插入
                    insert_sql = """
                        INSERT INTO board_basic (board_name, board_type, board_code, create_time, update_time)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    mysql_client.execute(insert_sql, (board_name, board_type, board_code, current_time, current_time))

                count += 1
            except Exception as e:
                logger.error(f"保存板块基础数据失败: {e}")

        logger.info(f"成功保存 {count} 个{board_type}板块基础数据")
        return count

    def collect_board_components(self, board_name: str, board_type: str = 'concept') -> List[Dict]:
        """
        采集板块成分股

        :param board_name: 板块名称
        :param board_type: 板块类型
        :return: 成分股列表
        """
        for attempt in range(self.retry_times):
            try:
                logger.debug(f"采集板块 {board_name} 的成分股...")

                # 根据板块类型选择不同的接口
                if board_type == 'concept':
                    # 概念板块成分股
                    components_df = ak.stock_board_concept_cons_em(symbol=board_name)
                else:
                    # 行业板块成分股（待实现具体接口）
                    logger.warning(f"行业板块成分股采集接口待实现")
                    return []

                if components_df is not None and not components_df.empty:
                    logger.debug(f"板块 {board_name} 有 {len(components_df)} 个成分股")
                    # TODO: 实际实现需要根据具体API返回的数据结构解析
                    return []

            except Exception as e:
                logger.debug(f"采集板块成分股失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_interval)
                else:
                    return []

        return []

    def save_board_components(self, components: List[Dict], board_name: str) -> int:
        """
        保存板块成分股到MySQL

        :param components: 成分股列表
        :param board_name: 板块名称
        :return: 插入/更新的数量
        """
        if not components:
            return 0

        count = 0
        current_time = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()

        for comp in components:
            try:
                stock_code = comp.get('stock_code', '')
                stock_name = comp.get('stock_name', '')
                weight = comp.get('weight', 0.0)

                if not stock_code:
                    continue

                # 检查是否存在
                query_sql = "SELECT id FROM board_component WHERE board_name = %s AND stock_code = %s"
                existing = mysql_client.query(query_sql, (board_name, stock_code))

                if existing:
                    # 更新
                    update_sql = """
                        UPDATE board_component
                        SET stock_name = %s, weight = %s
                        WHERE board_name = %s AND stock_code = %s
                    """
                    mysql_client.execute(update_sql, (stock_name, weight, board_name, stock_code))
                else:
                    # 插入
                    insert_sql = """
                        INSERT INTO board_component (board_name, stock_code, stock_name, weight, add_time)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    mysql_client.execute(insert_sql, (board_name, stock_code, stock_name, weight, current_time))

                count += 1
            except Exception as e:
                logger.error(f"保存板块成分股失败: {e}")

        return count

    def collect_and_save_boards(self) -> Dict[str, int]:
        """
        采集并保存板块数据的主方法

        :return: 采集结果统计
        """
        result = {
            'industry_count': 0,
            'concept_count': 0,
            'total_saved': 0,
        }

        # 采集行业板块
        industry_df = self.collect_industry_boards()
        if not industry_df.empty:
            result['industry_count'] = self.save_board_basic(industry_df, 'industry')

        # 采集概念板块
        concept_df = self.collect_concept_boards()
        if not concept_df.empty:
            result['concept_count'] = self.save_board_basic(concept_df, 'concept')

        result['total_saved'] = result['industry_count'] + result['concept_count']

        logger.info(f"板块数据采集完成: {result}")
        return result

    def get_all_boards(self) -> List[Dict]:
        """
        获取所有板块列表

        :return: 板块列表
        """
        try:
            sql = "SELECT board_name, board_type FROM board_basic"
            boards = mysql_client.query(sql)
            if boards:
                return [{'board_name': row['board_name'], 'board_type': row['board_type']} for row in boards]
            return []
        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return []


def main():
    """测试主函数"""
    collector = BoardDataCollector()

    # 采集并保存板块数据
    result = collector.collect_and_save_boards()
    print(f"采集结果: {result}")

    # 获取所有板块
    boards = collector.get_all_boards()
    print(f"板块列表: {len(boards)} 个")


if __name__ == "__main__":
    main()
