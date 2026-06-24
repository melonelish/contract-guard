from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.services import review as review_module


class _FakeSession:
    def __init__(self):
        self.executed = []
        self.added = None
        self.commits = 0
        self.refreshed = []

    async def execute(self, stmt):
        self.executed.append(stmt)

    def add(self, obj):
        self.added = obj

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


@pytest.mark.asyncio
async def test_create_review_locks_contract_row(monkeypatch):
    session = _FakeSession()
    user = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    contract = SimpleNamespace(id=uuid4())

    async def no_existing_review(*_args, **_kwargs):
        return None

    monkeypatch.setattr(review_module, "get_latest_review_for_contract", no_existing_review)

    review = await review_module.create_review(session, user, contract)

    assert session.executed, "contract row should be locked before creating review"
    assert "FOR UPDATE" in str(session.executed[0])
    assert review.contract_id == contract.id
    assert session.added is review


@pytest.mark.asyncio
async def test_download_from_storage_preserves_original_error(monkeypatch):
    class FakeMinio:
        def __init__(self, *args, **kwargs):
            pass

        def get_object(self, bucket, object_name):
            raise RuntimeError("storage boom")

    monkeypatch.setitem(sys.modules, "minio", SimpleNamespace(Minio=FakeMinio))
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: SimpleNamespace(
            minio_endpoint="localhost:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            minio_secure=False,
        ),
    )

    with pytest.raises(RuntimeError, match="storage boom"):
        await review_module._download_from_storage("s3://bucket/sample.pdf")


def test_validate_report_schema_rejects_missing_summary():
    is_valid, error = review_module.validate_report_schema({"risks": []})

    assert not is_valid
    assert "summary" in error


def test_validate_report_schema_rejects_non_string_basis_field():
    is_valid, error = review_module.validate_report_schema(
        {
            "summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0},
            "risks": [
                {
                    "clause_id": "cl_001",
                    "risk_level": "high",
                    "risk_category": "付款条件",
                    "legal_basis": ["not", "a", "string"],
                }
            ],
        }
    )

    assert not is_valid
    assert "legal_basis must be a string" in error


def test_clean_report_injects_summary_and_llm_defaults():
    report = {
        "risks": [
            {"clause_id": "cl_001", "risk_level": "high", "risk_category": "付款条件"},
            {"clause_id": "cl_002", "risk_level": "low", "risk_category": "违约责任"},
        ],
    }

    cleaned = review_module.clean_report(report)

    assert cleaned["summary"] == {"total_risks": 2, "high": 1, "medium": 0, "low": 1}
    assert cleaned["disclaimer"]
    assert cleaned["schema_version"] == "1.0"
    assert cleaned["risks"][0]["confidence"] == 0.5


def test_build_llm_meta_normalizes_usage():
    meta = review_module.build_llm_meta(
        {
            "model": "mimo-v2.5",
            "usage": {"prompt_tokens": 123, "completion_tokens": 456},
            "latency_ms": 789,
            "finish_reason": "end_turn",
        }
    )

    assert meta == {
        "provider_model": "mimo-v2.5",
        "prompt_tokens": 123,
        "completion_tokens": 456,
        "latency_ms": 789,
        "finish_reason": "end_turn",
    }


def test_ground_risk_legal_basis_downgrades_unverified_citation():
    risk = {
        "risk_category": "付款条件",
        "legal_basis": "《民法典》第999条",
        "basis_source": "《民法典》第999条（虚构条文）",
    }
    rag_results = [
        SimpleNamespace(
            law_name="民法典",
            article_number="第509条",
            article_title="合同履行",
            full_text="当事人应当按照约定全面履行自己的义务。",
            section="",
            score=0.9,
        )
    ]

    review_module._ground_risk_legal_basis(risk, rag_results)

    assert risk["legal_basis"] == "依据不足，基于法理分析"
    assert risk["basis_excerpt"] == ""
    assert risk["basis_source"] == ""


def test_parse_llm_report_content_supports_fenced_json():
    report = review_module._parse_llm_report_content(
        """```json
{
  "summary": {"total_risks": 0, "high": 0, "medium": 0, "low": 0},
  "risks": []
}
```"""
    )

    assert report["summary"]["total_risks"] == 0
    assert report["risks"] == []


def test_review_prompt_is_constrained_for_latency():
    assert "最重要的 8 条风险" in review_module.SYSTEM_PROMPT
    assert "contradictions 最多 3 条" in review_module.SYSTEM_PROMPT
    assert "missing_clauses 最多 5 条" in review_module.USER_PROMPT_TEMPLATE


def test_max_tokens_increased_for_long_contracts():
    """Phase 3d: max_tokens must be 8192 to prevent truncation."""
    assert review_module.LLM_MAX_TOKENS == 8192


def test_system_prompt_includes_high_risk_priority():
    """Phase 3d: prompt must explicitly list high-risk themes."""
    assert "数据安全" in review_module.SYSTEM_PROMPT
    assert "知识产权" in review_module.SYSTEM_PROMPT
    assert "合作范围" in review_module.SYSTEM_PROMPT
    assert "合规风险" in review_module.SYSTEM_PROMPT


def test_user_prompt_requires_contract_type_awareness():
    """Phase 3d: prompt must require contract type identification."""
    assert "合同类型" in review_module.USER_PROMPT_TEMPLATE
    assert "法条引用必须与合同类型匹配" in review_module.USER_PROMPT_TEMPLATE


def test_json_repair_prompt_is_present():
    assert "JSON 修复助手" in review_module.JSON_REPAIR_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Phase 3c — JSON parsing stability tests
# ---------------------------------------------------------------------------


def test_parse_llm_report_content_fenced_json():
    """Fenced code block should be extracted and parsed."""
    raw = '''以下是审查结果：
```json
{"summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0}, "risks": []}
```
请查收。'''
    report = review_module._parse_llm_report_content(raw)
    assert report["summary"]["total_risks"] == 1


def test_parse_llm_report_content_mixed_text():
    """JSON embedded in explanatory text should be extracted."""
    raw = '''好的，以下是合同审查结果：
{"summary": {"total_risks": 2, "high": 1, "medium": 1, "low": 0}, "risks": [{"clause_id": "cl_001", "risk_level": "high", "risk_category": "付款"}]}
以上是审查报告。'''
    report = review_module._parse_llm_report_content(raw)
    assert report["summary"]["total_risks"] == 2


def test_local_json_repair_unterminated_string():
    """Unterminated strings should be repaired locally."""
    # Simulate LLM output with unterminated string at line boundary
    raw = '{"summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0}, "risks": [{"clause_id": "cl_001", "risk_level": "high", "risk_category": "付款条件", "original_text": "甲方应在验收后30日内付清全款'
    report = review_module._local_json_repair(raw)
    assert report["summary"]["total_risks"] == 1


def test_local_json_repair_trailing_comma():
    """Trailing commas should be removed."""
    raw = '{"summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0}, "risks": [],}'
    report = review_module._local_json_repair(raw)
    assert report["risks"] == []


def test_local_json_repair_truncated_json():
    """Truncated JSON (missing closing braces) should be repaired."""
    raw = '{"summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0}, "risks": []'
    report = review_module._local_json_repair(raw)
    assert report["summary"]["total_risks"] == 1


def test_local_json_repair_truncated_nested():
    """Deeply truncated JSON should be closed properly."""
    raw = '{"summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0}, "risks": [{"clause_id": "cl_001"'
    report = review_module._local_json_repair(raw)
    assert "risks" in report


def test_extract_json_block_from_mixed_text():
    """Should extract JSON object from surrounding text."""
    raw = '''Here is the result:
{"key": "value", "nested": {"a": 1}}
End of result.'''
    extracted = review_module._extract_json_block(raw)
    assert extracted == '{"key": "value", "nested": {"a": 1}}'


def test_extract_json_block_returns_none_for_no_json():
    """Should return None when no JSON block found."""
    assert review_module._extract_json_block("no json here") is None
    assert review_module._extract_json_block("") is None


def test_parse_llm_report_content_direct_json():
    """Direct JSON should be parsed without any repair."""
    raw = '{"summary": {"total_risks": 0, "high": 0, "medium": 0, "low": 0}, "risks": []}'
    report = review_module._parse_llm_report_content(raw)
    assert report["summary"]["total_risks"] == 0


def test_parse_llm_report_content_fenced_with_surrounding_text():
    """Fenced JSON with text before and after should be extracted."""
    raw = '''我已经审查了这份合同，以下是结果：

```json
{
  "summary": {"total_risks": 3, "high": 1, "medium": 1, "low": 1},
  "risks": []
}
```

如有疑问请随时联系。'''
    report = review_module._parse_llm_report_content(raw)
    assert report["summary"]["total_risks"] == 3


def test_validate_report_schema_accepts_valid_report():
    """Valid report with all required fields should pass."""
    report = {
        "summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0},
        "risks": [
            {
                "clause_id": "cl_001",
                "risk_level": "high",
                "risk_category": "付款条件",
                "legal_basis": "《民法典》第585条",
                "basis_excerpt": "测试",
                "basis_source": "《民法典》第585条",
            }
        ],
    }
    is_valid, error = review_module.validate_report_schema(report)
    assert is_valid
    assert error == ""


def test_validate_report_schema_rejects_invalid_risk_level():
    """Invalid risk_level should be rejected."""
    report = {
        "summary": {"total_risks": 1, "high": 1, "medium": 0, "low": 0},
        "risks": [
            {
                "clause_id": "cl_001",
                "risk_level": "critical",  # invalid
                "risk_category": "付款",
            }
        ],
    }
    is_valid, error = review_module.validate_report_schema(report)
    assert not is_valid
    assert "risk_level" in error


def test_failed_review_has_error_detail():
    """Failed reviews must always have error_detail set."""
    from types import SimpleNamespace

    review = SimpleNamespace(
        status="failed",
        error_detail="JSON解析失败: test error",
        completed_at="2026-06-19T10:00:00",
    )
    assert review.status == "failed"
    assert review.error_detail is not None
    assert len(review.error_detail) > 0


def test_completed_review_has_no_error_detail():
    """Completed reviews should not have error_detail."""
    from types import SimpleNamespace

    review = SimpleNamespace(
        status="completed",
        error_detail=None,
    )
    assert review.status == "completed"
    assert review.error_detail is None


def test_apply_local_fixes_removes_trailing_commas():
    """_apply_local_fixes should remove trailing commas."""
    fixed = review_module._apply_local_fixes('{"a": 1, "b": 2,}')
    parsed = json.loads(fixed)
    assert parsed == {"a": 1, "b": 2}


def test_apply_local_fixes_closes_unclosed_braces():
    """_apply_local_fixes should close unclosed braces."""
    fixed = review_module._apply_local_fixes('{"a": 1, "b": {"c": 2}')
    parsed = json.loads(fixed)
    assert parsed["b"]["c"] == 2


def test_select_schema_fallback_report_prefers_initial_report():
    """When both reports are invalid, prefer the initial usable report."""
    initial = {
        "summary": {},
        "risks": [{"clause_id": "cl_001", "risk_level": "high"}],
    }
    retry = {
        "summary": {},
        "risks": [{"clause_id": "cl_999"}],
    }

    selected, source = review_module._select_schema_fallback_report(initial, retry)

    assert selected is initial
    assert source == "initial"


def test_select_schema_fallback_report_uses_retry_if_initial_unusable():
    """Retry report can be used only when initial result is unusable."""
    initial = {"summary": {}, "risks": []}
    retry = {
        "summary": {},
        "risks": [{"clause_id": "cl_002", "risk_level": "medium"}],
    }

    selected, source = review_module._select_schema_fallback_report(initial, retry)

    assert selected is retry
    assert source == "retry"


# ---------------------------------------------------------------------------
# Phase 3e — High-risk priority and empty content tests
# ---------------------------------------------------------------------------


def test_system_prompt_includes_contract_type_guidance():
    """SYSTEM_PROMPT should contain contract-type-specific review guidance."""
    prompt = review_module.SYSTEM_PROMPT
    assert "代理/销售/经销合同" in prompt
    assert "技术开发/定制/区块链" in prompt
    assert "SaaS/平台服务合同" in prompt
    assert "顾问/外包/兼职合同" in prompt
    assert "佣金计算" in prompt
    assert "安全责任" in prompt
    assert "SLA" in prompt
    assert "劳动关系认定" in prompt


def test_user_prompt_includes_contract_type_hints():
    """USER_PROMPT_TEMPLATE should hint at contract-type-specific checks."""
    template = review_module.USER_PROMPT_TEMPLATE
    assert "代理/销售/经销" in template
    assert "佣金计算" in template
    assert "技术开发/区块链" in template
    assert "SaaS/平台服务" in template
    assert "顾问/外包" in template


def test_parse_llm_report_content_empty_string():
    """Empty string should raise JSONDecodeError."""
    import pytest
    with pytest.raises(Exception):
        review_module._parse_llm_report_content("")


def test_parse_llm_report_content_whitespace_only():
    """Whitespace-only string should raise JSONDecodeError."""
    import pytest
    with pytest.raises(Exception):
        review_module._parse_llm_report_content("   \n\t  ")


def test_parse_llm_report_content_valid_minimal():
    """Minimal valid JSON should parse correctly."""
    raw = '{"summary": {"total_risks": 0, "high": 0, "medium": 0, "low": 0}, "risks": []}'
    report = review_module._parse_llm_report_content(raw)
    assert report["summary"]["total_risks"] == 0
    assert report["risks"] == []


def test_high_risk_categories_in_prompt():
    """High-risk categories should be explicitly mentioned in SYSTEM_PROMPT."""
    prompt = review_module.SYSTEM_PROMPT
    # Phase 3e specific categories
    assert "付款条件" in prompt
    assert "知识产权" in prompt
    assert "数据安全" in prompt
    assert "合规风险" in prompt
    assert "合同完整性" in prompt


# ---------------------------------------------------------------------------
# Phase 3e.2 — Agency contract risk category standardization tests
# ---------------------------------------------------------------------------


def _make_agency_report(risks: list[dict]) -> dict:
    """Helper to build a minimal report for testing post-processing."""
    return {
        "summary": {
            "total_risks": len(risks),
            "high": sum(1 for r in risks if r.get("risk_level") == "high"),
            "medium": sum(1 for r in risks if r.get("risk_level") == "medium"),
            "low": sum(1 for r in risks if r.get("risk_level") == "low"),
        },
        "risks": risks,
    }


def test_reclassify_commission_from_payment():
    """佣金相关内容应从'付款条件'重分类为'佣金计算'."""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "high",
            "risk_category": "付款条件",
            "original_text": "甲方按照乙方实际回款金额的一定比例向乙方支付代理佣金。",
            "legal_analysis": "佣金支付仅基于回款。",
            "plain_explanation": "佣金不确定。",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    assert report["risks"][0]["risk_category"] == "佣金计算"


def test_reclassify_commission_wildcard():
    """佣金关键词命中时，任意来源类别都应重分类为'佣金计算'."""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "违约责任",
            "original_text": "佣金按季度结算。",
            "legal_analysis": "",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    assert report["risks"][0]["risk_category"] == "佣金计算"


def test_reclassify_customer_ownership():
    """客户归属相关内容应重分类。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "合作范围",
            "original_text": "客户归属的具体规则详见附件三。",
            "legal_analysis": "",
            "plain_explanation": "客户归属规则不明确。",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    assert report["risks"][0]["risk_category"] == "客户归属"


def test_reclassify_training():
    """培训相关内容应重分类。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "合作范围",
            "original_text": "销售人员应接受甲方组织的产品培训并通过考核。",
            "legal_analysis": "",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    assert report["risks"][0]["risk_category"] == "培训"


def test_reclassify_regional_protection():
    """区域保护相关内容应重分类。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "合规风险",
            "original_text": "甲方授权乙方为华东地区的独家代理商。",
            "legal_analysis": "",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    assert report["risks"][0]["risk_category"] == "区域保护"


def test_reclassify_preserves_payment_for_sales_target_content():
    """含销售指标的付款条件风险不应被重分类（保留预期命中）。

    Phase 3e.2: removing 销售指标 wildcard rule to avoid losing
    "付款条件" expected-topic match.  The model sometimes labels
    sales-target clauses as "付款条件"; keeping that label is less
    harmful than reclassifying to "销售指标" (which isn't in
    expected_high_risk_topics).
    """
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "付款条件",
            "original_text": "乙方承诺完成年度销售指标人民币500万元。",
            "legal_analysis": "",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    # Should NOT be reclassified — stays as 付款条件
    assert report["risks"][0]["risk_category"] == "付款条件"


def test_upgrade_medium_to_high_for_commission():
    """佣金计算风险在含升级关键词时应从 medium 升为 high。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "佣金计算",
            "original_text": "",
            "legal_analysis": "甲方权力过大，乙方权益无保障。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._upgrade_agency_risks(report)

    assert report["risks"][0]["risk_level"] == "high"


def test_upgrade_medium_to_high_for_customer_ownership():
    """客户归属风险在含升级关键词时应升为 high。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "客户归属",
            "original_text": "",
            "legal_analysis": "",
            "plain_explanation": "规则模糊，易引发争议。",
            "suggested_revision": "",
        },
    ])

    review_module._upgrade_agency_risks(report)

    assert report["risks"][0]["risk_level"] == "high"


def test_upgrade_medium_to_high_for_payment():
    """付款条件风险在含升级关键词时应升为 high。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "付款条件",
            "original_text": "",
            "legal_analysis": "单方解除权缺乏协商机制。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._upgrade_agency_risks(report)

    assert report["risks"][0]["risk_level"] == "high"


def test_upgrade_does_not_affect_low_risks():
    """low 风险不应被升级。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "low",
            "risk_category": "佣金计算",
            "original_text": "",
            "legal_analysis": "单方不对等。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._upgrade_agency_risks(report)

    assert report["risks"][0]["risk_level"] == "low"


def test_upgrade_does_not_trigger_without_keywords():
    """不含升级关键词的 medium 风险不应被升级。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "佣金计算",
            "original_text": "佣金按季度结算。",
            "legal_analysis": "佣金支付按照合同约定执行。",
            "plain_explanation": "结算方式已明确约定。",
            "suggested_revision": "",
        },
    ])

    review_module._upgrade_agency_risks(report)

    assert report["risks"][0]["risk_level"] == "medium"


def test_non_agency_contract_not_affected():
    """非代理合同的同名风险不应被升级。"""
    # The trigger is in run_real_review based on title,
    # but _upgrade_agency_risks itself is title-agnostic.
    # Verify it only upgrades core agency categories.
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "知识产权",  # not an agency core category
            "original_text": "",
            "legal_analysis": "单方不对等。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._upgrade_agency_risks(report)

    # 知识产权 is not in _AGENCY_UPGRADE_RULES, should stay medium
    assert report["risks"][0]["risk_level"] == "medium"


def test_update_summary_counts_after_upgrade():
    """升级后 summary 计数应正确更新。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "medium",
            "risk_category": "佣金计算",
            "original_text": "",
            "legal_analysis": "单方不对等。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
        {
            "clause_id": "cl_002",
            "risk_level": "medium",
            "risk_category": "违约责任",
            "original_text": "",
            "legal_analysis": "一般风险。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    # Before upgrade: 0 high, 2 medium
    assert report["summary"]["high"] == 0
    assert report["summary"]["medium"] == 2

    review_module._upgrade_agency_risks(report)
    review_module._update_summary_counts(report)

    # After upgrade: 1 high (佣金计算), 1 medium (违约责任)
    assert report["summary"]["high"] == 1
    assert report["summary"]["medium"] == 1
    assert report["summary"]["total_risks"] == 2


def test_reclassify_then_upgrade_end_to_end():
    """端到端：分类重定 → 升级 → summary 更新完整链路。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "high",
            "risk_category": "付款条件",
            "original_text": "甲方按照乙方实际回款金额的一定比例向乙方支付代理佣金。",
            "legal_analysis": "佣金支付仅基于回款，甲方权力过大，权益无保障。",
            "plain_explanation": "佣金不确定。",
            "suggested_revision": "",
        },
        {
            "clause_id": "cl_002",
            "risk_level": "medium",
            "risk_category": "合作范围",
            "original_text": "客户归属的具体规则详见附件三。",
            "legal_analysis": "",
            "plain_explanation": "规则模糊，易引发争议。",
            "suggested_revision": "",
        },
        {
            "clause_id": "cl_003",
            "risk_level": "medium",
            "risk_category": "合作范围",
            "original_text": "销售人员应接受甲方组织的产品培训并通过考核。",
            "legal_analysis": "缺乏有效约束力。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
        {
            "clause_id": "cl_004",
            "risk_level": "medium",
            "risk_category": "违约责任",
            "original_text": "任一方违反本协议约定，应向守约方支付违约金人民币100,000元。",
            "legal_analysis": "违约金固定。",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)
    review_module._upgrade_agency_risks(report)
    review_module._update_summary_counts(report)

    cats = {r["clause_id"]: r["risk_category"] for r in report["risks"]}
    levels = {r["clause_id"]: r["risk_level"] for r in report["risks"]}

    # cl_001: 付款条件 → 佣金计算 (reclassify), high (already high)
    assert cats["cl_001"] == "佣金计算"
    assert levels["cl_001"] == "high"

    # cl_002: 合作范围 → 客户归属 (reclassify), medium → high (upgrade: 规则模糊+易引发争议)
    assert cats["cl_002"] == "客户归属"
    assert levels["cl_002"] == "high"

    # cl_003: 合作范围 → 培训 (reclassify), medium → high (upgrade: 缺乏有效约束)
    assert cats["cl_003"] == "培训"
    assert levels["cl_003"] == "high"

    # cl_004: 违约责任 stays, medium stays (no upgrade keywords for 违约责任)
    assert cats["cl_004"] == "违约责任"
    assert levels["cl_004"] == "medium"

    # Summary: 3 high, 1 medium
    assert report["summary"]["high"] == 3
    assert report["summary"]["medium"] == 1
    assert report["summary"]["total_risks"] == 4


def test_reclassify_preserves_already_correct_categories():
    """已经正确分类的风险不应被错误重分类。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "high",
            "risk_category": "知识产权",
            "original_text": "甲方拥有代理产品的全部知识产权。",
            "legal_analysis": "",
            "plain_explanation": "",
            "suggested_revision": "",
        },
    ])

    review_module._reclassify_agency_risks(report)

    assert report["risks"][0]["risk_category"] == "知识产权"


# ---------------------------------------------------------------------------
# Phase 3f — Missing clause promotion tests
# ---------------------------------------------------------------------------


def test_promote_missing_clauses_to_risks_adds_high_risk():
    """missing_clauses 应被提升为 risks 中的 high 风险项。"""
    report = {
        "risks": [
            {
                "clause_id": "cl_001",
                "risk_level": "high",
                "risk_category": "付款条件",
                "original_text": "甲方应在30日内付款。",
            },
        ],
        "missing_clauses": [
            {"name": "数据安全条款", "reason": "合同涉及用户数据但未约定安全措施。"},
        ],
    }

    review_module._promote_missing_clauses_to_risks(report)

    assert len(report["risks"]) == 2
    new_risk = report["risks"][1]
    assert new_risk["risk_level"] == "high"
    assert new_risk["clause_id"] == "missing_001"
    assert "数据安全" in new_risk["risk_category"]
    assert "数据安全条款" in new_risk["original_text"]


def test_promote_missing_clauses_deduplicates():
    """已有风险覆盖的缺失条款不应重复添加。"""
    report = {
        "risks": [
            {
                "clause_id": "cl_001",
                "risk_level": "medium",
                "risk_category": "响应时间",
                "original_text": "合同未约定SLA响应时间。",
            },
        ],
        "missing_clauses": [
            {"name": "SLA响应时间", "reason": "缺少SLA条款。"},
        ],
    }

    review_module._promote_missing_clauses_to_risks(report)

    # "SLA响应时间" is already covered by "响应时间" category → should NOT add
    assert len(report["risks"]) == 1


def test_promote_missing_clauses_no_missing():
    """无缺失条款时不应添加任何风险。"""
    report = {
        "risks": [],
        "missing_clauses": [],
    }

    review_module._promote_missing_clauses_to_risks(report)

    assert len(report["risks"]) == 0


def test_promote_missing_clauses_category_mapping():
    """不同缺失条款名称应映射到正确的 risk_category。"""
    report = {
        "risks": [],
        "missing_clauses": [
            {"name": "合规义务条款", "reason": ""},
            {"name": "供应链责任条款", "reason": ""},
            {"name": "不公平格式条款审查", "reason": ""},
            {"name": "灾难恢复机制", "reason": ""},
            {"name": "应急响应预案条款", "reason": ""},  # no specific mapping → 条款缺失
        ],
    }

    review_module._promote_missing_clauses_to_risks(report)

    assert len(report["risks"]) == 5
    cats = [r["risk_category"] for r in report["risks"]]
    assert "合规风险" in cats
    assert "供应链风险" in cats
    assert "不公平条款" in cats
    assert "运营管理" in cats
    assert "条款缺失" in cats


def test_promote_missing_clauses_updates_summary():
    """提升后 summary 计数应正确更新。"""
    report = {
        "risks": [
            {
                "clause_id": "cl_001",
                "risk_level": "medium",
                "risk_category": "付款条件",
                "original_text": "测试。",
            },
        ],
        "missing_clauses": [
            {"name": "质量保证条款", "reason": ""},
            {"name": "验收标准条款", "reason": ""},
        ],
    }

    review_module._promote_missing_clauses_to_risks(report)
    review_module._update_summary_counts(report)

    assert report["summary"]["total_risks"] == 3
    assert report["summary"]["high"] == 2  # two promoted missing clauses
    assert report["summary"]["medium"] == 1


def test_saas_prompt_includes_unfair_terms():
    """SaaS 合同指引应包含不公平格式条款检查。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "不公平格式条款" in prompt
    assert "自动续约陷阱" in prompt
    assert "数据迁移" in prompt


def test_tech_service_prompt_includes_operations():
    """技术服务合同指引应包含运营管理检查。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "运维责任" in prompt
    assert "灾难恢复" in prompt
    assert "业务连续性" in prompt


def test_procurement_prompt_includes_supply_chain():
    """采购合同指引应包含供应链风险检查。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "供应链风险" in prompt
    assert "合规义务" in prompt
    assert "交付与风险转移" in prompt


def test_missing_clause_promotion_instruction_in_prompt():
    """SYSTEM_PROMPT 应包含缺失条款提升为 risks 的强制指令。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "missing_clauses" in prompt
    assert "risks 数组中生成一条对应的 high 风险项" in prompt
    assert "missing_001" in prompt


# ---------------------------------------------------------------------------
# Phase 3h — High-frequency gap topic targeted fix tests
# ---------------------------------------------------------------------------


def test_nda_prompt_includes_confidentiality():
    """NDA/保密协议指引应包含保密范围、保密期限、信息使用限制检查。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "NDA/保密协议" in prompt
    assert "保密范围是否明确界定" in prompt
    assert "保密期限是否合理" in prompt
    assert "信息使用限制" in prompt


def test_consultant_prompt_includes_payment_and_confidentiality():
    """顾问/外包合同指引应包含付款条件和保密义务检查。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "付款条件与报酬约定" in prompt
    assert "保密义务与信息保护" in prompt


def test_user_prompt_includes_nda_hint():
    """USER_PROMPT_TEMPLATE 应包含 NDA 保密义务检查提示。"""
    template = review_module.USER_PROMPT_TEMPLATE
    assert "NDA/保密协议" in template
    assert "保密范围界定" in template


def test_user_prompt_includes_consultant_payment_hint():
    """USER_PROMPT_TEMPLATE 应包含顾问付款条件检查提示。"""
    template = review_module.USER_PROMPT_TEMPLATE
    assert "付款条件、保密义务" in template


def test_user_prompt_includes_procurement_hint():
    """USER_PROMPT_TEMPLATE 应包含采购付款条件和交付条件检查提示。"""
    template = review_module.USER_PROMPT_TEMPLATE
    assert "采购/买卖" in template
    assert "付款条件、交付条件" in template


def test_prompt_warns_against_generic_risks():
    """SYSTEM_PROMPT 应包含避免用通用风险替代特化风险的提醒。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "不要用" in prompt
    assert "通用风险替代" in prompt


def test_procurement_prompt_emphasizes_payment_delivery_qualification():
    """采购合同指引应强调付款条件、交付条件、供应商资质。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "付款条件与交付挂钩" in prompt
    assert "交付与风险转移" in prompt
    assert "产品资质" in prompt


def test_no_regression_agency_prompt():
    """代理合同指引不应被 Phase 3h 修改影响。"""
    prompt = review_module.SYSTEM_PROMPT
    assert "佣金计算" in prompt
    assert "客户归属" in prompt
    assert "区域保护" in prompt
    assert "销售指标" in prompt


def test_no_regression_missing_clause_promotion():
    """缺失条款提升功能不应被 Phase 3h 修改影响。"""
    report = {
        "risks": [],
        "missing_clauses": [
            {"name": "保密义务条款", "reason": "合同缺少保密条款。"},
        ],
    }
    review_module._promote_missing_clauses_to_risks(report)
    assert len(report["risks"]) == 1
    assert report["risks"][0]["risk_level"] == "high"


def test_no_regression_labor_law_filter():
    """劳动合同法过滤不应被 Phase 3h 修改影响。"""
    # The labor law filter is in rag.py, verify it still exists
    from app.services.rag import _is_labor_contract, _NON_LABOR_FORBIDDEN_LAWS
    assert _is_labor_contract("劳动合同") is True
    assert _is_labor_contract("采购合同") is False
    assert "中华人民共和国劳动合同法" in _NON_LABOR_FORBIDDEN_LAWS


def test_end_to_end_promote_with_agency_postprocess():
    """端到端：代理合同后处理 + 缺失条款提升完整链路。"""
    report = _make_agency_report([
        {
            "clause_id": "cl_001",
            "risk_level": "high",
            "risk_category": "付款条件",
            "original_text": "代理佣金按回款比例计算。",
            "legal_analysis": "佣金比例不明确，权益无保障。",
            "plain_explanation": "佣金不确定。",
            "suggested_revision": "",
        },
    ])
    report["missing_clauses"] = [
        {"name": "客户归属条款", "reason": "代理终止后客户资源归属不清。"},
    ]

    # Agent post-processing
    review_module._reclassify_agency_risks(report)
    review_module._upgrade_agency_risks(report)
    # Missing clause promotion
    review_module._promote_missing_clauses_to_risks(report)
    review_module._update_summary_counts(report)

    # cl_001 should be reclassified to 佣金计算
    assert report["risks"][0]["risk_category"] == "佣金计算"
    # missing clause should be added as high risk
    assert len(report["risks"]) == 2
    assert report["risks"][1]["risk_level"] == "high"
    assert report["risks"][1]["risk_category"] == "客户归属"
    # summary should be correct
    assert report["summary"]["total_risks"] == 2
    assert report["summary"]["high"] == 2
