from datetime import datetime

class DateTimeUtil(object):

    @staticmethod
    def now_time_yyyy_mm_dd_hh_mm_ss():
        now = datetime.now()
        parsed_time = now.strftime( "%Y-%m-%d %H:%M:%S")
        return parsed_time


    @staticmethod
    def now_time_yyyy_mm_dd():
        now = datetime.now()
        parsed_time = now.strftime( "%Y-%m-%d")
        return parsed_time

    @staticmethod
    def now_time_yyyymmdd():
        now = datetime.now()
        parsed_time = now.strftime("%Y%m%d")
        return parsed_time


    @staticmethod
    def str_to_timestamp_ms(time_str):
        # 解析字符串为 datetime 对象（假设为本地时区）
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        # 转换为 UTC 时间戳（秒），再乘以 1000 得到毫秒
        timestamp_ms = int(dt.timestamp() * 1000)
        return timestamp_ms