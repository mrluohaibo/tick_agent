#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
测试板块数据采集器
"""

import akshare as ak

def test_board_data_collection():
    """测试板块数据采集"""
    print("测试开始：采集板块基础数据")

    try:
        # 测试概念板块数据
        print("\n1. 采集概念板块数据")
        concept_df = ak.stock_board_concept_name_em()
        print(f"成功获取 {len(concept_df)} 个概念板块")
        if len(concept_df) > 0:
            print("概念板块示例:")
            print(concept_df.head(3).to_string())

        # 测试行业板块数据
        print("\n2. 采集行业板块数据")
        industry_df = ak.stock_board_industry_name_em()
        print(f"成功获取 {len(industry_df)} 个行业板块")
        if len(industry_df) > 0:
            print("行业板块示例:")
            print(industry_df.head(3).to_string())

        # 测试概念板块成分股
        if len(concept_df) > 0:
            print("\n3. 采集第一个概念板块的成分股")
            concept_name = concept_df.iloc[0]['板块名称']
            components_df = ak.stock_board_concept_cons_em(symbol=concept_name)
            print(f"概念 '{concept_name}' 包含 {len(components_df)} 只成分股")
            print("成分股示例:")
            print(components_df.head(3).to_string())

        return True

    except Exception as e:
        print(f"采集失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_board_data_collection()
    print(f"\n测试结果: {'成功' if success else '失败'}")