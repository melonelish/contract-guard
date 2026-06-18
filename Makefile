# ═══════════════════════════════════════════
# ContractGuard — Makefile
# ═══════════════════════════════════════════

.PHONY: setup up down logs restart clean test lint health

DOCKER_COMPOSE ?= docker-compose

# 一键启动（首次运行）
setup:
	bash scripts/setup.sh

# 启动所有服务
up:
	$(DOCKER_COMPOSE) up -d

# 停止所有服务
down:
	$(DOCKER_COMPOSE) down

# 查看 API 日志
logs:
	$(DOCKER_COMPOSE) logs -f api

# 重启 API（代码变更后）
restart:
	$(DOCKER_COMPOSE) restart api

# 后端测试
test:
	cd backend && python -m pytest tests/ -v

# Lint
lint:
	cd backend && ruff check .
	cd frontend && npx eslint . --ext ts,tsx

# 启动 Mock LLM Server（前端独立开发用）
mock:
	python scripts/mock_llm.py

# 健康检查
health:
	@echo "API:        $$(curl -s http://localhost:8000/api/v1/health | jq .status)"
	@echo "PostgreSQL: $$($(DOCKER_COMPOSE) exec -T postgres pg_isready)"
	@echo "Redis:      $$($(DOCKER_COMPOSE) exec -T redis redis-cli ping)"

# 数据库迁移
migrate:
	$(DOCKER_COMPOSE) exec api alembic upgrade head

# 创建新迁移
migration:
	$(DOCKER_COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

# 清理（停止 + 删除 volumes）
clean:
	$(DOCKER_COMPOSE) down -v
	rm -rf backend/__pycache__ backend/.pytest_cache
