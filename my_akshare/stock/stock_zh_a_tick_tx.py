#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2023/10/27 22:08
Desc: 腾讯-股票-实时行情-成交明细
成交明细-每个交易日 16:00 提供当日数据
港股报价延时 15 分钟
"""
import time

from utils.logger_config import  logger
import traceback
import warnings

import pandas as pd
import requests
from urllib.parse import urlencode, urljoin


def stock_zh_a_tick_tx_js(symbol: str = "sz000001") -> pd.DataFrame:
    """
    腾讯财经-历史分笔数据  这个接口存在数据不全的问题，估计需要走代理
    https://gu.qq.com/sz300494/gp/detail
    :param symbol: 股票代码
    :type symbol: str
    :return: 历史分笔数据
    :rtype: pandas.DataFrame
    """
    big_df = pd.DataFrame()
    page = 0
    warnings.warn("正在下载数据，请稍等")
    while True:
        try:
            url = "http://stock.gtimg.cn/data/index.php"
            params = {
                "appn": "detail",
                "action": "data",
                "c": symbol,
                "p": page,
            }
            # 将参数编码为查询字符串
            query_string = urlencode(params)

            # 拼接完整 URL
            full_url = url + "?" + query_string
            # time.sleep(0.5)

            headers = {
                "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }
            r = requests.get(full_url,headers = headers)
            text_data = r.text
            if text_data == "":
                logger.info(f"tick data text is empty for page {page}")
                break
            logger.info(f"stock_code {symbol} page {page} return not empty")
            temp_df = (
                pd.DataFrame(eval(text_data[text_data.find("[") :])[1].split("|"))
                .iloc[:, 0]
                .str.split("/", expand=True)
            )
            page += 1
            big_df = pd.concat([big_df, temp_df], ignore_index=True)
        except Exception as e:
            # noqa: E722
            info = traceback.format_exc()
            logger.error(info)
            break
    if not big_df.empty:
        big_df = big_df.iloc[:, 1:].copy()
        big_df.columns = [
            "成交时间",
            "成交价格",
            "价格变动",
            "成交量",
            "成交金额",
            "性质",
        ]
        big_df.reset_index(drop=True, inplace=True)
        property_map = {
            "S": "卖盘",
            "B": "买盘",
            "M": "中性盘",
        }
        big_df["性质"] = big_df["性质"].map(property_map)
        big_df = big_df.astype(
            {
                "成交时间": str,
                "成交价格": float,
                "价格变动": float,
                "成交量": int,
                "成交金额": int,
                "性质": str,
            }
        )
    return big_df

def request_with_url(url):
    pass


if __name__ == "__main__":
    stock_zh_a_tick_tx_js_df = stock_zh_a_tick_tx_js(symbol="sh601166")
    print(stock_zh_a_tick_tx_js_df)
