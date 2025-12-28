import my_akshare as ak
import logging as logger

if __name__ == '__main__':
    stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
    print(stock_zh_a_spot_em_df)
    print("1")
    logger.info("log")