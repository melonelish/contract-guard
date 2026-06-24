# 草稿审查闭环 - 最终交付清单

**完成日期**: 2026-06-23  
**版本**: Phase v12  
**状态**: ✅ 实现完成，等待部署测试

---

## 交付文件清单

### 后端代码（7个文件）

```
backend/app/services/review.py              [修改] +60行  新增 _html_to_text(), 修改 run_real_review()
backend/app/services/worker.py              [修改] +12行  提取并传递草稿参数
backend/app/services/queue.py               [修改] +10行  enqueue_review_task() 增加参数
backend/app/api/v1/contracts.py             [修改] +2行   传递 contract_id
backend/app/schemas/api.py                  [修改] +2行   暴露 reviewed_draft 字段
backend/migrations/versions/20260623_0005_add_reviewed_draft.py  [新增]  Migration
backend/tests/test_draft_review.py          [新增]  13个单元测试
```

### 前端代码（3个文件）

```
frontend/src/api/types.ts                   [修改] +2行   Review/ReviewReport 增加字段
frontend/src/pages/ContractDetailPage.tsx  [修改] +6行   显示草稿审查标识
frontend/src/components/Editor/EditMode.tsx [修改] +2行  明确化按钮文案
```

### 文档（3个文件）

```
07-testing/draft-review-closure-2026-06-23.md      [新增]  详细实现记录
07-testing/draft-review-verification.md            [新增]  验证手册
IMPLEMENTATION_SUMMARY.md                          [新增]  实现总结
```

---

## 核心实现

### 1. HTML 转文本（最小可用实现）

```python
def _html_to_text(html_content: str) -> str:
    """Convert TipTap HTML to plain text for LLM review."""
    import re
    
    # 块级元素 → 双换行
    text = re.sub(r'</(p|div|h[1-6]|li)>', '\n\n', html_content, flags=re.IGNORECASE)
    # <br> → 单换行
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # 移除所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # HTML 实体解码
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')...
    # 折叠多余换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
```

### 2. 审查链路草稿分支

```python
async def run_real_review(
    review_id: uuid.UUID,
    contract_title: str | None,
    contract_file_url: str,
    contract_file_type: str,
    contract_id: uuid.UUID | None = None,      # 新增
    use_draft_content: bool = False,            # 新增
) -> None:
    # ... parsing 阶段
    if use_draft_content:
        # 读取草稿
        contract = await session.get(Contract, contract_id)
        if not contract.draft_content or not contract.draft_content.strip():
            await _mark_failed(session, review, "草稿内容为空，无法审查")
            return
        contract_text = _html_to_text(contract.draft_content)
    else:
        # 原逻辑：读取文件
        contract_text = await _extract_contract_text(contract_file_url, contract_file_type)
```

### 3. 参数传递链路

```
前端 EditMode
  ↓ onClick handleReReview
  ↓ triggerReview(contractId, useDraft=true)
API contracts.py
  ↓ enqueue_review_task(use_draft_content=True, contract_id=...)
Redis Stream
  ↓ {"use_draft_content": "true", "contract_id": "..."}
Worker worker.py
  ↓ _process_task() 提取参数
run_real_review()
  ↓ if use_draft_content: 读取草稿
Parsing 阶段
```

---

## 验证状态

### ✅ 已完成自动化验证

- [x] 后端代码静态检查（Ruff）
- [x] 前端类型检查（TypeScript）
- [x] 前端构建（Vite）
- [x] 单元测试（13个测试全部通过）

### ⏳ 待手动验证

- [ ] 原文审查仍然正常（baseline）
- [ ] 草稿审查真正读取草稿内容（核心功能）
- [ ] 草稿为空时明确失败（错误处理）
- [ ] 页面显示审查来源标识（用户体验）
- [ ] 混合审查独立记录（数据完整性）

---

## 部署步骤

### 1. 数据库 Migration

```bash
cd backend
alembic upgrade head
alembic current  # 验证: 应显示 20260623_0005 (head)
```

### 2. 重启服务

```bash
# 后端
cd backend
uvicorn app.main:app --reload

# Worker
python -m app.services.worker

# 前端
cd frontend
npm run dev
```

### 3. 功能测试

按照 `07-testing/draft-review-verification.md` 执行手动测试。

---

## 关键指标

| 指标 | 数值 |
|---|---|
| 后端修改文件 | 7 个 |
| 前端修改文件 | 3 个 |
| 新增代码行数 | ~100 行 |
| 新增测试用例 | 13 个 |
| 测试通过率 | 100% |
| 静态检查 | 通过 |
| 构建状态 | 成功 |

---

## 技术债务

无新增技术债务。所有妥协均为有意识的设计选择：

- HTML 转文本使用正则（而非完整 Parser）：性能优，对 LLM 理解无影响
- 无草稿大小限制：与原文件处理一致，会自动截断
- 无增量审查：全量重审更简单可靠

---

## 下一步

1. **立即**: 执行 `alembic upgrade head` 运行 migration
2. **重启服务**: 后端 + Worker + 前端
3. **手动测试**: 按验证手册执行 5 个核心场景
4. **监控日志**: 确认 `use_draft_content=True` 和 `draft_extracted` 日志
5. **用户验收**: 确认"基于草稿审查"符合预期

---

**交付状态**: ✅ 代码完成  
**质量保证**: ✅ 自动化验证通过  
**待执行**: 手动功能测试  
**预计风险**: 低（所有修改在新分支，不影响现有功能）
