#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
测试新闻采集器功能
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 直接测试akshare新闻接口
import akshare as ak

def test_news_collection():
    """测试新闻采集功能"""
    print("测试开始：采集东方财富财经新闻")

    try:
        # 调用akshare接口获取新闻
        news_df = ak.news_stock_em()
        print(f"成功获取 {len(news_df)} 条新闻")

        # 显示前5条新闻
        if len(news_df) > 0:
            print("\n前5条新闻预览：")
            for i, row in news_df.head().iterrows():
                print(f"\n新闻 {i+1}:")
                print(f"标题: {row.get('title', 'N/A')}")
                print(f"时间: {row.get('date', 'N/A')}")
                print(f"内容: {row.get('content', 'N/A')[:100]}...")
                print(f"来源: {row.get('source', 'N/A')}")

        return True

    except Exception as e:
        print(f"采集失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_news_collection()
    print(f"\n测试结果: {'成功' if success else '失败'}")