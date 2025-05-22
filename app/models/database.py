import pymysql
import os
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
from app.db.database import db_session
# 加载环境变量
load_dotenv()

class Database:
    def __init__(self, db_name='ocr'):
        self.conn = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT'))
        )
        self.cursor = self.conn.cursor()


    def add_token(self, token, use_times, center_id):
        try:
            self.cursor.execute(
                "INSERT INTO tokens (token, use_times, center_id) VALUES (%s, %s, %s)",
                (token, use_times, center_id)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except pymysql.IntegrityError:
            raise ValueError("Token already exists")

    def token_exists(self, token):
        self.cursor.execute("SELECT token FROM tokens WHERE token=%s", (token,))
        return bool(self.cursor.fetchone())

    def center_id_exists(self, center_id):
        self.cursor.execute("SELECT center_id FROM centers WHERE center_id=%s", (center_id,))
        return bool(self.cursor.fetchone())

    def add_center_id(self, center_id):
        try:
            self.cursor.execute(
                "INSERT INTO centers (center_id) VALUES (%s)",
                (center_id,)
            )
            self.conn.commit()
            return True
        except pymysql.IntegrityError:
            return False

    def close(self):
        self.conn.close()

    def get_allowed_ips(self):
        # 查询数据库中的允许的IP地址
        # 增加try except
        try:
            self.cursor.execute("SELECT ip FROM ip")
            allowed_ips = [row[0] for row in self.cursor.fetchall()]
            return allowed_ips
        except pymysql.OperationalError:
            # 如果查询失败，返回空列表
            allowed_ips = []

class TokenRepository:
    """Token相关的数据库操作类"""
    
    @staticmethod
    def add_token(token: str, use_times: int, center_id: str) -> int:
        """
        添加新token
        
        Args:
            token: token字符串
            use_times: 可使用次数
            center_id: 中心ID
            
        Returns:
            新创建的token ID
            
        Raises:
            ValueError: 当token已存在时抛出
        """
        try:
            with db_session.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tokens (token, use_times, center_id) VALUES (%s, %s, %s)",
                    (token, use_times, center_id)
                )
                return cursor.lastrowid
        except pymysql.IntegrityError:
            raise ValueError("Token已存在")

    @staticmethod
    def token_exists(token: str) -> bool:
        """
        检查token是否存在
        
        Args:
            token: 要检查的token
            
        Returns:
            token是否存在
        """
        with db_session.get_cursor() as cursor:
            cursor.execute("SELECT token FROM tokens WHERE token=%s", (token,))
            return bool(cursor.fetchone())

    @staticmethod
    def get_token_info(token: str) -> Optional[Dict[str, Any]]:
        """
        获取token信息
        
        Args:
            token: token字符串
            
        Returns:
            token信息字典，如果不存在则返回None
        """
        with db_session.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, token, use_times, center_id FROM tokens WHERE token=%s",
                (token,)
            )
            return cursor.fetchone()

    @staticmethod
    def update_token_usage(token: str) -> bool:
        """
        更新token使用次数（减1）
        
        Args:
            token: 要更新的token
            
        Returns:
            更新是否成功
        """
        with db_session.get_cursor() as cursor:
            cursor.execute(
                "UPDATE tokens SET use_times = use_times - 1 WHERE token=%s AND use_times > 0",
                (token,)
            )
            return cursor.rowcount > 0

class CenterRepository:
    """中心相关的数据库操作类"""
    
    @staticmethod
    def center_exists(center_id: str) -> bool:
        """
        检查中心ID是否存在
        
        Args:
            center_id: 要检查的中心ID
            
        Returns:
            中心ID是否存在
        """
        with db_session.get_cursor() as cursor:
            cursor.execute("SELECT center_id FROM centers WHERE center_id=%s", (center_id,))
            return bool(cursor.fetchone())

    @staticmethod
    def add_center(center_id: str) -> bool:
        """
        添加新的中心
        
        Args:
            center_id: 中心ID
            
        Returns:
            添加是否成功
        """
        try:
            with db_session.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO centers (center_id) VALUES (%s)",
                    (center_id,)
                )
                return True
        except pymysql.IntegrityError:
            return False

class IPRepository:
    """IP白名单相关的数据库操作类"""
    
    @staticmethod
    def get_allowed_ips() -> List[str]:
        """
        获取允许的IP列表
        
        Returns:
            允许的IP地址列表
        """
        try:
            with db_session.get_cursor() as cursor:
                cursor.execute("SELECT ip FROM ip")
                results = cursor.fetchall()
                return [row['ip'] for row in results]
        except pymysql.OperationalError:
            return []