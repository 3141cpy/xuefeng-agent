import paramiko
import time
import socket
import os
from urllib.parse import urlparse

def try_connect_direct():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect('64.83.13.183', port=22, username='root', password='tnraWNCP3850', timeout=10)
        return client
    except Exception as e:
        print(f"直连失败: {e}")
        client.close()
        return None

def try_connect_via_proxy(proxy_host, proxy_port):
    print(f"尝试通过代理 {proxy_host}:{proxy_port} 连接...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((proxy_host, proxy_port))
        connect_request = f"CONNECT 64.83.13.183:22 HTTP/1.1\r\nHost: 64.83.13.183:22\r\n\r\n"
        sock.sendall(connect_request.encode())
        response = sock.recv(4096).decode()
        if '200' in response:
            print("代理隧道建立成功！")
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('64.83.13.183', port=22, username='root', password='tnraWNCP3850',
                          timeout=15, sock=sock)
            return client
        else:
            print(f"代理连接失败: {response}")
            sock.close()
            return None
    except Exception as e:
        print(f"代理连接异常: {e}")
        return None

# 连接
print("=== 尝试连接服务器 ===")
client = try_connect_direct()

if not client:
    # 使用环境变量代理
    http_proxy = os.environ.get('http_proxy', '') or os.environ.get('HTTP_PROXY', '')
    https_proxy = os.environ.get('https_proxy', '') or os.environ.get('HTTPS_PROXY', '')
    proxy_url = http_proxy or https_proxy
    if proxy_url:
        parsed = urlparse(proxy_url)
        proxy_host = parsed.hostname
        proxy_port = parsed.port
        if proxy_host and proxy_port:
            print(f"使用环境变量代理: {proxy_host}:{proxy_port}")
            client = try_connect_via_proxy(proxy_host, proxy_port)

if not client:
    print("❌ 所有连接方式均失败！")
    exit(1)

print("✅ SSH 连接成功！")

def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

def run_nohup(cmd):
    """执行 nohup 命令，不等待输出"""
    transport = client.get_transport()
    channel = transport.open_session()
    channel.exec_command(cmd)
    channel.close()

# 1. 检查 server.py 进程
print("\n=== 1. 检查 server.py 进程 ===")
out, err = run('ps aux | grep server.py | grep -v grep')
print(f"进程信息: {out if out.strip() else '未找到运行中的 server.py 进程'}")

# 2. 检查端口 8765
print("\n=== 2. 检查端口 8765 监听状态 ===")
out, err = run('ss -tlnp | grep 8765')
print(f"端口状态: {out if out.strip() else '端口 8765 未监听'}")

# 3. 检查 config.json
print("\n=== 3. 检查 config.json ===")
out, err = run('cat /root/xuefeng-agent/config.json')
print(f"配置内容:\n{out}")

expected_key = 'sk-975c579ce47c487e9acae2d55d2edc4a'
if expected_key in out:
    print(f"✅ api_key 已正确设置为 {expected_key}")
else:
    print(f"⚠️ api_key 未设置为预期值 {expected_key}")

# 4. 测试 ping
print("\n=== 4. 测试 /ping 接口 ===")
out, err = run('curl -s --max-time 10 http://localhost:8765/ping')
print(f"Ping 响应: {out if out.strip() else '无响应'}")
if err.strip():
    print(f"错误: {err}")

# 5. 如果服务不正常，重启
service_ok = out.strip() and 'ok' in out.lower()
if not service_ok:
    print("\n=== 5. 服务未正常响应，正在重启... ===")

    # 先查看日志
    print("查看最近日志...")
    out_log, err_log = run('tail -30 /root/xuefeng-agent/server.log 2>/dev/null || echo "无日志文件"')
    print(f"最近日志:\n{out_log}")

    print("杀死现有进程...")
    run('pkill -f "python3 server.py"')
    time.sleep(2)

    # 确认进程已停止
    out_check, _ = run('ps aux | grep server.py | grep -v grep')
    if out_check.strip():
        print(f"进程仍在运行: {out_check}")
        run('pkill -9 -f "python3 server.py"')
        time.sleep(1)

    print("启动服务...")
    run_nohup('cd /root/xuefeng-agent && nohup python3 server.py > server.log 2>&1 &')

    print("等待服务启动（15秒）...")
    time.sleep(15)

    # 再次检查进程
    out3, err3 = run('ps aux | grep server.py | grep -v grep')
    print(f"重启后进程: {out3 if out3.strip() else '未找到进程'}")

    # 再次检查端口
    out4, err4 = run('ss -tlnp | grep 8765')
    print(f"重启后端口: {out4 if out4.strip() else '端口未监听'}")

    # 再次测试 ping
    out5, err5 = run('curl -s --max-time 10 http://localhost:8765/ping')
    print(f"重启后 Ping 响应: {out5 if out5.strip() else '无响应'}")

    if out5.strip() and 'ok' in out5.lower():
        print("✅ 服务重启成功，已正常响应！")
    else:
        print("❌ 服务重启后仍无法正常响应")
        # 查看日志排查
        out_log2, _ = run('tail -50 /root/xuefeng-agent/server.log 2>/dev/null || echo "无日志"')
        print(f"启动日志:\n{out_log2}")
else:
    print("\n✅ 服务运行正常，无需重启！")

client.close()
print("\n=== 验证完成 ===")
