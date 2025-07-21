import os
import smtplib
import asyncio
import threading
from email.mime.text import MIMEText
from email.header import Header
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量获取邮件配置
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.163.com")          # SMTP服务器地址
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))              # SSL端口通常是465
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "bmy_share@163.com") # 邮箱账号
EMAIL_FROM = os.getenv("EMAIL_FROM", "bmy_share@163.com")     # 发件人地址
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD") # 授权码

# 默认主题和内容
DEFAULT_SUBJECT = os.getenv("EMAIL_SUBJECT", "elc_ocr：gemini api error")
DEFAULT_CONTENT = ""

# 收件人列表
EMAIL_TO = os.getenv("EMAIL_TO").split(",")

def send_email(subject=DEFAULT_SUBJECT, content=DEFAULT_CONTENT, recipients=None):
    """同步发送邮件"""
    if recipients is None:
        recipients = EMAIL_TO
    
    # 检查邮箱配置是否完整
    if not EMAIL_HOST_PASSWORD:
        print("❌ 邮件发送失败: 缺少邮箱授权码，请在环境变量中设置EMAIL_HOST_PASSWORD")
        return False
        
    # 创建纯文本邮件对象
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header(EMAIL_FROM)
    msg['To'] = Header(', '.join(recipients))
    msg['Subject'] = Header(subject)

    try:
        # 使用SSL安全连接SMTP服务器，设置超时时间为10秒
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            # 登录邮箱
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            # 发送邮件
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
        print("✅ 邮件发送成功")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"❌ 邮件发送失败: 邮箱认证错误，请检查账号和授权码")
        return False
    except smtplib.SMTPConnectError:
        print(f"❌ 邮件发送失败: 无法连接到SMTP服务器")
        return False
    except smtplib.SMTPServerDisconnected:
        print(f"❌ 邮件发送失败: 服务器连接中断")
        return False
    except TimeoutError:
        print(f"❌ 邮件发送失败: 连接超时")
        return False
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def send_email_in_thread(subject=DEFAULT_SUBJECT, content=DEFAULT_CONTENT, recipients=None):
    """在新线程中发送邮件，不阻塞主线程"""
    try:
        # 创建一个新线程来发送邮件
        thread = threading.Thread(
            target=send_email,
            args=(subject, content, recipients)
        )
        thread.daemon = True  # 设置为守护线程，主程序退出时不会等待
        thread.start()
        return True
    except Exception as e:
        print(f"❌ 邮件线程创建失败: {e}")
        return False

async def send_email_async(subject=DEFAULT_SUBJECT, content=DEFAULT_CONTENT, recipients=None):
    """异步发送邮件"""
    # 直接使用线程方式发送，避免asyncio复杂性
    return send_email_in_thread(subject, content, recipients)

if __name__ == "__main__":
    send_email()