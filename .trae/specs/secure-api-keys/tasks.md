# Tasks
- [x] Task 1: 修改 server.py — 在服务端新增 /api/chat 代理端点（接收 messages，调用 DeepSeek API，返回结果）
- [x] Task 2: 修改 server.py — 在服务端新增 /api/search 代理端点（接收 query，调用 Tavily API，返回结果）
- [x] Task 3: 修改 server.py — 新增服务端配置文件读取逻辑（从 config.json 读取 API Key）
- [x] Task 4: 修改 server.py 前端 JS — 将 fetch DeepSeek API 改为 fetch /api/chat，将 fetch Tavily API 改为 fetch /api/search
- [x] Task 5: 修改 server.py 前端 JS — 移除 API 设置弹窗、localStorage Key 存储、getCfg 函数中的 Key 默认值
- [x] Task 6: 在远程服务器创建 config.json 配置文件（含 DeepSeek Key 和 Tavily Key）
- [x] Task 7: 将修改后的 server.py 上传到远程服务器，重启服务
- [x] Task 8: 实际测试 — 验证网页源码无 Key 泄露，验证聊天和搜索功能正常

# Task Dependencies
- Task 1, 2, 3 可并行
- Task 4, 5 depends on Task 1, 2, 3
- Task 7 depends on Task 4, 5, 6
- Task 8 depends on Task 7
