import sqlite3
from typing import Optional

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