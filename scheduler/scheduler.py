#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 定时任务调度器
使用APScheduler实现定时任务调度
"""

from datetime import datetime, time as dt_time
import os
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.config_init import application_conf
from utils.logger_config import logger
from bz_core.news_collector import NewsCollector
from bz_core.board_data_collector import BoardDataCollector
from bz_core.quote_collector import QuoteCollector


class StockScheduler:
    """股票数据定时任务调度器"""

    def __init__(self):
        # 使用中国时区
        self.china_tz = timezone('Asia/Shanghai')
        self.scheduler = BackgroundScheduler(timezone=self.china_tz)

        # 初始化采集器
        self.news_collector = NewsCollector()
        self.board_collector = BoardDataCollector()
        self.quote_collector = QuoteCollector()

        # 交易时间段配置
        self.trading_hours = {
            'morning': {'start': dt_time(9, 30), 'end': dt_time(11, 30)},
            'afternoon': {'start': dt_time(13, 0), 'end': dt_time(15, 0)},
        }

    def is_trading_time(self) -> bool:
        """
        判断当前是否为交易时间

        :return: 是否为交易时间
        """
        now = datetime.now(self.china_tz)
        current_time = now.time()
        current_date = now.date()

        # 周末不交易 (5=周六, 6=周日)
        if now.weekday() >= 5:
            return False

        # 判断是否在交易时间段内
        is_morning = self.trading_hours['morning']['start'] <= current_time <= self.trading_hours['morning']['end']
        is_afternoon = self.trading_hours['afternoon']['start'] <= current_time <= self.trading_hours['afternoon']['end']

        return is_morning or is_afternoon

    def collect_board_basic_job(self):
        """定时任务: 采集板块基础数据"""
        logger.info(">>> [定时任务] 开始采集板块基础数据")
        try:
            result = self.board_collector.collect_and_save_boards()
            logger.info(f"板块基础数据采集完成: {result}")
        except Exception as e:
            logger.error(f"板块基础数据采集失败: {e}")

    def collect_news_pre_market_job(self):
        """定时任务: 盘前采集新闻"""
        logger.info(">>> [定时任务] 开始盘前新闻采集")
        try:
            result = self.news_collector.collect_and_save_news()
            logger.info(f"盘前新闻采集完成: {result}")
        except Exception as e:
            logger.error(f"盘前新闻采集失败: {e}")

    def collect_news_intraday_job(self):
        """定时任务: 盘中采集新闻"""
        logger.info(">>> [定时任务] 开始盘中新闻采集")
        try:
            result = self.news_collector.collect_and_save_news()
            logger.info(f"盘中新闻采集完成: {result}")
        except Exception as e:
            logger.error(f"盘中新闻采集失败: {e}")

    def collect_quotes_intraday_job(self):
        """定时任务: 盘中采集实时行情"""
        logger.debug(">>> [定时任务] 开始盘中实时行情采集")
        try:
            if self.is_trading_time():
                result = self.quote_collector.collect_and_save_quotes()
                logger.debug(f"盘中实时行情采集完成: {result}")
            else:
                logger.debug("当前不在交易时间，跳过行情采集")
        except Exception as e:
            logger.error(f"盘中实时行情采集失败: {e}")

    def archive_quotes_post_market_job(self):
        """定时任务: 盘后归档行情数据"""
        logger.info(">>> [定时任务] 开始盘后行情归档")
        try:
            count = self.quote_collector.archive_daily_quotes()
            logger.info(f"盘后行情归档完成: {count} 个板块")
        except Exception as e:
            logger.error(f"盘后行情归档失败: {e}")

    def cleanup_old_data_job(self):
        """定时任务: 清理旧数据"""
        logger.info(">>> [定时任务] 开始清理旧数据")
        try:
            # 清理30天前的新闻
            # self.news_collector.clean_old_news(days=30)
            logger.info("旧数据清理完成")
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")

    def setup_jobs(self):
        """设置所有定时任务"""
        logger.info("开始设置定时任务...")

        # 1. 每日08:00 采集板块基础数据
        self.scheduler.add_job(
            self.collect_board_basic_job,
            CronTrigger(hour=8, minute=0, timezone=self.china_tz),
            id='board_basic_collection',
            name='板块基础数据采集',
            replace_existing=True
        )

        # 2. 每日08:30 盘前采集新闻
        self.scheduler.add_job(
            self.collect_news_pre_market_job,
            CronTrigger(hour=8, minute=30, timezone=self.china_tz),
            id='news_pre_market',
            name='盘前新闻采集',
            replace_existing=True
        )

        # 3. 盘中每10分钟采集一次新闻 (交易时间内)
        self.scheduler.add_job(
            self.collect_news_intraday_job,
            CronTrigger(day_of_week='mon-fri', hour='9-14', minute='*/10', timezone=self.china_tz),
            id='news_intraday',
            name='盘中新闻采集',
            replace_existing=True
        )

        # 4. 盘中每1分钟采集一次实时行情 (交易时间内)
        self.scheduler.add_job(
            self.collect_quotes_intraday_job,
            IntervalTrigger(minutes=1, timezone=self.china_tz),
            id='quotes_intraday',
            name='盘中实时行情采集',
            replace_existing=True
        )

        # 5. 每日15:30 盘后归档行情
        self.scheduler.add_job(
            self.archive_quotes_post_market_job,
            CronTrigger(hour=15, minute=30, timezone=self.china_tz),
            id='quotes_archive',
            name='盘后行情归档',
            replace_existing=True
        )

        # 6. 每日02:00 清理旧数据
        self.scheduler.add_job(
            self.cleanup_old_data_job,
            CronTrigger(hour=2, minute=0, timezone=self.china_tz),
            id='data_cleanup',
            name='清理旧数据',
            replace_existing=True
        )

        logger.info("定时任务设置完成")

    def print_jobs(self):
        """打印所有已设置的定时任务"""
        logger.info("当前已设置的定时任务:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - [{job.id}] {job.name}: {job.next_run_time}")

    def start(self):
        """启动调度器"""
        logger.info("正在启动股票数据调度器...")
        self.setup_jobs()
        self.print_jobs()
        self.scheduler.start()
        logger.info("调度器已启动，等待任务执行...")

    def stop(self):
        """停止调度器"""
        logger.info("正在停止调度器...")
        self.scheduler.shutdown()
        logger.info("调度器已停止")


def main():
    """主函数"""
    scheduler = StockScheduler()

    try:
        scheduler.start()

        # 保持主线程运行
        import signal
        import time

        def signal_handler(signum, frame):
            logger.info("接收到停止信号...")
            scheduler.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 无限循环保持程序运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("程序被中断")
        scheduler.stop()
    except Exception as e:
        logger.error(f"调度器运行异常: {e}")
        scheduler.stop()


if __name__ == "__main__":
    main()
