#!/bin/bash
# ════════════════════════════════════════════════════════
# ContractGuard — 本地开发环境一键启动脚本
# ════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
echo_green() { echo -e "${GREEN}[OK]${NC} $1"; }
echo_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

# ═══════════ Pre-flight Checks ═══════════
echo "🔍 ContractGuard 环境检查..."

# Docker
if ! command -v docker &>/dev/null; then echo_fail "请安装 Docker Desktop"; exit 1; fi
DOCKER_VER=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
echo_green "Docker $DOCKER_VER"

# Docker Compose
if docker compose version &>/dev/null; then
  echo_green "Docker Compose (plugin)"
elif command -v docker-compose &>/dev/null; then
  echo_green "docker-compose (standalone)"
else
  echo_fail "请安装 Docker Compose"; exit 1
fi

# Memory (min 8GB for Docker, recommend 16GB)
if [[ "$OSTYPE" == "darwin"* ]]; then
  MEM_GB=$(sysctl -n hw.memsize | awk '{printf "%.0f", $1/1024/1024/1024}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
else
  MEM_GB=16  # Windows: assume OK
fi
if [ "$MEM_GB" -lt 8 ]; then echo_warn "内存 < 8GB，建议关闭其他应用后重试"; fi
echo_green "可用内存 ~${MEM_GB}GB"

# Ports
for PORT in 5432 6379 9200 9000 8200 8000 3000; do
  if nc -z localhost $PORT 2>/dev/null || ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo_warn "端口 $PORT 已被占用，请关闭对应服务"
  fi
done

# .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo_warn ".env 已从 .env.example 复制，请编辑填入 API Key"
fi

# ═══════════ Start Services ═══════════
echo ""
echo "📦 拉取 Docker 镜像..."
docker compose pull

echo ""
echo "🚀 启动基础设施服务..."
docker compose up -d postgres redis elasticsearch minio vault etcd

echo ""
echo "⏳ 等待服务健康检查通过..."
TIMEOUT=120; ELAPSED=0; INTERVAL=5

wait_healthy() {
  local svc=$1
  while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker compose ps $svc | grep -q "(healthy)"; then
      echo_green "$svc 就绪"
      return 0
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo -n "."
  done
  echo_fail "$svc 启动超时"
  return 1
}

wait_healthy postgres
wait_healthy redis
wait_healthy elasticsearch

echo ""
echo "🚀 启动 Milvus + API + Frontend..."
docker compose up -d milvus api frontend prometheus grafana
wait_healthy milvus
wait_healthy api

# ═══════════ Database Init ═══════════
echo ""
echo "🗄️  初始化数据库 Schema..."

if docker compose exec -T api alembic upgrade head 2>/dev/null; then
  echo_green "Alembic migration 完成"
else
  echo_warn "Alembic 未配置，跳过 migration。首次运行请手动创建表。"
fi

# ═══════════ Done ═══════════
echo ""
echo "═══════════════════════════════════════════"
echo "✅ ContractGuard 启动完成！"
echo ""
echo "  🌐 Web:       http://localhost:3000"
echo "  📡 API:       http://localhost:8000/api/v1/health"
echo "  📊 Grafana:   http://localhost:3001 (admin/admin)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  📂 MinIO:     http://localhost:9001"
echo ""
echo "  查看日志: docker compose logs -f api"
echo "  停止服务: docker compose down"
echo "═══════════════════════════════════════════"
