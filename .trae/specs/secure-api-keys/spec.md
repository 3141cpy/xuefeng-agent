# API Key 安全加固 Spec

## Why
当前 DeepSeek API Key 和 Tavily Key 直接嵌入前端 JavaScript 代码中，任何人查看网页源码即可获取，存在严重安全风险。需要将 API 调用移至服务端，Key 仅存储在服务器本地。

## What Changes
- 在服务端新增 `/api/chat` 代理端点，前端不再直接调用 DeepSeek API
- 在服务端新增 `/api/search` 代理端点，前端不再直接调用 Tavily API
- API Key 存储在服务器端配置文件中，**BREAKING** 前端不再能自定义 API Key
- 移除前端所有 Key 相关的 UI（API设置弹窗、localStorage 存储）
- 前端改为调用本地 `/api/chat` 和 `/api/search` 端点

## Impact
- Affected code: server.py（主要修改）
- Affected specs: deploy-to-remote-server
- 用户体验变化：用户不再需要配置 API Key，打开即用；但也不能用自己的 Key 了

## ADDED Requirements
### Requirement: 服务端代理 API 调用
系统 SHALL 在服务端代理所有外部 API 调用（DeepSeek 和 Tavily），API Key 仅存储在服务器本地文件中，不暴露给前端。

#### Scenario: 前端发送聊天请求
- **WHEN** 前端向 `/api/chat` 发送 POST 请求（包含 messages 数组）
- **THEN** 服务端使用存储的 DeepSeek Key 调用 DeepSeek API，返回结果给前端
- **AND** 响应中不包含任何 API Key 信息

#### Scenario: 前端发送搜索请求
- **WHEN** 前端向 `/api/search` 发送 POST 请求（包含 query）
- **THEN** 服务端使用存储的 Tavily Key 调用 Tavily API，返回结果给前端

#### Scenario: API Key 文件不存在
- **WHEN** 服务器启动时配置文件不存在
- **THEN** 服务正常启动但 API 功能返回错误提示

### Requirement: 前端不暴露 Key
系统 SHALL 确保前端 HTML/JS 代码中不包含任何 API Key，也无法通过浏览器开发者工具获取 Key。

#### Scenario: 查看网页源码
- **WHEN** 用户查看网页源码或 Network 请求
- **THEN** 无法找到任何 API Key 字符串

## MODIFIED Requirements
### Requirement: API 设置 UI
移除 API 设置弹窗，因为 Key 由服务端管理，用户无需配置。前端简化为纯聊天界面。

## REMOVED Requirements
### Requirement: 前端自定义 API Key
**Reason**: 安全风险，Key 暴露在前端
**Migration**: Key 改为服务端配置文件管理
