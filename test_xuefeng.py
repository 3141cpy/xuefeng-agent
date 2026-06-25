#!/usr/bin/env python3
import paramiko
import sys
import time

HOST = "64.83.13.183"
PORT = 22
USER = "root"
PASSWORD = "tnraWNCP3850"

# Commands to run on the remote server
COMMANDS = [
    ("== [1] Direct SSH test - connection status ==", "echo SSH_OK && hostname && uname -a"),

    ("== [2] Check service is listening on 8765 ==", "ss -tlnp 2>/dev/null | grep -E '8765|server.py' || netstat -tlnp 2>/dev/null | grep 8765"),

    ("== [3] Find server.py location ==", "ls -la /root/xuefeng-agent/ 2>/dev/null | head -30"),

    ("== [4] grep tavily in server.py ==", "grep -n -i tavily /root/xuefeng-agent/server.py 2>/dev/null || echo 'NOT FOUND at /root/xuefeng-agent/server.py'"),

    ("== [5] DB search test - 北京大学 2023 ==", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"北京大学 2023 录取分数线"}'"""),

    ("== [6] DB search test - 清华大学 ==", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"清华大学 计算机 2022"}'"""),

    ("== [7] DB search test - 浙江大学 ==", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"浙江大学"}'"""),

    ("== [8] Check endpoints / routes in server.py ==", "grep -n -E 'app\\.(get|post|route|add_route)|@app\\.|FastAPI\\(|def .*\\(.*request' /root/xuefeng-agent/server.py 2>/dev/null | head -50"),

    ("== [9] Find Tavily usage context (broader) ==", "grep -n -i -E 'tavily|TAVILY|web_search|web search' /root/xuefeng-agent/server.py 2>/dev/null"),

    ("== [10] Tavily API key env check ==", "grep -n -i -E 'TAVILY_API_KEY|tavily_api_key' /root/xuefeng-agent/server.py 2>/dev/null; echo '---env---'; env | grep -i tavily 2>/dev/null || echo 'no tavily env in current shell'"),

    ("== [11] Chat test with search query (deepseek-chat) ==", """curl -s -X POST http://localhost:8765/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"搜索一下2024年高考最新政策"}],"model":"deepseek-chat"}' --max-time 90"""),
]

def run_via_direct(client, cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out, err

def main():
    direct_ok = False
    client = None
    # Try direct SSH
    try:
        print(">> Trying direct SSH connection to %s:%s ..." % (HOST, PORT), flush=True)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=20, banner_timeout=20, auth_timeout=20)
        print(">> Direct SSH connected.", flush=True)
        direct_ok = True
    except Exception as e:
        print(">> Direct SSH failed: %r" % e, flush=True)
        client = None

    # Try HTTP proxy CONNECT via socat if direct failed
    used_proxy = False
    if not direct_ok:
        print(">> Trying HTTP proxy CONNECT via socat (127.0.0.1:18080)...", flush=True)
        # socat creates a local forwarding; we use ProxyCommand via paramiko
        # First check if socat exists / proxy reachable
        import socket
        try:
            s = socket.create_connection(("127.0.0.1", 18080), timeout=5)
            s.close()
            proxy_available = True
        except Exception as pe:
            print(">> Proxy 127.0.0.1:18080 not reachable: %r" % pe, flush=True)
            proxy_available = False

        if proxy_available:
            proxy_cmd = "socat - PROXY:127.0.0.1:%s:%s,proxyport=18080" % (HOST, PORT)
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                sock = paramiko.ProxyCommand(proxy_cmd)
                client.connect(HOST, port=PORT, username=USER, password=PASSWORD, sock=sock, timeout=30, banner_timeout=30, auth_timeout=30)
                print(">> SSH via proxy connected.", flush=True)
                used_proxy = True
            except Exception as e:
                print(">> Proxy SSH failed: %r" % e, flush=True)
                client = None

    if client is None:
        print("!! Could not establish SSH connection (neither direct nor proxy). Aborting.", flush=True)
        sys.exit(1)

    # Run commands
    for title, cmd in COMMANDS:
        print("\n" + "=" * 70, flush=True)
        print(title, flush=True)
        print("=" * 70, flush=True)
        try:
            out, err = run_via_direct(client, cmd, timeout=120)
            if out:
                print("STDOUT:\n" + out, flush=True)
            if err:
                print("STDERR:\n" + err, flush=True)
            if not out and not err:
                print("(no output)", flush=True)
        except Exception as e:
            print("!! Command failed: %r" % e, flush=True)

    # Separate handling for log checks with possibly long output
    log_cmds = [
        ("== [L1] List log files ==", "ls -la /root/xuefeng-agent/*.log 2>/dev/null; echo '---nohup---'; ls -la /root/xuefeng-agent/nohup.out 2>/dev/null; echo '---all-files---'; ls -la /root/xuefeng-agent/ 2>/dev/null | head -40"),
        ("== [L2] tail nohup.out ==", "tail -80 /root/xuefeng-agent/nohup.out 2>/dev/null || echo 'no nohup.out'"),
        ("== [L3] find recent log files ==", "find /root/xuefeng-agent -maxdepth 2 -name '*.log' -o -name 'nohup*' 2>/dev/null | head -20"),
        ("== [L4] grep tavily/db errors in nohup.out ==", "grep -i -E 'tavily|sqlite|database|error|traceback|exception' /root/xuefeng-agent/nohup.out 2>/dev/null | tail -60 || echo 'no matches / no file'"),
    ]
    for title, cmd in log_cmds:
        print("\n" + "=" * 70, flush=True)
        print(title, flush=True)
        print("=" * 70, flush=True)
        try:
            out, err = run_via_direct(client, cmd, timeout=60)
            if out:
                print("STDOUT:\n" + out, flush=True)
            if err:
                print("STDERR:\n" + err, flush=True)
            if not out and not err:
                print("(no output)", flush=True)
        except Exception as e:
            print("!! Command failed: %r" % e, flush=True)

    # Also pull the relevant server.py sections: Tavily + DB handlers
    print("\n" + "=" * 70, flush=True)
    print("== [CODE] Dump server.py Tavily + DB sections ==", flush=True)
    print("=" * 70, flush=True)
    # Get line count and content around tavily & search/sqlite/db
    code_cmd = """
echo "### total lines ###";
wc -l /root/xuefeng-agent/server.py;
echo "### tavily lines ###";
grep -n -i tavily /root/xuefeng-agent/server.py;
echo "### sqlite/db/search lines ###";
grep -n -i -E 'sqlite3|connect\\(|admission|/api/search|def search|/api/chat|def chat' /root/xuefeng-agent/server.py;
"""
    out, err = run_via_direct(client, code_cmd, timeout=60)
    if out:
        print(out, flush=True)
    if err:
        print("STDERR:", err, flush=True)

    client.close()
    print("\n>> Done.", flush=True)

if __name__ == "__main__":
    main()
