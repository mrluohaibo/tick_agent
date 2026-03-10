#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Date: 2026-02-23
Desc: 日志配置模块
支持多模块日志，30天保留策略
"""

import logging
import logging.handlers
import os
from datetime import datetime
from bz_core.Constant import root_path
from utils.config_init import application_conf


# ========================================================================
# 日志颜色配置
# ========================================================================

log_colors_config = {
    # 终端输出日志颜色配置
    'DEBUG': 'white',
    'INFO': 'cyan',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

default_formats = {
    # 终端输出格式
    'color_format': '%(log_color)s%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
    # 日志输出格式
    'log_format': '%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
}

# 日志保留天数
LOG_RETENTION_DAYS = 30


# ========================================================================
# 日志配置类
# ========================================================================

class LoggerConfig:
    """日志配置类"""

    def __init__(self):
        # 日志目录
        self.log_dir = os.path.join(root_path, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)

        # 从配置读取日志级别
        self.log_level = self._get_log_level()

        # 日志文件路径
        today = datetime.now().strftime('%Y-%m-%d')
        self.log_files = {
            'app': os.path.join(self.log_dir, f'app_{today}.log'),
            'data_collection': os.path.join(self.log_dir, f'data_collection_{today}.log'),
            'agent_news': os.path.join(self.log_dir, f'agent_news_{today}.log'),
            'agent_sector': os.path.join(self.log_dir, f'agent_sector_{today}.log'),
            'agent_reason': os.path.join(self.log_dir, f'agent_reason_{today}.log'),
            'agent_report': os.path.join(self.log_dir, f'agent_report_{today}.log'),
            'websocket': os.path.join(self.log_dir, f'websocket_{today}.log'),
        }

        # 日志大小限制 (100MB)
        self.max_bytes = 100 * 1024 * 1024

        # 备份文件数量 (30天 = 30个备份)
        self.backup_count = LOG_RETENTION_DAYS

    def _get_log_level(self):
        """从配置获取日志级别"""
        level_str = application_conf.get_properties("logging.level") or "INFO"
        return getattr(logging, level_str.upper(), logging.INFO)

    def setup_file_handler(self, log_file):
        """设置文件处理器"""
        # 使用RotatingFileHandler，按大小轮转
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )

        # 设置格式
        formatter = logging.Formatter(default_formats["log_format"])
        handler.setFormatter(formatter)

        return handler

    def setup_console_handler(self):
        """设置控制台处理器"""
        try:
            import colorlog
            handler = logging.StreamHandler()
            formatter = colorlog.ColoredFormatter(
                default_formats["color_format"],
                log_colors=log_colors_config
            )
            handler.setFormatter(formatter)
            return handler
        except ImportError:
            # colorlog不可用时使用普通格式
            handler = logging.StreamHandler()
            formatter = logging.Formatter(default_formats["log_format"])
            handler.setFormatter(formatter)
            return handler

    def create_logger(self, name, log_file):
        """创建logger"""
        logger = logging.getLogger(name)

        # 清除已有handler（防止重复）
        if logger.handlers:
            logger.handlers.clear()

        logger.propagate = False
        logger.setLevel(self.log_level)

        # 添加文件处理器
        file_handler = self.setup_file_handler(log_file)
        logger.addHandler(file_handler)

        # 添加控制台处理器
        console_handler = self.setup_console_handler()
        logger.addHandler(console_handler)

        return logger


# ========================================================================
# 全局日志实例
# ========================================================================

config = LoggerConfig()

# 应用主日志
logger = config.create_logger('app', config.log_files['app'])
logger.info("应用日志服务启动成功")

# 数据采集日志
data_collection_logger = config.create_logger('data_collection', config.log_files['data_collection'])
data_collection_logger.info("数据采集日志服务启动成功")

# 新闻Agent日志
news_agent_logger = config.create_logger('agent_news', config.log_files['agent_news'])
news_agent_logger.info("新闻Agent日志服务启动成功")

# 板块监控Agent日志
sector_agent_logger = config.create_logger('agent_sector', config.log_files['agent_sector'])
sector_agent_logger.info("板块Agent日志服务启动成功")

# 归因Agent日志
reason_agent_logger = config.create_logger('agent_reason', config.log_files['agent_reason'])
reason_agent_logger.info("归因Agent日志服务启动成功")

# 报告Agent日志
report_agent_logger = config.create_logger('agent_report', config.log_files['agent_report'])
report_agent_logger.info("报告Agent日志服务启动成功")

# WebSocket日志
websocket_logger = config.create_logger('websocket', config.log_files['websocket'])
websocket_logger.info("WebSocket日志服务启动成功")


# ========================================================================
# 辅助函数
# ========================================================================

def get_logger(name: str):
    """根据名称获取对应的logger"""
    logger_map = {
        'app': logger,
        'data_collection': data_collection_logger,
        'agent_news': news_agent_logger,
        'agent_sector': sector_agent_logger,
        'agent_reason': reason_agent_logger,
        'agent_report': report_agent_logger,
        'websocket': websocket_logger,
    }
    return logger_map.get(name, logger)


def log_agent_operation(agent_name: str, operation: str, **kwargs):
    """记录Agent操作日志"""
    agent_logger = get_logger(f'agent_{agent_name}')
    log_message = f"Agent[{agent_name}] {operation}"

    if kwargs:
        log_message += f" - {kwargs}"

    agent_logger.info(log_message)


def log_llm_request(agent_name: str, model: str, prompt_tokens: int, completion_tokens: int):
    """记录LLM请求日志（用于监控和成本计算）"""
    agent_logger = get_logger(f'agent_{agent_name}')
    log_message = f"LLM请求 - Agent[{agent_name}] Model[{model}] Prompt[{prompt_tokens}t] Completion[{completion_tokens}t]"
    agent_logger.debug(log_message)


def log_data_collection(module: str, operation: str, success: bool, **kwargs):
    """记录数据采集日志"""
    collection_logger = get_logger('data_collection')
    status = "成功" if success else "失败"
    log_message = f"{module}.{operation} - {status}"

    if kwargs:
        log_message += f" - {kwargs}"

    if success:
        collection_logger.info(log_message)
    else:
        collection_logger.error(log_message)


def clean_old_logs():
    """清理超过保留期的旧日志文件"""
    try:
        import glob
        import time

        now = time.time()
        cutoff = now - (LOG_RETENTION_DAYS * 86400)  # 转换为秒

        log_pattern = os.path.join(root_path, 'logs', '*.log*')
        old_files = []

        for filepath in glob.glob(log_pattern):
            if os.path.getmtime(filepath) < cutoff:
                old_files.append(filepath)

        # 删除旧文件
        for old_file in old_files:
            try:
                os.remove(old_file)
                logger.info(f"已清理旧日志文件: {old_file}")
            except Exception as e:
                logger.error(f"清理日志文件失败: {e} - {old_file}")

        if old_files:
            logger.info(f"已清理 {len(old_files)} 个旧日志文件")

    except Exception as e:
        logger.error(f"清理旧日志失败: {e}")


if __name__ == "__main__":
    """测试主函数"""
    print("日志配置测试:")

    # 测试各模块日志
    logger.info("应用日志测试")
    data_collection_logger.info("数据采集日志测试")
    news_agent_logger.info("新闻Agent日志测试")
    sector_agent_logger.info("板块Agent日志测试")
    reason_agent_logger.info("归因Agent日志测试")
    report_agent_logger.info("报告Agent日志测试")
    websocket_logger.info("WebSocket日志测试")

    # 测试辅助函数
    log_agent_operation('news', 'analyze', news_id='test_001')
    log_llm_request('news', 'gpt-4', 100, 50)
    log_data_collection('news_collector', 'collect_news', True, count=10)

    print("\n日志配置测试完成!")
    print(f"日志目录: {root_path}/logs")
    print(f"日志保留天数: {LOG_RETENTION_DAYS}")
