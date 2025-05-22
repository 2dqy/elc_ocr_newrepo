import sqlite3
from typing import Optional
import pymysql
from contextlib import contextmanager
from typing import Generator
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class DatabaseConfig:
    """数据库配置类"""
    HOST: str = os.getenv('DB_HOST', 'localhost')
    USER: str = os.getenv('DB_USER', 'root')
    PASSWORD: str = os.getenv('DB_PASSWORD', '')
    DATABASE: str = os.getenv('DB_NAME', 'ocr')
    PORT: int = int(os.getenv('DB_PORT', 3306))

class DatabaseSession:
    """数据库会话管理类"""
    
    @staticmethod
    def get_connection():
        """获取数据库连接"""
        return pymysql.connect(
            host=DatabaseConfig.HOST,
            user=DatabaseConfig.USER,
            password=DatabaseConfig.PASSWORD,
            database=DatabaseConfig.DATABASE,
            port=DatabaseConfig.PORT,
            cursorclass=pymysql.cursors.DictCursor  # 使用字典游标
        )

    @contextmanager
    def get_cursor(self) -> Generator[pymysql.cursors.DictCursor, None, None]:
        """
        获取数据库游标的上下文管理器
        
        使用示例:
        ```python
        with DatabaseSession().get_cursor() as cursor:
            cursor.execute("SELECT * FROM table")
            result = cursor.fetchall()
        ```
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

# 创建全局数据库会话实例
db_session = DatabaseSession()

class Database:
    """数据库连接管理类"""
    def __init__(self, db_path: str = "app.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

    def get_allowed_ips(self) -> list:
        """获取允许的IP列表"""
        self.cursor.execute("SELECT ip FROM allowed_ips")
        return [row[0] for row in self.cursor.fetchall()]

    def token_exists(self, token: str) -> bool:
        """检查token是否存在"""
        self.cursor.execute("SELECT COUNT(*) FROM tokens WHERE token = ?", (token,))
        return self.cursor.fetchone()[0] > 0

    def center_id_exists(self, center_id: str) -> bool:
        """检查center_id是否存在"""
        self.cursor.execute("SELECT COUNT(*) FROM centers WHERE id = ?", (center_id,))
        return self.cursor.fetchone()[0] > 0

    def add_token(self, token: str, use_times: int, center_id: str):
        """
        添加新token
        
        Args:
            token: token字符串
            use_times: 可使用次数
            center_id: 中心ID
        """
        try:
            self.cursor.execute(
                "INSERT INTO tokens (token, use_times, center_id) VALUES (?, ?, ?)",
                (token, use_times, center_id)
            )
            self.connection.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError("Token已存在") from e

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close() 