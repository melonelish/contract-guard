# API 补充规格

> 01-07 的 `接口设计.md` 已定义了大部分端点，但以下端点缺少请求/响应体。本文只补缺失部分。

---

## 1. 缺失的请求/响应体

### 认证

```python
# POST /api/v1/auth/register
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=50)
    company_name: str = Field(..., min_length=1, max_length=100)

# POST /api/v1/auth/login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400

# POST /api/v1/auth/refresh
class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
    expires_in: int = 86400
```

### 合同

```python
# GET /api/v1/contracts — Query: page=1&page_size=20&status=&search=
class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    meta: PaginatedMeta  # {page, page_size, total, total_pages}

# PUT /api/v1/contracts/{id}/draft
class SaveDraftRequest(BaseModel):
    draft_json: dict           # TipTap JSON 文档
    change_summary: str = ""

# POST /api/v1/contracts/{id}/draft/review
class DraftReviewRequest(BaseModel):
    draft_json: dict
    change_summary: str = ""
```

### 审查

```python
# POST /api/v1/contracts/{id}/review
class TriggerReviewRequest(BaseModel):
    contract_type: str | None = None
    review_depth: str = "standard"  # standard | deep
```

### 反馈

```python
# POST /api/v1/reviews/{id}/feedback
class FeedbackRequest(BaseModel):
    clause_id: int | None = None   # null = 反馈整份报告
    is_helpful: bool
    comment: str | None = None
```

---

## 2. 错误码枚举

```python
# backend/app/schemas/errors.py

from enum import IntEnum

class ErrorCode(IntEnum):
    # 通用 1xxx
    SUCCESS = 0
    INVALID_REQUEST = 1001
    UNAUTHORIZED = 1002
    FORBIDDEN = 1003
    NOT_FOUND = 1004
    CONFLICT = 1005
    RATE_LIMITED = 1006
    INTERNAL_ERROR = 1007

    # 认证 2xxx
    LOGIN_FAILED = 2001
    TOKEN_EXPIRED = 2002
    TOKEN_INVALID = 2003

    # 合同 3xxx
    CONTRACT_NOT_FOUND = 3001
    UNSUPPORTED_FILE_TYPE = 3004
    FILE_TOO_LARGE = 3005
    CONTRACT_EDIT_CONFLICT = 3006

    # 审查 4xxx
    REVIEW_NOT_FOUND = 4001
    REVIEW_IN_PROGRESS = 4002
    REVIEW_FAILED = 4003
    LLM_UNAVAILABLE = 4004

    # 知识库 5xxx
    KB_UPDATE_FAILED = 5001
```

---

## 3. 统一响应格式（确认与 01-07 一致）

```python
class ApiResponse(BaseModel):
    code: int = 0              # 0=成功，非0=ErrorCode
    message: str = "success"
    data: Any = None
    meta: dict | None = None   # 分页时填 PaginatedMeta
```
