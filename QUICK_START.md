# 草稿审查闭环 - 快速启动指南

**状态**: ✅ 代码完成，等待部署  
**用时**: 1 个工作会话  
**完成日期**: 2026-06-23

---

## 一句话总结

将"基于草稿重新审查"从**只传参数不落执行**升级为**真正可用的完整闭环**：当用户点击"基于草稿重新审查"时，系统现在会真正读取编辑后的草稿内容（而非原合同文件）进行审查。

---

## 快速启动（3 步）

### 1️⃣ 运行数据库 Migration

```bash
cd backend
alembic upgrade head
```

**验证**:
```bash
alembic current
# 应显示: 20260623_0005 (head)
```

### 2️⃣ 重启服务

```bash
# 后端
cd backend
uvicorn app.main:app --reload

# Worker（新终端）
cd backend
python -m app.services.worker

# 前端（新终端）
cd frontend
npm run dev
```

### 3️⃣ 功能测试（2分钟）

1. 访问 `http://localhost:5173/workspace`
2. 上传合同 → 点击"发起审查"（原文审查，baseline）
3. 进入"草稿模式" → 修改内容 → 点击"保存草稿"
4. 点击"基于草稿重新审查"
5. **验证点**: 
   - 页面显示 "📝 当前报告基于草稿内容审查"
   - 报告内容基于修改后的草稿，而非原 PDF

---

## 核心改动

### 后端（3 个关键文件）

**`backend/app/services/review.py`** (+60 行)
- 新增 `_html_to_text()`: 将 TipTap HTML 草稿转为纯文本
- 修改 `run_real_review()`: 增加 `use_draft_content` 参数
- Parsing 阶段: 根据参数读取草稿或原文件

**`backend/app/services/worker.py`** (+12 行)
- 从 Redis Stream 提取 `contract_id` 和 `use_draft_content`
- 传递给 `run_real_review()`

**`backend/app/services/queue.py`** (+10 行)
- `enqueue_review_task()` 增加参数
- Redis 消息包含草稿标识

### 前端（1 个关键文件）

**`frontend/src/pages/ContractDetailPage.tsx`** (+6 行)
- 草稿审查时显示标识："📝 当前报告基于草稿内容审查"

---

## 关键决策

### ✅ 草稿为空 → 明确失败
- 不静默退回原合同
- 错误信息清晰："草稿内容为空，无法审查"

### ✅ HTML 转文本 → 正则简单实现
- 无需外部依赖
- 去除标签保留结构
- 对 LLM 理解足够

### ✅ 参数传递 → Redis Stream
- Worker 与 API 解耦
- 消息包含所有上下文

---

## 测试状态

### ✅ 自动化测试全部通过
- 后端静态检查: 通过
- 前端类型检查: 通过
- 前端构建: 成功
- 单元测试: 13/13 通过

### ⏳ 手动测试（5个场景）
1. 原文审查（baseline）
2. 草稿审查（核心功能）
3. 草稿为空（错误处理）
4. 审查来源显示（UI）
5. 混合审查（数据完整性）

详见 `07-testing/draft-review-verification.md`

---

## 故障排查

### 问题: 草稿审查实际审查了原文件

**检查**:
```bash
# 1. 查看 Worker 日志
tail -f backend/logs/app.log | grep use_draft_content
# 应包含: use_draft_content=True

# 2. 查看数据库
psql -d contractguard -c "SELECT id, reviewed_draft FROM reviews ORDER BY created_at DESC LIMIT 5;"
# 应有 reviewed_draft=true 的记录
```

### 问题: 前端不显示草稿标识

**检查**:
- 浏览器开发者工具 → Network → `/api/v1/reviews/{id}` 响应
- 确认 JSON 中有 `reviewed_draft: true`

---

## 回滚方案（如需要）

```bash
cd backend
alembic downgrade -1  # 回滚 migration
git revert HEAD       # 回滚代码
```

---

## 文档索引

| 文档 | 用途 |
|---|---|
| `QUICK_START.md` | 本文档 - 快速启动 |
| `IMPLEMENTATION_SUMMARY.md` | 详细技术总结 |
| `DELIVERY_CHECKLIST.md` | 交付清单 |
| `07-testing/draft-review-closure-2026-06-23.md` | 完整实现记录 |
| `07-testing/draft-review-verification.md` | 验证手册 |

---

## 下一步

1. ✅ **已完成**: 代码实现 + 自动化测试
2. ⏳ **当前**: 等待执行 `alembic upgrade head`
3. ⏳ **下一步**: 重启服务 + 手动功能测试
4. ⏳ **最后**: 用户验收 + 生产部署

---

**预计风险**: 🟢 低（所有修改在新分支，不影响现有功能）  
**部署时间**: < 5 分钟  
**测试时间**: < 10 分钟  

---

**最后更新**: 2026-06-23  
**负责人**: Claude Sonnet 4.5  
**状态**: ✅ Ready to Deploy
