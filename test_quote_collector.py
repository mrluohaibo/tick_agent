#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
测试实时行情采集器
"""

import akshare as ak

def test_quote_collection():
    """测试实时行情采集"""
    print("测试开始：采集实时行情数据")

    try:
        # 测试概念板块实时行情
        print("\n1. 采集概念板块实时行情")
        concept_spot_df = ak.stock_board_concept_spot_em()
        print(f"成功获取 {len(concept_spot_df)} 个概念板块实时行情")
        if len(concept_spot_df) > 0:
            print("概念板块实时行情示例（TOP5涨幅）:")
            print(concept_spot_df.sort_values('涨跌幅', ascending=False).head(5).to_string())

        # 测试行业板块实时行情
        print("\n2. 采集行业板块实时行情")
        industry_spot_df = ak.stock_board_industry_spot_em()
        print(f"成功获取 {len(industry_spot_df)} 个行业板块实时行情")
        if len(industry_spot_df) > 0:
            print("行业板块实时行情示例（TOP5涨幅）:")
            print(industry_spot_df.sort_values('涨跌幅', ascending=False).head(5).to_string())

        # 测试板块资金流向
        print("\n3. 采集板块资金流向")
        fund_flow_df = ak.stock_board_fund_flow_rank_em()
        print(f"成功获取 {len(fund_flow_df)} 个板块资金流向数据")
        if len(fund_flow_df) > 0:
            print("板块资金流向示例（TOP5主力净流入）:")
            # 根据实际列名调整
            numeric_cols = ['主力净流入-净额', '超大单-净额', '大单-净额', '中单-净额', '小单-净额']
            available_cols = [col for col in numeric_cols if col in fund_flow_df.columns]
            if available_cols:
                result = fund_flow_df.nlargest(5, available_cols[0]) if available_cols[0] in fund_flow_df.columns else fund_flow_df.head(5)
                print(result[['板块名称', '主力净流入-净额'] + available_cols[1:]].to_string())

        # 测试实时行情异动检测
        print("\n4. 检测异动板块（涨幅>2%）")
        all_boards = []
        if len(concept_spot_df) > 0:
            concept_spot_df['板块类型'] = '概念'
            all_boards.append(concept_spot_df)
        if len(industry_spot_df) > 0:
            industry_spot_df['板块类型'] = '行业'
            all_boards.append(industry_spot_df)

        if all_boards:
            combined_df = pd.concat(all_boards, ignore_index=True)
            abnormal_boards = combined_df[combined_df['涨跌幅'] > 2.0]
            print(f"发现 {len(abnormal_boards)} 个异动板块")
            if len(abnormal_boards) > 0:
                print("异动板块列表:")
                print(abnormal_boards[['板块名称', '板块类型', '涨跌幅', '成交额', '换手率']].to_string())

        return True

    except Exception as e:
        print(f"采集失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 导入pandas
    import pandas as pd

    success = test_quote_collection()
    print(f"\n测试结果: {'成功' if success else '失败'}")