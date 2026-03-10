#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 定时任务调度器
使用APScheduler实现定时任务调度
"""
import time
from datetime import datetime
import os
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone

# 添加项目根目录到Python路径
abspath = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(abspath)))
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
        self.cn_tz = timezone('Asia/Shanghai')
        self.scheduler = BackgroundScheduler(timezone=self.cn_tz)
        self.news_collector = NewsCollector()
        self.board_collector = BoardDataCollector()
        self.quote_collector = QuoteCollector()

        logger.info("初始化调度器...")

    def add_jobs(self):
        """添加定时任务"""

        # 板块基础数据采集 - 每天08:00
        self.scheduler.add_job(
            func=self.board_collector.run,
            trigger=CronTrigger(hour=8, minute=0, timezone=self.cn_tz),
            id='board_basic',
            name='板块基础数据采集',
            replace_existing=True
        )

        # 盘前新闻采集 - 每天08:30
        self.scheduler.add_job(
            func=self.news_collector.run,
            trigger=CronTrigger(hour=8, minute=30, timezone=self.cn_tz),
            id='pre_market_news',
            name='盘前新闻采集',
            replace_existing=True
        )

        # 盘中行情采集 - 交易时段每1分钟
        self.scheduler.add_job(
            func=self.quote_collector.run,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-14',
                minute='0-59',
                timezone=self.cn_tz
            ),
            id='intraday_quotes',
            name='盘中行情采集',
            replace_existing=True
        )

        # 盘后归档 - 每天15:30
        self.scheduler.add_job(
            func=self.archive_daily_data,
            trigger=CronTrigger(hour=15, minute=30, timezone=self.cn_tz),
            id='post_market_archive',
            name='盘后归档',
            replace_existing=True
        )

        logger.info("定时任务添加完成")

    def archive_daily_data(self):
        """盘后归档处理"""
        logger.info("执行盘后归档处理...")
        # TODO: 实现归档逻辑

    def start(self):
        """启动调度器"""
        self.add_jobs()
        self.scheduler.start()
        logger.info("调度器已启动")

        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
            logger.info("调度器已停止")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已停止")


if __name__ == '__main__':
    # 检查当前时间是否在交易时段
    now = datetime.now(timezone('Asia/Shanghai'))
    logger.info(f"当前时间: {now}")

    scheduler = StockScheduler()
    scheduler.start()
