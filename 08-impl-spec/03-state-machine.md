# 审查状态机

> 01-07 的 `Agent协作协议.md` 画了状态图但箭头没有命名事件。以下补全。

```python
# backend/app/core/state_machine.py

from enum import Enum

class ReviewStatus(str, Enum):
    CREATED       = "created"
    QUEUED        = "queued"
    PARSING       = "parsing"
    PARSED        = "parsed"
    ANALYZING     = "analyzing"
    ANALYZED      = "analyzed"
    PARTIAL_FAIL  = "partial_fail"
    REPORTING     = "reporting"
    REPORTED      = "reported"
    VALIDATING    = "validating"
    APPROVED      = "approved"
    REJECTED      = "rejected"
    RETRYING      = "retrying"
    COMPLETED     = "completed"
    CANCELLED     = "cancelled"
    FAILED        = "failed"

# (当前状态, 事件) → 下一个状态
TRANSITIONS: dict[tuple[str, str], str] = {
    # ── 正常流程 ──
    ("CREATED",    "submit"):          "QUEUED",
    ("QUEUED",     "start"):           "PARSING",
    ("PARSING",    "parse_done"):      "PARSED",
    ("PARSED",     "start_analysis"):  "ANALYZING",
    ("ANALYZING",  "all_done"):        "ANALYZED",
    ("ANALYZED",   "start_report"):    "REPORTING",
    ("REPORTING",  "report_done"):     "REPORTED",
    ("REPORTED",   "start_validate"):  "VALIDATING",
    ("VALIDATING", "validate_pass"):   "APPROVED",
    ("VALIDATING", "validate_reject"): "REJECTED",
    ("APPROVED",   "complete"):        "COMPLETED",

    # ── 部分失败 + 重试 ──
    ("ANALYZING",   "partial_done"):   "ANALYZING",     # 继续等剩余条款
    ("ANALYZING",   "partial_fail"):   "PARTIAL_FAIL",
    ("PARTIAL_FAIL","retry_done"):     "ANALYZING",     # 重跑失败的条款
    ("RETRYING",    "retry_success"):  "PARSED",
    ("RETRYING",    "retry_exhausted"):"FAILED",

    # ── 驳回重试 ──
    ("REJECTED",    "retry"):          "REPORTING",

    # ── 取消（运行中状态均可取消） ──
    ("PARSING",     "cancel"):         "CANCELLED",
    ("PARSED",      "cancel"):         "CANCELLED",
    ("ANALYZING",   "cancel"):         "CANCELLED",
    ("PARTIAL_FAIL","cancel"):         "CANCELLED",
    ("REPORTING",   "cancel"):         "CANCELLED",
    ("RETRYING",    "cancel"):         "CANCELLED",

    # ── 重新审查 ──
    ("COMPLETED",   "reopen"):         "CREATED",
    ("FAILED",      "retry_all"):      "CREATED",
}

# ── 超时配置（秒） ──
TIMEOUT_SECONDS = {
    "PARSING":    120,
    "ANALYZING":   60,    # 单个条款
    "REPORTING":  120,
    "VALIDATING":  30,
}

# ── 最大重试次数 ──
MAX_RETRIES = {
    "parser":    3,
    "analyzer":  2,
    "report":    2,
    "validator": 2,
    "global":    5,
}
```
