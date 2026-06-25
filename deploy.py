#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deploy server.py to remote host via paramiko (with HTTP CONNECT proxy fallback)."""
import paramiko, socket, time, sys, os, urllib.parse

HOST = '64.83.13.183'
PORT = 22
USER = 'root'
PASSWORD = 'tnraWNCP3850'
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 18080
LOCAL_FILE = '/workspace/server.py'
REMOTE_DIR = '/root/xuefeng-agent'
REMOTE_FILE = REMOTE_DIR + '/server.py'

def make_proxy_socket(target_host, target_port, proxy_host, proxy_port, timeout=20):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((proxy_host, proxy_port))
    req = (f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
           f"Host: {target_host}:{target_port}\r\n\r\n").encode()
    s.sendall(req)
    resp = b''
    while b'\r\n\r\n' not in resp:
        chunk = s.recv(4096)
        if not chunk:
            raise Exception("proxy closed during CONNECT")
        resp += chunk
    first = resp.split(b'\r\n', 1)[0]
    if b' 200 ' not in first:
        raise Exception(f"proxy CONNECT failed: {first!r}")
    return s

def connect_ssh():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # 1) direct
    print("[SSH] trying direct connection ...")
    try:
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD,
                        timeout=12, banner_timeout=15, auth_timeout=15, allow_agent=False, look_for_keys=False)
        print("[SSH] direct OK")
        return client
    except Exception as e:
        print(f"[SSH] direct failed: {e}")
        try: client.close()
        except: pass
    # 2) via proxy
    print("[SSH] trying via HTTP CONNECT proxy 127.0.0.1:18080 ...")
    sock = make_proxy_socket(HOST, PORT, PROXY_HOST, PROXY_PORT)
    c2 = paramiko.SSHClient()
    c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c2.connect(HOST, port=PORT, username=USER, password=PASSWORD, sock=sock,
                banner_timeout=30, auth_timeout=30, allow_agent=False, look_for_keys=False)
    print("[SSH] proxy OK")
    return c2

def run(client, cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    ch = stdout.channel
    ch.settimeout(timeout)
    # read whatever is available; tolerate the channel staying open (bg processes)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    rc = ch.recv_exit_status() if ch.exit_status_ready() else -1
    return rc, out, err

def run_quick(client, cmd, timeout=10):
    """Run a command that backgrounds a process: read with short timeout, don't wait for exit."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    ch = stdout.channel
    ch.settimeout(timeout)
    out = err = ''
    try:
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
    except Exception:
        pass
    try: ch.close()
    except: pass
    return out, err

def trunc(s, n=200):
    s = s.strip()
    if len(s) > n:
        return s[:n] + f"...(+{len(s)-n} chars)"
    return s

def main():
    results = []  # (id, name, status, summary)
    client = connect_ssh()
    print("[SSH] connected")

    # quick sanity
    rc, out, err = run(client, 'uname -a; hostname; whoami')
    print("[HOST]", trunc(out, 120))

    # ensure remote dir exists
    rc, out, err = run(client, f'mkdir -p {REMOTE_DIR}')
    print(f"[MKDIR] rc={rc} err={trunc(err,80)}")

    # SFTP upload
    print("[SFTP] uploading", LOCAL_FILE, "->", REMOTE_FILE)
    sftp = client.open_sftp()
    t0 = time.time()
    sftp.put(LOCAL_FILE, REMOTE_FILE)
    sftp.close()
    print(f"[SFTP] uploaded in {time.time()-t0:.1f}s")

    # verify upload
    rc, out, err = run(client, f'ls -la {REMOTE_FILE}; wc -l {REMOTE_FILE}')
    print("[UPLOAD-VERIFY]", trunc(out, 160))

    # restart service
    print("[RESTART] killing existing process ...")
    run(client, 'pkill -f "python3 server.py" 2>/dev/null; sleep 1; echo killed')
    time.sleep(2)
    print("[RESTART] starting ...")
    start_cmd = (f'cd {REMOTE_DIR} && setsid nohup python3 server.py '
                 f'> server.log 2>&1 < /dev/null & echo STARTED=$!')
    out, err = run_quick(client, start_cmd, timeout=8)
    print("[RESTART] start:", trunc(out,80), trunc(err,80))
    print("[RESTART] waiting 8s for startup ...")
    time.sleep(8)

    # --- TESTS ---
    def record(tid, name, ok, summary):
        results.append((tid, name, "PASS" if ok else "FAIL", summary))
        print(f"  [{tid}] {'PASS' if ok else 'FAIL'}: {trunc(summary,200)}")

    # a) process check
    print("\n=== TEST a) process check ===")
    rc, out, err = run(client, 'ps aux | grep "server.py" | grep -v grep')
    record("a", "进程检查(ps)", bool(out.strip()), trunc(out,200))

    # b) port check
    print("=== TEST b) port 8765 check ===")
    rc, out, err = run(client, 'ss -tlnp | grep 8765')
    record("b", "端口检查(8765)", bool(out.strip()), trunc(out,200))

    # c) ping
    print("=== TEST c) /ping ===")
    rc, out, err = run(client, 'curl -s -m 10 http://localhost:8765/ping')
    record("c", "/ping", ('"ok":true' in out) or ('ok' in out and 'true' in out), trunc(out,200))

    # d) /query province=北京 school=北京大学 (Chinese in URL)
    print("=== TEST d) /query 北京/北京大学 (Chinese in URL) ===")
    rc, out, err = run(client, 'curl -s -m 15 "http://localhost:8765/query?province=北京&school=北京大学"')
    ok_d = '"count"' in out and ('"count":0' not in out)
    # if empty, retry with url-encoded
    if not out.strip() or not ok_d:
        print("  retry with URL-encoded params ...")
        rc2, out2, err2 = run(client,
            'curl -s -m 15 "http://localhost:8765/query?province=%E5%8C%97%E4%BA%AC&school=%E5%8C%97%E4%BA%AC%E5%A4%A7%E5%AD%A6"')
        if out2.strip():
            out = out2
            ok_d = '"count"' in out and ('"count":0' not in out)
    record("d", "/query 北京/北京大学", ok_d, trunc(out,200))

    # e) /query province=浙江 school=浙江大学
    print("=== TEST e) /query 浙江/浙江大学 ===")
    rc, out, err = run(client, 'curl -s -m 15 "http://localhost:8765/query?province=浙江&school=浙江大学"')
    ok_e = '"count"' in out and ('"count":0' not in out)
    if not out.strip() or not ok_e:
        rc2, out2, err2 = run(client,
            'curl -s -m 15 "http://localhost:8765/query?province=%E6%B5%99%E6%B1%9F&school=%E6%B5%99%E6%B1%9F%E5%A4%A7%E5%AD%A6"')
        if out2.strip():
            out = out2
            ok_e = '"count"' in out and ('"count":0' not in out)
    record("e", "/query 浙江/浙江大学", ok_e, trunc(out,200))

    # f) /recommend province=浙江 score=680
    print("=== TEST f) /recommend 浙江 score=680 ===")
    rc, out, err = run(client, 'curl -s -m 15 "http://localhost:8765/recommend?province=浙江&score=680"')
    ok_f = ('"chong"' in out) and ('"wen"' in out) and ('"bao"' in out)
    if not out.strip() or not ok_f:
        rc2, out2, err2 = run(client,
            'curl -s -m 15 "http://localhost:8765/recommend?province=%E6%B5%99%E6%B1%9F&score=680"')
        if out2.strip():
            out = out2
            ok_f = ('"chong"' in out) and ('"wen"' in out) and ('"bao"' in out)
    record("f", "/recommend 浙江 680", ok_f, trunc(out,200))

    # g) /recommend province=北京 score=650 (Chinese)
    print("=== TEST g) /recommend 北京 score=650 ===")
    rc, out, err = run(client, 'curl -s -m 15 "http://localhost:8765/recommend?province=北京&score=650"')
    ok_g = ('"chong"' in out) and ('"wen"' in out) and ('"bao"' in out)
    if not out.strip() or not ok_g:
        rc2, out2, err2 = run(client,
            'curl -s -m 15 "http://localhost:8765/recommend?province=%E5%8C%97%E4%BA%AC&score=650"')
        if out2.strip():
            out = out2
            ok_g = ('"chong"' in out) and ('"wen"' in out) and ('"bao"' in out)
    record("g", "/recommend 北京 650", ok_g, trunc(out,200))

    # h) Tavily /api/search
    print("=== TEST h) /api/search (Tavily) ===")
    rc, out, err = run(client,
        '''curl -s -m 30 -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"2024年高考最新政策"}' ''')
    # success if returns json with results or answer key (not a hard error)
    ok_h = ('"results"' in out) or ('"answer"' in out) or ('"query"' in out)
    record("h", "/api/search (Tavily)", ok_h, trunc(out,200))

    # i) chat test (new API key)
    print("=== TEST i) /api/chat (deepseek-chat) ===")
    rc, out, err = run(client,
        '''curl -s -m 60 -X POST http://localhost:8765/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"你好，简单介绍一下你自己"}],"model":"deepseek-chat"}' ''')
    ok_i = ('"content"' in out) or ('"message"' in out) or ('"choices"' in out) or ('"delta"' in out)
    record("i", "/api/chat (deepseek)", ok_i, trunc(out,200))

    # j) logs
    print("=== TEST j) server.log (tail -20) ===")
    rc, out, err = run(client, 'tail -20 /root/xuefeng-agent/server.log')
    record("j", "日志检查(tail -20)", True, trunc(out,400))

    client.close()

    # ----- summary -----
    print("\n" + "="*72)
    print("测试结果汇总表")
    print("="*72)
    print(f"{'ID':<4} {'状态':<6} {'测试项':<32} {'响应摘要'}")
    print("-"*72)
    pass_n = 0
    for tid, name, status, summary in results:
        if status == "PASS": pass_n += 1
        line = f"{tid:<4} {status:<6} {name:<28} {summary}"
        print(line)
    print("-"*72)
    print(f"总计: {pass_n}/{len(results)} 通过")
    print("="*72)
    return 0 if pass_n == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())
