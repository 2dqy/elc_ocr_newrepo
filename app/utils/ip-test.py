import requests
import json
import sys
import argparse
import socket
import netifaces

def get_local_ips():
    """获取本地所有网络接口的 IP 地址"""
    interfaces = netifaces.interfaces()
    ip_list = []
    for iface in interfaces:
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip_list.append(addr['addr'])
    return ip_list

def send_post_request(url, data, headers=None, proxy=None, timeout=10):
    """发送 POST 请求，支持代理"""
    try:
        # 默认 headers，基于你的 curl 命令
        default_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0"
        }
        if headers:
            default_headers.update(headers)

        # 发送 POST 请求
        response = requests.post(
            url,
            data=json.dumps(data),
            headers=default_headers,
            proxies=proxy,
            timeout=timeout
        )
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"

def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="Send POST request with customizable IP or proxy")
    parser.add_argument("--url", default="http://127.0.0.1:8000/upload/add_token", help="Target URL")
    parser.add_argument("--proxy", help="Proxy URL (e.g., http://proxy:port)")
    parser.add_argument("--interface", help="Network interface to bind (e.g., eth0)")
    args = parser.parse_args()

    # 请求数据，基于你的 curl 命令
    data = {
        "token": "bobtest",
        "use_times": 100,
        "center_id": "TMDHC"
    }

    # 显示本地 IP 地址
    print("Available local IP addresses:")
    for ip in get_local_ips():
        print(f"  - {ip}")

    # 如果指定了代理
    proxies = None
    if args.proxy:
        proxies = {
            "http": args.proxy,
            "https": args.proxy
        }
        print(f"Using proxy: {args.proxy}")

    # 如果指定了网络接口（需要 root 权限或特定配置）
    if args.interface:
        print(f"Binding to interface: {args.interface}")
        print("Note: Binding to a specific interface requires root privileges or custom socket configuration.")
        # 以下代码需要特殊权限，可能不适用于所有环境
        # 你可以手动切换网络接口或使用代理
        print("Consider using --proxy instead or running on a machine with the desired IP.")

    # 发送请求
    status_code, response_text = send_post_request(
        url=args.url,
        data=data,
        proxy=proxies
    )

    # 输出结果
    if status_code:
        print(f"Status Code: {status_code}")
        print(f"Response: {response_text}")
    else:
        print(f"Error: {response_text}")

if __name__ == "__main__":
    main()