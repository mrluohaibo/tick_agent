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