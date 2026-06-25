#!/usr/bin/env python3
import paramiko

HOST = "64.83.13.183"; PORT = 22; USER = "root"; PASSWORD = "tnraWNCP3850"

def connect():
    proxy_cmd = "socat - PROXY:127.0.0.1:%s:%s,proxyport=18080" % (HOST, PORT)
    c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sock = paramiko.ProxyCommand(proxy_cmd)
    c.connect(HOST, port=PORT, username=USER, password=PASSWORD, sock=sock, timeout=30, banner_timeout=30, auth_timeout=30)
    return c

def run(c, cmd, t=90):
    _, out, err = c.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8","replace"), err.read().decode("utf-8","replace")

c = connect()
print(">> Connected via proxy.\n", flush=True)

tests = [
    ("== GET /ping (db health) ==", "curl -s http://localhost:8765/ping"),
    ("== GET /api/models ==", "curl -s http://localhost:8765/api/models"),
    ("== GET /query?province=北京&school=北京大学 (DB query) ==", """curl -s 'http://localhost:8765/query?province=%E5%8C%97%E4%BA%AC&school=%E5%8C%97%E4%BA%AC%E5%A4%A7%E5%AD%A6'"""),
    ("== GET /query?province=浙江&school=浙江大学 (DB query) ==", """curl -s 'http://localhost:8765/query?province=%E6%B5%99%E6%B1%9F&school=%E6%B5%99%E6%B1%9F%E5%A4%A7%E5%AD%A6'"""),
    ("== GET /recommend?province=北京&rank=2000&keyword=计算机 (冲稳保 DB) ==", """curl -s 'http://localhost:8765/recommend?province=%E5%8C%97%E4%BA%AC&rank=2000&keyword=%E8%AE%A1%E7%AE%97%E6%9C%BA'"""),
    ("== GET /recommend?province=浙江&score=680 (score-based DB) ==", """curl -s 'http://localhost:8765/recommend?province=%E6%B5%99%E6%B1%9F&score=680'"""),
    ("== POST /api/search tavily (concise, max_results=2) ==", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"2024高考政策","max_results":2}'"""),
    ("== GET /search?q=test (legacy web_search stub) ==", """curl -s 'http://localhost:8765/search?q=test'"""),
]
for title, cmd in tests:
    print("\n" + "="*70, flush=True); print(title, flush=True); print("="*70, flush=True)
    out, err = run(c, cmd)
    if out:
        # Truncate very long tavily output
        print(out[:2500] + ("\n...[TRUNCATED]" if len(out) > 2500 else ""), flush=True)
    if err:
        print("STDERR:", err[:500], flush=True)
    if not out and not err:
        print("(no output)", flush=True)

c.close()
print("\n>> Done.", flush=True)
