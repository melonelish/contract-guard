# API与Schema固定契约

> 版本：v1.0 | 最后更新：2026-06-16

---

## 一、文档目的

本文件用于把 ContractGuard 的外部接口契约固定下来。

适用对象：

- 后端 API Agent
- 前端类型生成 Agent
- 测试用例生成 Agent

强制原则：

- 本文中的字段名、类型、可空性、枚举值，默认就是实现契约
- 示例不只是参考样例，而是最小合规输出
- 若与散落在其他文档中的示例冲突，以本文件为准，并同步修正文档源头

---

## 二、全局基础类型

### 2.1 UUID 字段

以下标识统一使用 UUID 字符串：

- `tenant_id`
- `user_id`
- `contract_id`
- `review_id`
- `task_id`
- `clause_id`
- `clause_analysis_id`
- `version_id`
- `draft_id`

### 2.2 通用枚举

```ts
type ReviewStatus =
  | "created"
  | "queued"
  | "parsing"
  | "parsed"
  | "analyzing"
  | "analyzed"
  | "partial_fail"
  | "reporting"
  | "reported"
  | "validating"
  | "approved"
  | "rejected"
  | "retrying"
  | "completed"
  | "cancelled"
  | "failed";

type RiskLevel = "high" | "medium" | "low";

type Vote = "accurate" | "inaccurate";

type DiffType = "add" | "delete" | "modify" | "comment";
```

---

## 三、统一响应壳

### 3.1 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "meta": null
}
```

### 3.2 失败响应

```json
{
  "code": 4003,
  "message": "review failed",
  "data": null,
  "meta": {
    "request_id": "req-uuid",
    "retryable": true
  }
}
```

### 3.3 约束

- 所有响应都使用 `code/message/data/meta` 四段结构
- `code=0` 代表成功
- 非 0 错误时，`data` 必须为 `null`
- 分页接口的 `meta` 至少包含 `page/page_size/total`

---

## 四、核心领域对象

### 4.1 Contract

```json
{
  "contract_id": "11111111-1111-1111-1111-111111111111",
  "title": "设备采购合同",
  "file_type": "pdf",
  "file_size": 248123,
  "page_count": 12,
  "contract_type": "采购合同",
  "status": "uploaded",
  "created_at": "2026-06-16T09:00:00Z",
  "updated_at": "2026-06-16T09:00:00Z"
}
```

### 4.2 Clause

```json
{
  "clause_id": "22222222-2222-2222-2222-222222222222",
  "clause_code": "cl_007",
  "title": "付款条件",
  "category": "付款与结算",
  "page": 5,
  "position": {
    "line_start": 32,
    "line_end": 49
  },
  "full_text": "甲方应于验收完成后3日内支付95%货款，余款于12个月后支付。",
  "contains_table": false,
  "table_markdown": null
}
```

### 4.3 Risk Item

```json
{
  "clause_analysis_id": "33333333-3333-3333-3333-333333333333",
  "clause_id": "22222222-2222-2222-2222-222222222222",
  "clause_code": "cl_007",
  "risk_level": "high",
  "risk_category": "付款条件",
  "original_text": "甲方应于验收完成后3日内支付95%货款，余款于12个月后支付。",
  "legal_analysis": "付款节点明显偏向乙方，甲方缺少足够验收与质保控制权。",
  "law_references": [],
  "case_references": [],
  "plain_explanation": "付款节点明显偏向乙方，甲方缺少足够验收与质保控制权。",
  "suggested_revision": "建议将尾款支付条件与质保期及缺陷修复完成挂钩。",
  "confidence": 0.91
}
```

### 4.4 Review Summary

```json
{
  "review_id": "44444444-4444-4444-4444-444444444444",
  "task_id": "44444444-4444-4444-4444-444444444444",
  "status": "completed",
  "summary": {
    "total_risks": 4,
    "high": 1,
    "medium": 2,
    "low": 1
  }
}
```

---

## 五、核心接口固定请求/响应

### 5.1 上传合同

`POST /api/v1/contracts/upload`

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "contract_id": "11111111-1111-1111-1111-111111111111",
    "title": "设备采购合同",
    "status": "uploaded",
    "created_at": "2026-06-16T09:00:00Z"
  },
  "meta": null
}
```

### 5.2 触发审查

`POST /api/v1/contracts/{id}/review`

请求体：

```json
{
  "contract_type": "采购合同",
  "review_depth": "standard"
}
```

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "review_id": "44444444-4444-4444-4444-444444444444",
    "task_id": "44444444-4444-4444-4444-444444444444",
    "status": "queued",
    "estimated_seconds": 900
  },
  "meta": null
}
```

### 5.3 查询审查状态

`GET /api/v1/reviews/{id}/status`

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "review_id": "44444444-4444-4444-4444-444444444444",
    "task_id": "44444444-4444-4444-4444-444444444444",
    "status": "analyzing",
    "progress": 45,
    "current_stage": "analyzing",
    "eta_sec": 320
  },
  "meta": null
}
```

### 5.4 获取审查报告

`GET /api/v1/reviews/{id}`

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "review_id": "44444444-4444-4444-4444-444444444444",
    "task_id": "44444444-4444-4444-4444-444444444444",
    "contract": {
      "contract_id": "11111111-1111-1111-1111-111111111111",
      "title": "设备采购合同",
      "contract_type": "采购合同"
    },
    "summary": {
      "total_risks": 4,
      "high": 1,
      "medium": 2,
      "low": 1
    },
    "risks": [],
    "contradictions": [],
    "missing_clauses": [],
    "disclaimer": "fixed-text"
  },
  "meta": null
}
```

### 5.5 保存草稿

`PUT /api/v1/contracts/{id}/draft`

请求体：

```json
{
  "draft_json": {
    "clauses": []
  },
  "change_summary": "已修改付款条件",
  "version": 3
}
```

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "draft_id": "55555555-5555-5555-5555-555555555555",
    "version": 4,
    "status": "editing",
    "updated_at": "2026-06-16T10:30:00Z"
  },
  "meta": null
}
```

### 5.6 重新审查草稿

`POST /api/v1/contracts/{id}/draft/review`

请求体：

```json
{
  "draft_json": {
    "clauses": []
  },
  "change_summary": "修改付款条件和违约责任"
}
```

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "review_id": "66666666-6666-6666-6666-666666666666",
    "task_id": "66666666-6666-6666-6666-666666666666",
    "status": "queued",
    "incremental": true,
    "changed_clause_count": 2
  },
  "meta": null
}
```

### 5.7 获取版本差异

`GET /api/v1/contracts/{id}/diffs?from=v1&to=v2`

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "from_version": 1,
    "to_version": 2,
    "clauses_added": [],
    "clauses_removed": [],
    "clauses_modified": [
      {
        "clause_id": "22222222-2222-2222-2222-222222222222",
        "clause_code": "cl_007",
        "title": "付款条件",
        "old_text": "甲方应于验收完成后3日内支付95%货款。",
        "new_text": "甲方应于验收完成后7日内支付90%货款。"
      }
    ]
  },
  "meta": null
}
```

---

## 六、WebSocket 固定事件契约

### 6.1 进度事件

```json
{
  "event": "stage",
  "review_id": "44444444-4444-4444-4444-444444444444",
  "task_id": "44444444-4444-4444-4444-444444444444",
  "stage": "analyzing",
  "progress": 45,
  "detail": "正在分析条款 8/18",
  "clause_current": 8,
  "clause_total": 18,
  "eta_sec": 320
}
```

### 6.2 完成事件

```json
{
  "event": "complete",
  "review_id": "44444444-4444-4444-4444-444444444444",
  "task_id": "44444444-4444-4444-4444-444444444444",
  "summary": {
    "total_risks": 4,
    "high": 1,
    "medium": 2,
    "low": 1
  },
  "duration_sec": 286
}
```

### 6.3 失败事件

```json
{
  "event": "failed",
  "review_id": "44444444-4444-4444-4444-444444444444",
  "task_id": "44444444-4444-4444-4444-444444444444",
  "code": 4004,
  "message": "llm unavailable",
  "detail": "主模型与备用模型均不可用",
  "retryable": true
}
```

---

## 七、前端类型生成要求

- 前端 `src/api/types.ts` 必须严格映射本文件中的对象结构
- 对于后端暂未返回但文档已固定的字段，禁止前端私自删除类型
- 所有 UUID 字段前端统一视为 `string`
- `risk_level`、`status`、`event` 一律建成字面量联合类型，不用宽泛 `string`

---

## 八、测试要求

| 测试 ID | 目标 |
|---|---|
| T-SCHEMA-001 | 上传合同响应字段完整 |
| T-SCHEMA-002 | 触发审查同时返回 `review_id` 和 `task_id` |
| T-SCHEMA-003 | 风险项必须返回 `clause_analysis_id + clause_id + clause_code` |
| T-SCHEMA-004 | WebSocket `failed` 事件结构固定 |
| T-SCHEMA-005 | 草稿保存响应返回递增后的 `version` |
