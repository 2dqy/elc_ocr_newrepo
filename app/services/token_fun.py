from fastapi import HTTPException, Form
from app.models.database import Database
from fastapi.responses import FileResponse, JSONResponse


# 验证token

def verify_token(token: str = Form(...)):
    """验证用户的token是否有效，如果无效则抛出HTTPException"""
    try:
        # 使用Database类连接MySQL
        db = Database()

        # 查询token是否存在及其使用次数
        db.cursor.execute("SELECT use_times FROM tokens WHERE token=%s", (token,))
        print("token:", token)
        result = db.cursor.fetchone()
        print("result:", result)

        if not result:
            raise HTTPException(
                status_code=200,
                detail={
                    "errors": [{
                        "message": "TOKEN_NOT_FOUND",
                        "extensions": {
                            "code": "FORBIDDEN",
                        }
                    }]
                }
            )

        if result[0] <= 0:
            raise HTTPException(
                status_code=200,
                detail={
                    "errors": [{
                        "message": "TOKEN次數不夠",
                        "extensions": {
                            "code": "TOKEN_error",
                        }
                    }]
                }
            )
        
        return token
    except HTTPException:
        # 重新抛出HTTPException
        raise
    except Exception as e:
        print(f"Token验证错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "errors": [{
                    "message": "Token验证系统错误",
                    "extensions": {
                        "code": "INTERNAL_ERROR",
                    }
                }]
            }
        )

# 更新token使用次数
def update_token_usage(token: str):
    """更新token的使用次数"""
    try:
        # 使用Database类连接MySQL
        db = Database()

        # 更新使用次数
        db.cursor.execute("UPDATE tokens SET use_times = use_times - 1 WHERE token=%s", (token,))
        db.conn.commit()

        print(f"Token {token} 使用次数已更新")
    except Exception as e:
        print(f"更新Token使用次数错误: {str(e)}")


def get_ip_prefix(ip: str) -> str:
    """获取 IP 地址的前三位（a.b.c）"""
    parts = ip.split(".")
    if len(parts) != 4:
        return ""
    return ".".join(parts[:3])
