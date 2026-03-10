#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
测试akshare接口
"""

import akshare as ak

# 获取所有可用接口
print("akshare可用接口:")
attrs = [attr for attr in dir(ak) if not attr.startswith('_') and 'news' in attr.lower()]
print(f"包含news的接口: {attrs}")

# 测试新闻接口
print("\n尝试测试新闻接口...")

# 尝试获取新闻列表
try:
    # 可能的接口名称
    possible_news_funcs = [
        'news_stock_em',
        'news_sina',
        'news_howbuy',
        'news_cjnews',
        'news_eastmoney',
        'news_10jqka',
        'news_gszq',
        'news_xueqiu',
        'news_jinrongjie',
        'news_mmf'
    ]

    for func_name in possible_news_funcs:
        if hasattr(ak, func_name):
            print(f"\n尝试调用 {func_name}...")
            try:
                result = getattr(ak, func_name)()
                if isinstance(result, (list, dict)):
                    print(f"成功调用 {func_name}, 结果类型: {type(result)}")
                    if hasattr(result, 'head'):
                        print(f"返回了DataFrame，前3行:")
                        print(result.head(3))
                    elif len(result) > 0:
                        print(f"返回了 {len(result)} 条记录")
                        if isinstance(result[0], dict):
                            print("第一条记录:", result[0])
                break
            except Exception as e:
                print(f"调用 {func_name} 失败: {str(e)}")

except Exception as e:
    print(f"错误: {str(e)}")

# 测试行情接口
print("\n\n测试行情接口...")
board_funcs = [attr for attr in dir(ak) if 'board' in attr.lower() and not attr.startswith('_')]
print(f"包含board的接口: {board_funcs}")