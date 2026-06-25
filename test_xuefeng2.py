#!/usr/bin/env python3
import paramiko
import sys

HOST = "64.83.13.183"
PORT = 22
USER = "root"
PASSWORD = "tnraWNCP3850"

def connect():
    # Direct failed before, use proxy
    proxy_cmd = "socat - PROXY:127.0.0.1:%s:%s,proxyport=18080" % (HOST, PORT)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sock = paramiko.ProxyCommand(proxy_cmd)
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, sock=sock, timeout=30, banner_timeout=30, auth_timeout=30)
    return client

def run(client, cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")

def main():
    client = connect()
    print(">> Connected via proxy.\n", flush=True)

    # Dump server.py key sections using sed -n (line ranges)
    sections = [
        ("== Section A: imports + config (lines 1-60) ==", "sed -n '1,60p' /root/xuefeng-agent/server.py"),
        ("== Section B: Tavily handler + /api/search routing (lines 60-140) ==", "sed -n '60,140p' /root/xuefeng-agent/server.py"),
        ("== Section C: /api/chat handler (lines 82-110) + DB search logic (lines 140-240) ==", "sed -n '140,240p' /root/xuefeng-agent/server.py"),
        ("== Section D: rest of search/chat (lines 240-330) ==", "sed -n '240,330p' /root/xuefeng-agent/server.py"),
        ("== Section E: config.json contents (mask key) ==", "python3 -c \"import json; c=json.load(open('/root/xuefeng-agent/config.json')); print({k:(v[:8]+'...[MASKED]' if 'key' in k.lower() and isinstance(v,str) and len(v)>8 else v) for k,v in c.items()})\" 2>/dev/null || cat /root/xuefeng-agent/config.json | python3 -c \"import sys,json; c=json.load(sys.stdin); print({k:(str(v)[:8]+'...[MASKED]' if 'key' in k.lower() else v) for k,v in c.items()})\""),
    ]
    for title, cmd in sections:
        print("\n" + "=" * 70, flush=True)
        print(title, flush=True)
        print("=" * 70, flush=True)
        out, err = run(client, cmd, timeout=60)
        if out:
            print(out, flush=True)
        if err:
            print("STDERR:", err, flush=True)

    # Now test the SQLite database DIRECTLY to confirm it works (bypass /api/search)
    print("\n" + "=" * 70, flush=True)
    print("== Direct SQLite DB test (query admission_clean.db) ==", flush=True)
    print("=" * 70, flush=True)
    db_cmd = """python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('/root/xuefeng-agent/admission_clean.db')
cur = conn.cursor()
# show schema
print("--- tables ---")
for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(r)
print("--- schema of admission ---")
for r in cur.execute("PRAGMA table_info(admission)"):
    print(r)
print("--- row count ---")
print(cur.execute("SELECT COUNT(*) FROM admission").fetchone())
print("--- sample: 北京大学 rows ---")
for r in cur.execute("SELECT province,year,school_name,major_name,score,rank FROM admission WHERE school_name LIKE '%北京大学%' ORDER BY year DESC LIMIT 10"):
    print(r)
print("--- sample: 清华大学 2022 ---")
for r in cur.execute("SELECT province,year,school_name,major_name,score,rank FROM admission WHERE school_name LIKE '%清华大学%' AND year=2022 LIMIT 10"):
    print(r)
print("--- sample: 浙江大学 ---")
for r in cur.execute("SELECT province,year,school_name,major_name,score,rank FROM admission WHERE school_name LIKE '%浙江大学%' LIMIT 10"):
    print(r)
conn.close()
PYEOF"""
    out, err = run(client, db_cmd, timeout=60)
    if out:
        print(out, flush=True)
    if err:
        print("STDERR:", err, flush=True)

    # Now test /api/search with different param shapes to find the DB path
    print("\n" + "=" * 70, flush=True)
    print("== /api/search variant tests (find DB-triggering params) ==", flush=True)
    print("=" * 70, flush=True)
    variants = [
        ("variant-1: with score=680", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"北京大学","score":680,"province":"北京"}'"""),
        ("variant-2: rank-based", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":"北京大学","rank":1000,"province":"北京"}'"""),
        ("variant-3: empty query", """curl -s -X POST http://localhost:8765/api/search -H "Content-Type: application/json" -d '{"query":""}'"""),
    ]
    for title, cmd in variants:
        print("\n--- %s ---" % title, flush=True)
        out, err = run(client, cmd, timeout=60)
        if out:
            print(out[:2000], flush=True)
        if err:
            print("STDERR:", err[:500], flush=True)

    # Check server.log content (was 0 bytes, but check again) and check the process
    print("\n" + "=" * 70, flush=True)
    print("== Process + log inspection ==", flush=True)
    print("=" * 70, flush=True)
    proc_cmd = """echo '--- ps ---'; ps aux | grep -E 'server.py|python3' | grep -v grep; echo '--- server.log size ---'; ls -la /root/xuefeng-agent/server.log; echo '--- server.log content (first 100 lines) ---'; head -100 /root/xuefeng-agent/server.log; echo '--- systemd? ---'; systemctl list-units --type=service 2>/dev/null | grep -i xuefeng || echo 'not a systemd service'; echo '--- how was it started (check cmdline of pid) ---'; cat /proc/$(pgrep -f 'server.py' | head -1)/cmdline 2>/dev/null | tr '\\0' ' '; echo; echo '--- check stderr redirect ---'; ls -la /proc/$(pgrep -f 'server.py' | head -1)/fd/ 2>/dev/null | head -10"""
    out, err = run(client, proc_cmd, timeout=60)
    if out:
        print(out, flush=True)
    if err:
        print("STDERR:", err, flush=True)

    # Live error capture: tail the server's stdout/stderr by checking fd
    # Actually do a fresh chat call and look for any newly-logged errors
    print("\n" + "=" * 70, flush=True)
    print("== Re-test chat & search, capture timing/errors ==", flush=True)
    print("=" * 70, flush=True)
    chat_cmd = """curl -s -X POST http://localhost:8765/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"你好，用一句话介绍你自己"}],"model":"deepseek-chat"}' --max-time 60 | head -c 800"""
    out, err = run(client, chat_cmd, timeout=90)
    print("CHAT RESPONSE:", out, flush=True)
    if err:
        print("CHAT STDERR:", err, flush=True)

    client.close()
    print("\n>> Done.", flush=True)

if __name__ == "__main__":
    main()
