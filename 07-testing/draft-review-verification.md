# 草稿审查闭环实现 - 验证脚本

本脚本用于验证草稿审查功能的完整性。

## 前置条件

1. 后端服务运行在 `http://localhost:8000`
2. 前端服务运行在 `http://localhost:5173`
3. 数据库已运行 migration: `20260623_0005_add_reviewed_draft.py`
4. Redis 服务运行在 `localhost:6379`

## 验证步骤

### 1. 数据库 Migration 验证

```bash
cd backend
alembic current
# 预期输出: 20260623_0005 (head)

# 检查 reviews 表是否有 reviewed_draft 字段
psql -U postgres -d contractguard -c "\d reviews" | grep reviewed_draft
# 预期输出: reviewed_draft | boolean | not null | false
```

### 2. 后端代码验证

```bash
cd backend
python -m ruff check app/services/review.py app/services/worker.py app/services/queue.py app/api/v1/contracts.py app/schemas/api.py
# 预期输出: All checks passed!

python -m pytest tests/test_draft_review.py -v
# 预期输出: 15 个测试全部通过
```

### 3. 前端代码验证

```bash
cd frontend
npm run type-check
# 预期输出: 无错误

npm run build
# 预期输出: ✓ built in X.XXs
```

### 4. 功能验证（需要手动测试）

#### 4.1 原文审查（baseline）

1. 访问 `http://localhost:5173/workspace`
2. 上传一份测试合同（PDF）
3. 点击"发起审查"
4. 等待审查完成
5. **验证点**:
   - 审查状态变为 `completed`
   - 页面**没有**显示"📝 当前报告基于草稿内容审查"
   - 报告内容基于原始 PDF 文件

#### 4.2 草稿审查（核心场景）

1. 在上一步合同详情页，点击"进入草稿模式"
2. 在编辑器中修改内容，例如：
   ```
   修改后的合同内容
   
   甲方：测试公司A
   乙方：测试公司B
   
   第一条：修改后的条款
   ```
3. 点击"保存草稿"，等待提示"草稿已保存到服务器"
4. 点击"基于草稿重新审查"
5. 确认对话框，选择"确认重新审查"
6. 等待审查完成
7. **验证点**:
   - 审查状态变为 `completed`
   - 页面**显示**"📝 当前报告基于草稿内容审查"
   - 报告内容基于修改后的草稿内容，而非原始 PDF

#### 4.3 草稿为空时的错误处理

1. 上传新合同
2. 不进入编辑模式，直接在浏览器控制台执行：
   ```javascript
   // 模拟直接调用草稿审查 API
   fetch('http://localhost:8000/api/v1/contracts/YOUR_CONTRACT_ID/review?use_draft=true', {
     method: 'POST',
     headers: {
       'Authorization': 'Bearer YOUR_TOKEN'
     }
   })
   ```
3. **验证点**:
   - 审查状态变为 `failed`
   - 错误信息为："草稿审查失败: 草稿内容为空，无法审查。请先在编辑模式中保存草稿内容。"

#### 4.4 混合审查（原文 + 草稿）

1. 上传合同
2. 第一次：点击"发起审查"（原文审查）
3. 第二次：修改草稿并点击"基于草稿重新审查"
4. 第三次：再次点击"发起审查"（原文审查）
5. **验证点**:
   - 在审查历史中可以看到 3 条记录
   - 第 1 条：`reviewed_draft=false`
   - 第 2 条：`reviewed_draft=true`，显示"📝 当前报告基于草稿内容审查"
   - 第 3 条：`reviewed_draft=false`

### 5. 日志验证

#### 5.1 Worker 日志

```bash
# 查看 Worker 处理草稿审查的日志
tail -f backend/logs/app.log | grep -E "use_draft_content|draft_extracted"
```

预期输出示例：
```
worker.task_started review_id=xxx use_draft_content=True
review.draft_extracted review_id=xxx draft_length=1234 text_length=567
```

#### 5.2 Redis 队列消息

```bash
# 查看 Redis Stream 中的消息
redis-cli XREAD COUNT 1 STREAMS review:tasks 0-0
```

预期包含字段：
```
1) "use_draft_content"
2) "true"
3) "contract_id"
4) "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### 6. 性能验证

#### 6.1 HTML 转文本性能

```bash
cd backend
python -c "
import time
from app.services.review import _html_to_text

# 生成大型 HTML（模拟长合同）
html = '<p>段落内容</p>' * 10000

start = time.time()
result = _html_to_text(html)
elapsed = time.time() - start

print(f'HTML length: {len(html)}')
print(f'Text length: {len(result)}')
print(f'Time: {elapsed*1000:.2f}ms')
"
```

预期输出：
```
HTML length: 150000
Text length: ~100000
Time: < 100ms
```

### 7. 数据完整性验证

```sql
-- 查询最近的草稿审查记录
SELECT 
  r.id,
  r.contract_id,
  r.reviewed_draft,
  r.status,
  c.title,
  LENGTH(c.draft_content) as draft_size
FROM reviews r
JOIN contracts c ON r.contract_id = c.id
WHERE r.reviewed_draft = true
ORDER BY r.created_at DESC
LIMIT 5;
```

预期结果：
- `reviewed_draft` 为 `true` 的记录
- 对应的 `contracts.draft_content` 不为空

## 已知问题排查

### 问题 1: 草稿审查实际审查了原文件

**症状**: 点击"基于草稿重新审查"后，报告内容仍然是原合同内容

**排查**:
1. 检查 Worker 日志是否有 `use_draft_content=True`
2. 检查是否有 `review.draft_extracted` 日志
3. 检查数据库中 `contracts.draft_content` 是否有内容

**可能原因**:
- Redis Stream 消息中没有正确传递 `use_draft_content`
- Worker 没有正确解析参数
- 草稿内容为空

### 问题 2: 草稿审查失败，错误信息不清晰

**症状**: 审查状态为 `failed`，但 `error_detail` 为空或不明确

**排查**:
1. 检查 `review.error_detail` 字段
2. 检查后端日志中的 `review.failed` 条目
3. 检查是否执行到了 `_mark_failed` 函数

**可能原因**:
- 异常没有被正确捕获
- 错误消息被截断（超过 2000 字符）

### 问题 3: 前端不显示"基于草稿审查"标识

**症状**: 草稿审查完成，但页面没有显示"📝 当前报告基于草稿内容审查"

**排查**:
1. 打开浏览器开发者工具，查看 Network 标签
2. 检查 `/api/v1/reviews/{review_id}` 响应中是否有 `reviewed_draft` 字段
3. 检查 React DevTools 中 `report` 对象的 `reviewed_draft` 属性

**可能原因**:
- 后端 Schema 没有正确序列化 `reviewed_draft`
- 前端 TypeScript 类型定义不匹配
- 条件渲染逻辑错误

### 问题 4: HTML 转文本结果异常

**症状**: 转换后的文本包含 HTML 标签或格式混乱

**排查**:
1. 运行测试：`pytest tests/test_draft_review.py::TestHTMLToText -v`
2. 检查草稿内容的 HTML 结构是否符合预期
3. 手动测试 `_html_to_text()` 函数

**可能原因**:
- 正则表达式没有正确匹配所有标签
- HTML 实体没有完全解码
- 输入 HTML 格式不规范

## 回滚方案

如果草稿审查功能出现严重问题，需要回滚：

```bash
# 1. 数据库回滚
cd backend
alembic downgrade -1  # 回滚 20260623_0005

# 2. 代码回滚
git revert HEAD  # 或手动恢复到上一个 commit

# 3. 重启服务
# 后端
cd backend
pkill -f uvicorn
uvicorn app.main:app --reload

# Worker
pkill -f worker
python -m app.services.worker
```

## 成功标准

所有验证步骤通过，且满足以下条件：

- [x] 后端代码 ruff 检查通过
- [x] 后端测试全部通过
- [x] 前端类型检查通过
- [x] 前端构建成功
- [ ] 原文审查功能不受影响（baseline）
- [ ] 草稿审查真正读取草稿内容（核心功能）
- [ ] 草稿为空时明确失败（边界处理）
- [ ] 页面正确显示审查来源标识（用户体验）
- [ ] 日志包含草稿审查相关信息（可观测性）

---

**最后更新**: 2026-06-23  
**负责人**: Claude Sonnet 4.5  
**状态**: 自动化验证完成，等待手动功能测试
