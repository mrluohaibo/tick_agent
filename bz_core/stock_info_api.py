import os

import my_akshare as ak
import pandas as pd

from bz_core import Constant
from bz_core.stock_dict import stock_dict_zh_2_en
from utils.HandleLog import  logger
from utils.StringUtil import StringUtil
from utils.datetime_util import DateTimeUtil
from utils.db_tool_init import mongo_client


class StockInfo():

    def __init__(self):
        self.stock_db_name =  "all_stock_basic"


    def get_all_stock_info(self):

        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
        excel_save_file = self.join_path(Constant.root_path,"temp_file_save/last_stock_info.xlsx")
        stock_zh_a_spot_em_df.to_excel(excel_save_file, index=False)
        self.handle_stock_pd_data(stock_zh_a_spot_em_df)
        # print(stock_zh_a_spot_em_df)


    def handle_stock_pd_data(self,df):
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

    def insert_stock_info_2_mongo(self,all_data):
        for per_row in all_data:
            unique_stock_code = per_row["stock_code"]
            query = {"stock_code": unique_stock_code}
            match_doc = mongo_client.find_one(self.stock_db_name,query=query)
            if match_doc is not None:
                per_row["update_time"] = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()
                mongo_client.update_one(self.stock_db_name,query=query, update={"$set":per_row})
            else:
                per_row["create_time"] = DateTimeUtil.now_time_yyyy_mm_dd_hh_mm_ss()
                mongo_client.insert_one(self.stock_db_name,per_row)

        logger.info(f" insert {self.stock_db_name} info:{len(all_data)}")



    def get_en_code_of_zh(self,zh_name):
        head_name_en = stock_dict_zh_2_en.get(zh_name,"")
        if head_name_en == "":
            logger.error(f"字段 {zh_name} 没有找到对应的en_code")
        return head_name_en


    def parse_xlsx_to_pd(self):
        excel_save_file = self.join_path(Constant.root_path, "temp_file_save/last_stock_info.xlsx")
        df = pd.read_excel(excel_save_file)
        self.handle_stock_pd_data(df)
        print(df)

    def join_path(self,a,b):
        return os.path.join(a,b)




if __name__ == "__main__":

    stock_info = StockInfo()
    stock_info.parse_xlsx_to_pd()
    logger.info("ok!!!")