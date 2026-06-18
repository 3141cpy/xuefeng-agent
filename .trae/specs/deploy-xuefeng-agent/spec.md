# 部署雪峰Agent到本地 Spec

## Why
用户希望深入了解"雪峰Agent"项目并将其部署到本地，获得可直接访问的网页地址来使用该AI高考志愿顾问系统。

## What Changes
- 分析项目依赖和运行环境需求
- 安装必要的Python依赖
- 解压录取数据库（admission_clean.db.gz → admission_clean.db）
- 启动server.py Web服务器
- 验证服务可访问

## Impact
- Affected code: server.py（主程序，无需修改）
- 依赖: Python 3.10+, 无第三方依赖（server.py仅使用标准库）

## ADDED Requirements
### Requirement: 本地部署
系统 SHALL 在本地启动一个HTTP服务器，监听0.0.0.0:8765，提供雪峰Agent的完整Web界面。

#### Scenario: 部署成功
- **WHEN** 执行 `python server.py`
- **THEN** 服务器在8765端口启动，浏览器访问 http://localhost:8765 可看到完整聊天界面

#### Scenario: 数据库自动解压
- **WHEN** admission_clean.db不存在但admission_clean.db.gz存在
- **THEN** 首次启动时自动解压数据库文件
