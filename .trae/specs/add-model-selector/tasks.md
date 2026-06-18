# Tasks
- [x] Task 1: 修改 server.py 服务端 — /api/chat 支持前端传入 model 参数（需在允许列表内），新增 /api/models 端点返回可用模型列表
- [x] Task 2: 修改 server.py 前端 JS — 顶部栏新增模型选择下拉框，选择状态存 localStorage，send() 时将选中模型传给 /api/chat
- [x] Task 3: 更新远程服务器 config.json — 新增 models 字段（deepseek-chat、deepseek-reasoner、deepseek-v4-flash、deepseek-v4-pro）
- [x] Task 4: 上传修改后的 server.py 和 config.json 到远程服务器，重启服务
- [x] Task 5: 实际测试 — 验证模型切换功能、Tavily 搜索功能、无 Key 泄露

# Task Dependencies
- Task 2 depends on Task 1
- Task 4 depends on Task 1, 2, 3
- Task 5 depends on Task 4
