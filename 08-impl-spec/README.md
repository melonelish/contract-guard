# 实现规格说明书

> **本文档是写给 AI 编码 Agent 的。**
> Agent 拿到本文档 + 现有架构文档，应能直接写出可运行的代码，无需猜测。
>
> 填写原则：只写"是什么"，不写"为什么"。"为什么"已经在 01-07 目录的文档里了。

## 文档结构

| 文件 | 内容 | 对应架构文档 |
|------|------|------------|
| `START-HERE.md` | 编码顺序指南（8 个 Phase） | — |
| `01-project-structure.md` | 完整项目目录树 | 系统架构设计 |
| `02-agent-framework.md` | Agent 基类 + Orchestrator + Supervisor + MessageBus | AGENTS.md、Agent职责划分 |
| `03-state-machine.md` | 审查状态机枚举 + 转换表 + 超时/重试配置 | Agent协作协议 |
| `04-api-supplement.md` | 缺失的请求/响应体 + 错误码枚举 | 接口设计 |
| `05-integration.md` | Redis 命名空间 + Settings 类 + 调用链 | 系统架构设计、.env.example |

## 如何使用

1. 逐个文件填写，每个 `{{TODO}}` 占位符必须填完
2. 填完后让 Agent 读本文档目录下的所有文件
3. Agent 应能直接创建项目、写代码、跑起来
