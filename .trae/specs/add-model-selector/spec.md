# 前端模型选择功能 + Tavily 验证 Spec

## Why
当前模型硬编码为 `deepseek-chat`，用户无法切换。DeepSeek 提供多个模型（deepseek-chat、deepseek-reasoner 等），不同模型效果和成本不同，用户应能自主选择。同时需要验证 Tavily 联网搜索是否正常工作。

## What Changes
- 服务端 `/api/chat` 端点支持前端传入 `model` 参数，覆盖默认模型
- 服务端新增 `/api/models` 端点，返回可用模型列表（从 config.json 读取）
- 前端顶部栏新增模型选择下拉框，用户可切换模型
- 前端选择的模型通过 `/api/chat` 请求传给服务端
- config.json 新增 `models` 字段定义可选模型列表
- 验证 Tavily 搜索功能端到端正常

## Impact
- Affected code: server.py（服务端 + 前端 JS）
- Affected config: config.json 新增 models 字段

## ADDED Requirements
### Requirement: 前端模型选择
系统 SHALL 在前端顶部栏提供模型选择下拉框，用户可切换不同的 DeepSeek 模型。

#### Scenario: 用户切换模型
- **WHEN** 用户从下拉框选择一个模型
- **THEN** 后续聊天请求使用该模型，选择状态保存在 localStorage

#### Scenario: 默认模型
- **WHEN** 用户首次访问页面
- **THEN** 默认使用 config.json 中配置的默认模型

### Requirement: 服务端支持动态模型
系统 SHALL 在 /api/chat 端点接受前端传入的 model 参数。

#### Scenario: 前端指定模型
- **WHEN** /api/chat 请求包含 model 字段
- **THEN** 使用该模型调用 API（需在允许列表内）

#### Scenario: 前端未指定模型
- **WHEN** /api/chat 请求不包含 model 字段
- **THEN** 使用 config.json 中的默认模型

### Requirement: 可用模型列表
系统 SHALL 通过 /api/models 端点返回可用模型列表，前端据此渲染下拉框。

### Requirement: Tavily 搜索正常
系统 SHALL 确保 Tavily 联网搜索功能端到端正常工作。
