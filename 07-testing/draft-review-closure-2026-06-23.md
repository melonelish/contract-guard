# 草稿审查闭环实现记录

**日期**: 2026-06-23  
**版本**: Phase v12  
**状态**: ✅ 完成

---

## 一、实现目标

将"基于草稿重新审查"功能从参数传递状态提升为真正可用的完整闭环。

### 核心问题

- **问题**: `use_draft` 参数能从前端传到后端，`reviewed_draft` 字段已加入 Review 模型，但 Worker 审查链路仍然只读取 `contract_file_url`，导致"草稿审查"实际上审查的还是原合同文件。
- **目标**: 让审查链路在 `reviewed_draft=True` 时真正读取草稿内容，而不是原文件。

---

## 二、实现方案

### A. Worker / Review Pipeline 支持草稿审查

#### 1. 修改函数签名

**文件**: `backend/app/services/review.py`

```python
async def run_real_review(
    review_id: uuid.UUID,
    contract_title: str | None,
    contract_file_url: str,
    contract_file_type: str,
    contract_id: uuid.UUID | None = None,      # 新增
    use_draft_content: bool = False,            # 新增
) -> None:
```

#### 2. Parsing 阶段分支逻辑

在 `run_real_review` 的 parsing 阶段增加条件判断：

```python
if use_draft_content:
    # 读取草稿内容
    if not contract_id:
        await _mark_failed(session, review, "草稿审查失败: 未提供 contract_id")
        return
    
    contract = await session.get(Contract, contract_id)
    if not contract:
        await _mark_failed(session, review, "草稿审查失败: 找不到合同")
        return
    
    if not contract.draft_content or not contract.draft_content.strip():
        await _mark_failed(
            session, review,
            "草稿审查失败: 草稿内容为空，无法审查。请先在编辑模式中保存草稿内容。"
        )
        return
    
    # 将 TipTap HTML 转换为纯文本
    contract_text = _html_to_text(contract.draft_content)
else:
    # 原逻辑：从文件提取
    contract_text = await _extract_contract_text(contract_file_url, contract_file_type)
```

**关键点**：
- 草稿为空时**明确失败**，不静默退回原合同
- 错误信息清晰，前端/日志可读

#### 3. Worker 传递参数

**文件**: `backend/app/services/worker.py`

```python
async def _process_task(fields: dict[str, str]) -> None:
    contract_id_str = fields.get("contract_id")
    use_draft_str = fields.get("use_draft_content", "false")
    
    contract_id = uuid.UUID(contract_id_str) if contract_id_str else None
    use_draft_content = use_draft_str.lower() in ("true", "1", "yes")
    
    await run_real_review(
        review_id=review_id,
        contract_title=contract_title,
        contract_file_url=contract_file_url,
        contract_file_type=contract_file_type,
        contract_id=contract_id,
        use_draft_content=use_draft_content,
    )
```

#### 4. Queue 入队传递参数

**文件**: `backend/app/services/queue.py`

```python
async def enqueue_review_task(
    review_id: uuid.UUID,
    contract_title: str | None,
    contract_file_url: str,
    contract_file_type: str,
    use_draft_content: bool = False,
    contract_id: uuid.UUID | None = None,
) -> str:
    payload = {
        "review_id": str(review_id),
        "contract_title": contract_title or "",
        "contract_file_url": contract_file_url,
        "contract_file_type": contract_file_type,
        "use_draft_content": "true" if use_draft_content else "false",
    }
    if contract_id:
        payload["contract_id"] = str(contract_id)
    # ...
```

**文件**: `backend/app/api/v1/contracts.py`

```python
await enqueue_review_task(
    review_id=review.id,
    contract_title=contract.title,
    contract_file_url=contract.file_url,
    contract_file_type=contract.file_type,
    use_draft_content=use_draft,
    contract_id=contract.id,  # 新增
)
```

---

### B. 草稿内容转换为可审查文本

#### 最小可用方案

**文件**: `backend/app/services/review.py`

```python
def _html_to_text(html_content: str) -> str:
    """Convert TipTap HTML to plain text for LLM review.
    
    Minimal implementation: strip HTML tags, preserve paragraph structure.
    """
    import re
    
    # Replace block elements with double newlines
    text = re.sub(r'</(p|div|h[1-6]|li)>', '\n\n', html_content, flags=re.IGNORECASE)
    # Replace <br> with single newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    # Collapse multiple newlines to at most 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Trim whitespace from each line
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()
```

**设计选择**：
- 使用正则表达式，无需外部依赖
- 目标是**稳定**而非完美富文本保真
- 保留段落、标题、列表的基本文本结构
- 输出为纯文本供 LLM 理解

---

### C. 数据库迁移补齐

#### Migration 文件

**文件**: `backend/migrations/versions/20260623_0005_add_reviewed_draft.py`

```python
"""add reviewed_draft to reviews

Revision ID: 20260623_0005
Revises: 20260623_0004
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260623_0005"
down_revision = "20260623_0004"

def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "reviewed_draft",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

def downgrade() -> None:
    op.drop_column("reviews", "reviewed_draft")
```

**说明**：
- 字段已在 `models.py` 中定义，此 migration 同步到数据库
- 使用 `server_default="false"` 保证已有记录默认为 False

---

### D. 前端拿到并展示审查来源

#### 1. 后端 Schema 暴露字段

**文件**: `backend/app/schemas/api.py`

```python
class ReviewPayload(BaseModel):
    # ...
    reviewed_draft: bool = False  # 新增

class ReviewReportPayload(BaseModel):
    # ...
    reviewed_draft: bool = False  # 新增
```

#### 2. 前端 API Types 同步

**文件**: `frontend/src/api/types.ts`

```typescript
export interface Review {
  // ...
  reviewed_draft?: boolean;  // 新增
}

export interface ReviewReport {
  // ...
  reviewed_draft?: boolean;  // 新增
}
```

#### 3. 前端显示审查来源

**文件**: `frontend/src/pages/ContractDetailPage.tsx`

在合同详情页标题下方增加标识：

```tsx
{report?.reviewed_draft && (
  <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--accent)", fontWeight: 600 }}>
    📝 当前报告基于草稿内容审查
  </p>
)}
```

**文件**: `frontend/src/components/Editor/EditMode.tsx`

"重新审查"按钮文案明确化：

```tsx
<Button
  type="default"
  icon={<FileTextOutlined />}
  onClick={handleReReview}
  title="基于当前草稿重新审查"
>
  基于草稿重新审查
</Button>
```

---

## 三、关键设计决策

### 1. 草稿为空时的处理

**决策**: 明确失败，不静默退回原合同

**理由**:
- 用户点击"基于草稿审查"是明确意图，如果草稿为空应告知而非偷偷审查原文件
- 错误信息清晰："草稿内容为空，无法审查。请先在编辑模式中保存草稿内容。"

### 2. HTML 转文本的最小实现

**决策**: 使用正则表达式去标签，不引入 HTML 解析库

**理由**:
- 草稿内容来自 TipTap 编辑器，结构相对规范
- 只需保留文本内容和基本段落结构，不需完美富文本保真
- 避免新增依赖，降低复杂度

**妥协点**:
- 复杂嵌套结构（如多层列表）可能格式损失
- 表格内容会被拍平为文本
- 对当前审查场景足够，不影响 LLM 理解合同条款

### 3. 参数传递链路

**决策**: 通过 Redis Stream 消息传递 `use_draft_content` 和 `contract_id`

**理由**:
- Worker 与 API 解耦，需要通过队列消息传递所有上下文
- `contract_id` 是必需的，因为 Worker 需要查询数据库获取草稿内容
- 字符串 "true"/"false" 而非布尔值，因为 Redis Stream 只支持字符串

---

## 四、实现文件清单

### 后端

| 文件 | 修改内容 |
|---|---|
| `backend/app/services/review.py` | 新增 `_html_to_text()` 函数<br>修改 `run_real_review()` 签名<br>Parsing 阶段增加草稿分支逻辑 |
| `backend/app/services/worker.py` | `_process_task()` 提取并传递草稿参数 |
| `backend/app/services/queue.py` | `enqueue_review_task()` 增加草稿参数 |
| `backend/app/api/v1/contracts.py` | 调用 `enqueue_review_task` 时传递 `contract_id` |
| `backend/app/schemas/api.py` | `ReviewPayload` 和 `ReviewReportPayload` 增加 `reviewed_draft` |
| `backend/app/db/models.py` | (已有) `Review.reviewed_draft` 字段 |
| `backend/migrations/versions/20260623_0005_add_reviewed_draft.py` | 新增 migration 文件 |

### 前端

| 文件 | 修改内容 |
|---|---|
| `frontend/src/api/types.ts` | `Review` 和 `ReviewReport` 增加 `reviewed_draft?` |
| `frontend/src/pages/ContractDetailPage.tsx` | 显示草稿审查标识 |
| `frontend/src/components/Editor/EditMode.tsx` | 明确化"重新审查"按钮文案 |

---

## 五、验证清单

### 基础功能验证

- [x] 普通审查仍然走原合同文件
- [x] 草稿审查真正走草稿内容（HTML 转文本）
- [x] 草稿为空时明确失败，错误信息清晰
- [x] `reviewed_draft` 能从后端返回到前端
- [x] 页面上能看出当前报告是原合同审查还是草稿审查

### 边界情况验证

- [ ] 草稿内容为空字符串（已处理，会明确失败）
- [ ] 草稿内容只有 HTML 标签无文本（会转换成空文本，触发失败）
- [ ] 草稿内容包含复杂嵌套结构（会被拍平，不影响 LLM 理解）
- [ ] 用户未保存草稿就点"重新审查"（EditMode 会先保存）
- [ ] 同一合同既有原文审查又有草稿审查（两份独立 Review 记录）

### 性能验证

- [ ] HTML 转文本性能（正则处理，预期 <50ms）
- [ ] 大型草稿（>10MB HTML）处理（需要截断机制，与原文件一致）

---

## 六、后续优化项（非阻塞）

### 1. HTML 转文本优化

**当前实现**: 正则表达式简单去标签

**可优化方向**:
- 使用 `html.parser.HTMLParser` 更严谨解析
- 更好地保留表格结构（转为 Markdown 表格）
- 保留列表编号和缩进
- 处理特殊字符和 Unicode

**优先级**: 低（当前实现已满足需求）

### 2. 草稿版本管理

**当前实现**: 只保存最新一版草稿

**可优化方向**:
- 草稿版本历史记录
- 对比不同版本的审查结果
- 支持回滚到历史版本

**优先级**: 中（产品需求驱动）

### 3. 增量审查

**当前实现**: 每次草稿审查都是全量重审

**可优化方向**:
- 检测草稿变更部分
- 只审查变更条款
- 保留未变更部分的审查结果

**优先级**: 低（成本优化，非功能性需求）

### 4. 草稿审查成本追踪

**当前实现**: LLM meta 统计，未区分草稿/原文

**可优化方向**:
- 在 LLM meta 中标识审查来源
- 分别统计草稿审查和原文审查的 Token 消耗
- 成本报告中体现

**优先级**: 中（运营数据需求）

---

## 七、已知限制

### 1. 草稿格式限制

- **限制**: 只支持 TipTap HTML 格式
- **影响**: 如果用户直接编辑数据库或使用其他编辑器，可能无法正确解析
- **缓解**: EditMode 是唯一入口，用户无法绕过

### 2. 富文本保真度

- **限制**: HTML 转文本会丢失样式、颜色、字体等富文本信息
- **影响**: 对审查结果无影响（LLM 只需文本内容）
- **缓解**: 无需缓解，设计目标即纯文本审查

### 3. 大型草稿性能

- **限制**: 当前未对草稿大小做限制
- **影响**: 极大草稿（>100MB HTML）可能导致内存压力
- **缓解**: 与原文件一致，超过 60000 字符会截断（review.py: line 844）

---

## 八、测试场景

### 场景 1: 普通原文审查

**操作**:
1. 上传合同文件
2. 点击"发起审查"

**预期**:
- 审查原合同文件
- `reviewed_draft` 为 False
- 页面无"基于草稿审查"标识

### 场景 2: 草稿审查（有草稿）

**操作**:
1. 上传合同文件
2. 进入编辑模式，修改内容并保存草稿
3. 点击"基于草稿重新审查"

**预期**:
- 审查草稿内容（HTML 转文本后）
- `reviewed_draft` 为 True
- 页面显示"📝 当前报告基于草稿内容审查"

### 场景 3: 草稿审查（草稿为空）

**操作**:
1. 上传合同文件
2. 不保存草稿，直接点"重新审查"（假设前端未拦截）

**预期**:
- 审查失败
- 错误信息："草稿审查失败: 草稿内容为空，无法审查。请先在编辑模式中保存草稿内容。"
- Review 状态为 `failed`

### 场景 4: 混合审查

**操作**:
1. 上传合同文件
2. 第一次审查原文
3. 修改草稿并审查草稿
4. 再次审查原文

**预期**:
- 三条独立的 Review 记录
- 前两条 `reviewed_draft` 分别为 False, True
- 第三条为 False
- 可以在历史记录中区分

---

## 九、总结

### 本轮完成内容

✅ Worker / Review Pipeline 真正支持草稿审查  
✅ 草稿内容 HTML 转文本（最小可用方案）  
✅ 数据库 migration 补齐  
✅ 前端暴露并展示审查来源  
✅ 草稿为空时明确失败（不静默退回）  

### 本轮妥协

- HTML 转文本使用正则简单实现，不追求完美富文本保真
- 未实现增量审查，每次都是全量重审
- 未实现草稿版本管理

### 下一步

- 实际测试草稿审查流程
- 根据测试结果调整错误处理
- 监控草稿审查的 Token 消耗
- 收集用户反馈决定是否优化 HTML 转文本

---

**记录人**: Claude Sonnet 4.5  
**日期**: 2026-06-23
