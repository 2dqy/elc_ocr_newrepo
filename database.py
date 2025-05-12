import pymysql



class Database:
    def __init__(self, db_name='ocr'):
        self.conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database=db_name,
            port=3306
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
        except mysql.connector.IntegrityError:
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
        except mysql.connector.IntegrityError:
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