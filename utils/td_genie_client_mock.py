from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from utils.logger_config import  logger


class MockTDEngineClient:
    """TDengine客户端的Mock版本，用于测试时跳过TDengine"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6030,
        user: str = "root",
        password: str = "taosdata",
        database: Optional[str] = None,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.timeout = timeout
        self._conn = None
        self.connect()

    def connect(self):
        """建立Mock连接"""
        try:
            # 模拟连接成功
            self._conn = "mock_connection"
            logger.info(f"🔗 Mock TDengine connection established at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"❌ Mock connection failed: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn = None
            logger.info("🔌 Mock connection closed")

    def execute(self, sql: str) -> int:
        """执行非查询语句（Mock）"""
        logger.debug(f"📝 Mock execute: {sql}")
        # 返回模拟影响的行数
        return 0

    def query(self, sql: str) -> List[Tuple]:
        """执行查询语句（Mock）"""
        logger.debug(f"🔍 Mock query: {sql}")
        # 返回空结果集
        return []

    @contextmanager
    def get_cursor(self):
        """获取游标上下文管理器"""
        mock_cursor = MockCursor()
        try:
            yield mock_cursor
        finally:
            mock_cursor.close()

    def __enter__(self):
        """支持with语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出with语句时自动关闭连接"""
        self.close()


class MockCursor:
    """Mock游标"""

    def __init__(self):
        self._description = None
        self._rowcount = 0

    def execute(self, sql: str):
        """执行SQL"""
        logger.debug(f"📝 Mock cursor execute: {sql}")

    def fetchall(self) -> List[Tuple]:
        """获取所有结果"""
        return []

    def fetchone(self) -> Optional[Tuple]:
        """获取一条结果"""
        return None

    def close(self):
        """关闭游标"""
        logger.debug("🔌 Mock cursor closed")


# 为了兼容性，创建原来的TDEngineClient的别名
TDEngineClient = MockTDEngineClient