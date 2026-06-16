# ═══════════════════════════════════════════
# ContractGuard — Makefile
# ═══════════════════════════════════════════

.PHONY: setup up down logs restart clean test lint health

# 一键启动（首次运行）
setup:
	bash scripts/setup.sh

# 启动所有服务
up:
	docker compose up -d

# 停止所有服务
down:
	docker compose down

# 查看 API 日志
logs:
	docker compose logs -f api

# 重启 API（代码变更后）
restart:
	docker compose restart api

# 后端测试
test:
	cd backend && python -m pytest tests/ -v

# Lint
lint:
	cd backend && ruff check .
	cd frontend && npx eslint . --ext ts,tsx

# 健康检查
health:
	@echo "API:        $$(curl -s http://localhost:8000/api/v1/health | jq .status)"
	@echo "PostgreSQL: $$(docker compose exec -T postgres pg_isready)"
	@echo "Redis:      $$(docker compose exec -T redis redis-cli ping)"

# 数据库迁移
migrate:
	docker compose exec api alembic upgrade head

# 创建新迁移
migration:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

# 清理（停止 + 删除 volumes）
clean:
	docker compose down -v
	rm -rf backend/__pycache__ backend/.pytest_cache
