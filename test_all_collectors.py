#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
测试所有数据采集模块
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入采集模块
from bz_core.news_collector import NewsCollector
from bz_core.board_data_collector import BoardDataCollector
from bz_core.quote_collector import QuoteCollector

def test_news_collector():
    """测试新闻采集器"""
    print("=" * 60)
    print("测试新闻采集器")
    print("=" * 60)

    collector = NewsCollector()

    # 测试新闻采集
    print("\n1. 测试新闻采集...")
    news_df = collector.collect_news_em()
    if not news_df.empty:
        print(f"成功采集 {len(news_df)} 条新闻")

        # 测试数据处理
        documents = collector.process_news_data(news_df)
        print(f"成功处理 {len(documents)} 条新闻文档")
    else:
        print("新闻采集失败")

def test_board_data_collector():
    """测试板块数据采集器"""
    print("\n" + "=" * 60)
    print("测试板块数据采集器")
    print("=" * 60)

    collector = BoardDataCollector()

    # 测试行业板块采集
    print("\n1. 测试行业板块采集...")
    industry_df = collector.collect_industry_boards()
    if not industry_df.empty:
        print(f"成功采集 {len(industry_df)} 个行业板块")
    else:
        print("行业板块采集失败")

    # 测试概念板块采集
    print("\n2. 测试概念板块采集...")
    concept_df = collector.collect_concept_boards()
    if not concept_df.empty:
        print(f"成功采集 {len(concept_df)} 个概念板块")

        # 测试成分股采集
        if len(concept_df) > 0:
            board_name = concept_df.iloc[0]['板块名称']
            print(f"\n3. 测试概念板块 '{board_name}' 的成分股采集...")
            # 注释掉数据库保存，避免需要真实数据库连接
            # components = collector.save_board_components(board_name, 'concept')
            # print(f"成功获取 {len(components)} 个成分股")
            print("成分股采集功能已实现（需要MySQL连接才能测试）")
    else:
        print("概念板块采集失败")

def test_quote_collector():
    """测试行情采集器"""
    print("\n" + "=" * 60)
    print("测试行情采集器")
    print("=" * 60)

    collector = QuoteCollector()

    # 检查是否在交易时间
    if collector.is_trading_time():
        print("当前为交易时间，开始采集实时行情...")

        # 测试行业板块行情
        print("\n1. 测试行业板块行情采集...")
        industry_quotes = collector.collect_industry_quotes()
        if not industry_quotes.empty:
            print(f"成功采集 {len(industry_quotes)} 个行业板块行情")
        else:
            print("行业板块行情采集失败")

        # 测试概念板块行情
        print("\n2. 测试概念板块行情采集...")
        concept_quotes = collector.collect_concept_quotes()
        if not concept_quotes.empty:
            print(f"成功采集 {len(concept_quotes)} 个概念板块行情")

            # 测试行情数据处理
            print("\n3. 测试行情数据处理...")
            all_quotes = []
            if not industry_quotes.empty:
                industry_quotes['板块类型'] = '行业'
                all_quotes.append(industry_quotes)
            if not concept_quotes.empty:
                concept_quotes['板块类型'] = '概念'
                all_quotes.append(concept_quotes)

            if all_quotes:
                combined_df = all_quotes[0] if len(all_quotes) == 1 else pd.concat(all_quotes, ignore_index=True)
                processed_quotes = collector.process_quote_data(combined_df)
                print(f"成功处理 {len(processed_quotes)} 条行情数据")
        else:
            print("概念板块行情采集失败")
    else:
        print("当前非交易时间，跳过实时行情采集")

if __name__ == "__main__":
    # 注意：由于需要数据库连接，这里只测试数据采集部分
    print("开始测试数据采集模块（不包含数据库存储）...")

    try:
        test_news_collector()
        test_board_data_collector()
        test_quote_collector()

        print("\n" + "=" * 60)
        print("所有采集模块测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()