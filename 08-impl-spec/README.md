# 实现规格说明书

> **本文档是写给 AI 编码 Agent 的。**
> Agent 拿到本文档 + 现有架构文档，应能直接写出可运行的代码，无需猜测。
>
> 填写原则：只写"是什么"，不写"为什么"。"为什么"已经在 01-07 目录的文档里了。

## 文档结构

| 文件 | 内容 | 对应架构文档 |
|------|------|------------|
| `01-project-structure.md` | 完整项目目录树 + 每个文件职责 | 系统架构设计 |
| `02-domain-models.md` | 所有 Pydantic/SQLAlchemy 模型定义 | 数据库设计 |
| `03-agent-specs.md` | 每个 Agent 的完整 I/O 接口 | AGENTS.md、Agent职责划分 |
| `04-state-machine.md` | 审查状态机完整定义 | Agent协作协议 |
| `05-api-contracts.md` | 每个 API 端点的请求/响应/错误码 | 接口设计 |
| `06-llm-integration.md` | LLM 调用层实现规格 | LLM Wrapper Design |
| `07-frontend-specs.md` | 前端类型/store/组件规格 | 双屏对比设计、PRD |
| `08-integration-contracts.md` | 组件间调用协议 | 系统架构设计 |
| `09-config-specs.md` | Settings 类 + 环境变量映射 | .env.example |

## 如何使用

1. 逐个文件填写，每个 `{{TODO}}` 占位符必须填完
2. 填完后让 Agent 读本文档目录下的所有文件
3. Agent 应能直接创建项目、写代码、跑起来
