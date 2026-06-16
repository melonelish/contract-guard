# 项目目录结构

```
contractguard/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # Settings(BaseSettings)
│   │   ├── api/
│   │   │   ├── deps.py                # get_db, get_current_user, get_redis
│   │   │   └── v1/
│   │   │       ├── router.py          # 汇总子路由
│   │   │       ├── auth.py
│   │   │       ├── contracts.py
│   │   │       ├── reviews.py
│   │   │       ├── versions.py
│   │   │       ├── feedback.py
│   │   │       └── health.py
│   │   ├── core/
│   │   │   ├── agent.py               # WorkerAgent ABC
│   │   │   ├── supervisor.py          # SupervisorAgent
│   │   │   ├── orchestrator.py        # ReviewOrchestrator
│   │   │   ├── message_bus.py         # Redis Streams 封装
│   │   │   └── state_machine.py       # 审查状态机
│   │   ├── agents/
│   │   │   ├── parser.py
│   │   │   ├── analyzer.py
│   │   │   ├── report.py
│   │   │   ├── validator.py
│   │   │   └── drafter.py
│   │   ├── llm/
│   │   │   ├── wrapper.py             # llm_chat / llm_embed
│   │   │   ├── registry.py            # MODEL_REGISTRY
│   │   │   └── circuit_breaker.py
│   │   ├── rag/
│   │   │   ├── search.py              # hybrid_search
│   │   │   └── embed.py
│   │   ├── db/
│   │   │   ├── session.py             # AsyncSession + tenant_id 注入
│   │   │   └── models.py              # SQLAlchemy ORM
│   │   ├── schemas/
│   │   │   ├── agent.py               # Agent I/O Pydantic 模型
│   │   │   ├── api.py                 # API 请求/响应模型
│   │   │   ├── domain.py              # 领域对象
│   │   │   └── errors.py              # ErrorCode 枚举
│   │   ├── services/
│   │   │   ├── auth.py
│   │   │   ├── contract.py
│   │   │   └── review.py
│   │   └── utils/
│   │       ├── pdf.py
│   │       └── diff.py
│   ├── tests/
│   │   └── conftest.py
│   ├── migrations/
│   │   └── env.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts              # Axios + JWT 拦截器
│   │   │   ├── types.ts
│   │   │   └── endpoints.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   ├── contract.ts
│   │   │   └── review.ts
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   ├── ContractList/
│   │   │   ├── ReviewReport/
│   │   │   ├── DiffViewer/
│   │   │   └── ContractEditor/
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   └── pages/
│   │       ├── Login.tsx
│   │       ├── ContractListPage.tsx
│   │       ├── ReviewDetailPage.tsx
│   │       └── DraftEditorPage.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docker-compose.yml
├── .env.example
└── Makefile
```
