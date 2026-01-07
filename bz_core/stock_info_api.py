import os
import time

import my_akshare as ak
import akshare as remote_ak
import pandas as pd

from bz_core import Constant
from bz_core.stock_dict import stock_dict_zh_2_en, stock_tick_dict
from utils.HandleLog import logger
from utils.StringUtil import StringUtil
from utils.datetime_util import DateTimeUtil
from utils.db_tool_init import mongo_client, td_engine_client


class StockInfo():

    def __init__(self):
        self.stock_db_name = "all_stock_basic"

    def get_all_stock_info(self):
        '''
        获取实时全股票数据
        :return:
        '''
        timestamp_before = time.time() * 1000
        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
        logger.info(f" get stock all info spend {time.time() * 1000 - timestamp_before} ms")
        date_str = DateTimeUtil.now_time_yyyymmdd()
        excel_save_file = self.join_path(Constant.root_path, f"temp_file_save/last_stock_info_{date_str}.xlsx")
        stock_zh_a_spot_em_df.to_excel(excel_save_file, index=False)
        timestamp_before = time.time() * 1000
        self.handle_stock_pd_data(stock_zh_a_spot_em_df)
        logger.info(f" save stock all info to db spend {time.time() * 1000 - timestamp_before} ms")
        # print(stock_zh_a_spot_em_df)

    def handle_stock_pd_data(self, df):
        heads = [
            # "序号",
            "代码",
            "名称",
            "最新价",
            "涨跌幅",
            "涨跌额",
            "成交量",
            "成交额",
            "振幅",
            "最高",
            "最低",
            "今开",
            "昨收",
            "量比",
            "换手率",
            "市盈率-动态",
            "市净率",
            "总市值",
            "流通市值",
            "涨速",
            "5分钟涨跌",
            "60日涨跌幅",
            "年初至今涨跌幅",
        ]
        all_data = []
        for index, row in df.iterrows():
            # print(f"行索引: {index}")
            # print(f"代码: {row['stock_code']}, 名称: {row['stock_name']}")
            item_row = {}
            has_data = False
            for head_name in heads:
                head_name_en = self.get_en_code_of_zh(head_name)
                if not StringUtil.is_empty(head_name_en):
                    item_row[head_name_en] = row[head_name]
                    if not has_data:
                        has_data = True
            if has_data:
                all_data.append(item_row)
        logger.info(f" refresh all stock info:{len(all_data)}")
        self.insert_stock_info_2_mongo(all_data)

    def insert_stock_info_2_mongo(self, all_data):
        '''
        每天盘后将最新数据更新到全局股票表中
        :param all_data:
        :return:
        '''
        for per_row in all_data:
            unique_stock_code = per_row["stock_code"]
            query = {"stock_code": unique_stock_code}
            match_doc = mongo_client.find_one(self.stock_db_name, query=query)
            if match_doc is not None:
                per_row["update_time"] = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()
                update_num = mongo_client.update_one(self.stock_db_name, query=query, update={"$set": per_row})
                logger.info(f"stock {unique_stock_code} update {update_num}")
            else:
                per_row["create_time"] = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()
                mongo_client.insert_one(self.stock_db_name, per_row)

        logger.info(f" insert {self.stock_db_name} info:{len(all_data)}")

    def get_en_code_of_zh(self, zh_name):
        head_name_en = stock_dict_zh_2_en.get(zh_name, "")
        if head_name_en == "":
            logger.error(f"字段 {zh_name} 没有找到对应的en_code")
        return head_name_en

    def parse_xlsx_to_pd(self):
        date_str = DateTimeUtil.now_time_yyyymmdd()
        excel_save_file = self.join_path(Constant.root_path, f"temp_file_save/last_stock_info_{date_str}.xlsx")
        df = pd.read_excel(excel_save_file)
        self.handle_stock_pd_data(df)

    def join_path(self, a, b):
        return os.path.join(a, b)

    def update_stock_industry(self):
        '''
         获取每只股票的行业
         并将行业形成字典表进行保存
         低频更新，基本可以一个一天更新一次就行了
        :return:
        '''
        # 分页获取 股票信息 1229 2124 更新的id
        last_id = ""
        page_size = 1000
        match_doc = mongo_client.get_cursor_paginated_data(self.stock_db_name, query={}, last_id=last_id,
                                                           page_size=page_size)
        while len(match_doc) > 0:
            last_id = match_doc[-1]["_id"]
            stock_code_list = [item["stock_code"] for item in match_doc]
            self.update_industry_stock(stock_code_list)
            if len(match_doc) < page_size:
                break
            else:
                match_doc = mongo_client.get_cursor_paginated_data(self.stock_db_name, query={}, last_id=last_id,
                                                                   page_size=page_size)

    def update_industry_stock(self, stock_code_list):
        '''

        :param stock_code_list:
        :return:
        '''
        if len(stock_code_list) > 0:
            for stock_code in stock_code_list:
                stock_individual_info_em_df = ak.stock_individual_info_em(symbol=stock_code)
                if stock_individual_info_em_df is not None:
                    stock_info = {}
                    has_data = False
                    for index, row in stock_individual_info_em_df.iterrows():
                        item_name = row["item"]
                        item_value = row["value"]
                        if item_name in ['行业', '上市时间', '总股本', '流通股']:
                            head_name_en = self.get_en_code_of_zh(item_name)
                            if not StringUtil.is_empty(head_name_en):
                                stock_info[head_name_en] = item_value
                                if not has_data:
                                    has_data = True

                    if has_data:
                        self.update_stock_other_info(stock_code, stock_info)

    def update_stock_other_info(self, stock_code, stock_info):
        query = {"stock_code": stock_code}
        match_doc = mongo_client.find_one(self.stock_db_name, query=query)
        if match_doc is not None:
            stock_info["update_time"] = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()
            update_num = mongo_client.update_one(self.stock_db_name, query=query, update={"$set": stock_info})
            logger.info(f"stock {stock_code} other info update {update_num}")
        else:
            logger.error(f"stock {stock_code} not exist,is impossible")

    def query_stock_tick_store_db(self, stock_code):
        '''
        历史分笔数据
        每个交易日 16:00 提供当日数据; 如遇到数据缺失, 请使用 ak.stock_zh_a_tick_163() 接口(注意数据会有一定差异)
        :param stock_code:
        :return:
        '''
        if StringUtil.is_empty(stock_code):
            logger.error(f"stock {stock_code} not exist,is impossible")
            raise Exception("股票代码不能为空")
        if not stock_code.startswith("s"):
            if stock_code.startswith("6"):
                stock_code = "sh" + stock_code
            else:
                stock_code = "sz" + stock_code

        stock_zh_a_tick_tx_js_df = ak.stock_zh_a_tick_tx_js(symbol=stock_code)
        if stock_zh_a_tick_tx_js_df.empty:
            logger.error(f"stock {stock_code} not exist")
            return
        if len(stock_zh_a_tick_tx_js_df) < 3000:
            fail_res = f"stock {stock_code} tick data len {stock_zh_a_tick_tx_js_df.size} not full"
            logger.error(fail_res)
            # raise Exception(fail_res)

        date_str = DateTimeUtil.now_time_yyyymmdd()
        format_date = DateTimeUtil.now_time_yyyy_mm_dd()
        excel_save_file = self.join_path(Constant.root_path,
                                         f"temp_file_save/last_stock_tick_{stock_code}_{date_str}.xlsx")
        stock_zh_a_tick_tx_js_df.to_excel(excel_save_file, index=False)
        self.store_stock_tick_to_db(stock_code,format_date, stock_zh_a_tick_tx_js_df)

    def read_stock_tick_excel_to_db(self, stock_code):
        if not stock_code.startswith("s"):
            if stock_code.startswith("6"):
                stock_code = "sh" + stock_code
            else:
                stock_code = "sz" + stock_code

        date_str = DateTimeUtil.now_time_yyyymmdd()
        format_date = DateTimeUtil.now_time_yyyy_mm_dd()
        excel_save_file = self.join_path(Constant.root_path,
                                         f"temp_file_save/last_stock_tick_{stock_code}_{date_str}.xlsx")

        df = pd.read_excel(excel_save_file)
        if df.empty:
            logger.error(f"stock {stock_code} not exist")
            return
        if len(df) <= 3000:
            logger.error(f"stock {stock_code} data not full")
            raise Exception(f"stock {stock_code} tick data len {df.size} not full")

        self.store_stock_tick_to_db(stock_code, format_date, df)

    def store_stock_tick_to_db(self, stock_code, format_date, stock_zh_a_tick_tx_js_df):
        heads = [
            # "序号",
            "成交时间",
            "成交价格",
            "价格变动",
            "成交量",
            "成交金额",
            "性质",
        ]
        self.delete_point_day_tick_data(stock_code, format_date)


        def get_en_code_of_zh_stock_tick(zh_name):
            head_name_en = stock_tick_dict.get(zh_name, "")
            if head_name_en == "":
                logger.error(f"字段 {zh_name} 没有找到对应的en_code")
            return head_name_en

        def get_nature_type(nature):
            if nature == "买盘":
                return 1
            elif nature == "卖盘":
                return -1
            else:
                return 0

        all_data = []

        for index, row in stock_zh_a_tick_tx_js_df.iterrows():
            # print(f"行索引: {index}")
            # print(f"代码: {row['stock_code']}, 名称: {row['stock_name']}")
            item_row = {}
            has_data = False
            for head_name in heads:
                head_name_en = get_en_code_of_zh_stock_tick(head_name)
                if not StringUtil.is_empty(head_name_en):
                    item_row[head_name_en] = row[head_name]
                    if not has_data:
                        has_data = True
            if has_data:
                item_row["trade_day"] = format_date
                item_row["ts"] = DateTimeUtil.str_to_timestamp_ms(
                    format_date + " " + item_row[get_en_code_of_zh_stock_tick("成交时间")])
                item_row["nature_type"] = get_nature_type(item_row[get_en_code_of_zh_stock_tick("性质")])
                all_data.append(item_row)
        logger.info(f" refresh all stock tick info:{len(all_data)}")
        self.insert_stock_tick_to_tdengine(stock_code,format_date, all_data)

    def insert_stock_tick_to_tdengine(self, stock_code,format_date, all_data):
        real_code = stock_code[2:]
        exchange = stock_code[:2]

        def dick_to_tuple(dict_list):
            keys = ["ts", "trade_day", "transaction_time", "transaction_price", "price_change", "trading_volume",
                    "transaction_volume", "nature_type"]
            result = [tuple(entry[k] for k in keys) for entry in dict_list]
            return result

        sql = f'INSERT INTO {stock_code} USING stock_tick TAGS ("{real_code}", "{exchange}")  VALUES (?,?,?,?,?,?,?,?)'
        batch_count = 50
        batch_list = []
        for item in all_data:

            batch_list.append(item)
            if len(batch_list) == batch_count:
                tuple_list = dick_to_tuple(batch_list)
                td_engine_client.insert_many(sql,data = tuple_list)
                batch_list =[]

        if len(batch_list) > 0:
            tuple_list = dick_to_tuple(batch_list)
            td_engine_client.insert_many(sql, data=tuple_list)
            batch_list = []

        logger.info(f"stock code:{stock_code} to tdengine store date {format_date} tick data ok，total len ：{len(all_data)}")

    def delete_point_day_tick_data(self, stock_code, format_date):
        # 插入单条数据

        td_engine_client.execute(f"""
                      DELETE FROM {stock_code}
                        WHERE ts BETWEEN '{format_date} 00:00:00' AND '{format_date} 23:59:59';
                       """)


if __name__ == "__main__":
    stock_info = StockInfo()
    # stock_info.update_stock_industry()
    stock_info.query_stock_tick_store_db("601166")

    logger.info("-------------ok!!!-------------------------")
