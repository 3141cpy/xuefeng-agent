# 部署雪峰Agent到远程美国云服务器 Spec

## Why
用户希望将雪峰Agent部署到自己的2H2G美国云服务器（64.83.13.183），让其他人可以通过公网访问使用。服务器上已有其他运行中的任务，必须确保不影响现有服务。

## What Changes
- SSH连接远程服务器，检查当前资源占用和运行中的服务
- 上传项目文件到远程服务器
- 在远程服务器上启动server.py
- 配置进程守护（确保服务持续运行）
- 验证公网可访问

## Impact
- Affected code: 无代码修改，仅部署操作
- 远程服务器: 64.83.13.183（root用户，SSH密码登录）
- 端口: 8765（需确认不与现有服务冲突）

## ADDED Requirements
### Requirement: 安全检查优先
系统 SHALL 在部署前先检查远程服务器的资源占用和运行中的服务，确认不会影响现有任务。

#### Scenario: 服务器资源不足
- **WHEN** 服务器内存占用>85%或CPU持续>80%
- **THEN** 暂停部署，报告给用户，等待用户决策

#### Scenario: 端口冲突
- **WHEN** 8765端口已被占用
- **THEN** 换用其他可用端口

### Requirement: 远程部署
系统 SHALL 将雪峰Agent完整部署到远程服务器，并通过公网IP可访问。

#### Scenario: 部署成功
- **WHEN** 完成文件上传和服务启动
- **THEN** 通过 http://64.83.13.183:8765 可访问雪峰Agent界面

### Requirement: 进程守护
系统 SHALL 使用nohup或systemd确保server.py在后台持续运行，SSH断开后不退出。

### Requirement: 不影响现有服务
系统 SHALL 仅占用必要资源，不修改、不停止服务器上已有的任何服务。
