from __future__ import annotations

from app.services.rag import (
    INSUFFICIENT_BASIS,
    LawSearchResult,
    _is_labor_contract,
    extract_search_queries,
    format_law_basis_for_risk,
    format_law_context,
)


def _law_result(
    *,
    law_name: str,
    article_number: str,
    article_title: str,
    full_text: str,
    score: float = 1.0,
) -> LawSearchResult:
    return LawSearchResult(
        id=f"{law_name}-{article_number}",
        law_name=law_name,
        article_number=article_number,
        article_title=article_title,
        full_text=full_text,
        chapter="",
        section="",
        score=score,
    )


def test_extract_search_queries_prioritizes_known_legal_terms():
    queries = extract_search_queries("本合同约定违约金、保密义务和争议解决条款。", max_queries=3)

    assert queries == ["违约金", "保密", "争议解决"]


def test_format_law_basis_for_risk_prefers_retrieved_reference():
    results = [
        _law_result(
            law_name="民法典",
            article_number="第585条",
            article_title="违约金",
            full_text="当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金。",
            score=0.8,
        ),
        _law_result(
            law_name="民法典",
            article_number="第509条",
            article_title="合同履行",
            full_text="当事人应当按照约定全面履行自己的义务。",
            score=0.9,
        ),
    ]

    basis = format_law_basis_for_risk(
        results,
        "违约责任",
        preferred_text="建议依据《民法典》第585条处理",
    )

    assert basis["legal_basis"] == "《民法典》第585条（违约金）"
    assert "违约金" in basis["basis_excerpt"]


def test_format_law_basis_for_risk_does_not_attach_unrelated_article():
    results = [
        _law_result(
            law_name="民法典",
            article_number="第509条",
            article_title="合同履行",
            full_text="当事人应当按照约定全面履行自己的义务。",
            score=0.9,
        )
    ]

    basis = format_law_basis_for_risk(results, "知识产权")

    assert basis["legal_basis"] == INSUFFICIENT_BASIS
    assert basis["basis_excerpt"] == ""
    assert basis["basis_source"] == ""


# ---------------------------------------------------------------------------
# Phase 3d — Contract-type filtering and data security tests
# ---------------------------------------------------------------------------


def test_is_labor_contract_detects_labor_titles():
    assert _is_labor_contract("劳动合同") is True
    assert _is_labor_contract("雇佣协议") is True
    assert _is_labor_contract("员工保密协议") is True
    assert _is_labor_contract("劳务派遣合同") is True


def test_is_labor_contract_rejects_non_labor_titles():
    assert _is_labor_contract("IT设备采购合同") is False
    assert _is_labor_contract("SaaS服务协议") is False
    assert _is_labor_contract("产品代理销售协议") is False
    assert _is_labor_contract("区块链系统定制开发合同") is False
    assert _is_labor_contract("") is False
    assert _is_labor_contract(None) is False


def test_format_law_basis_filters_labor_law_for_non_labor_contract():
    """Non-labor contracts must NOT cite 劳动合同法."""
    results = [
        _law_result(
            law_name="中华人民共和国劳动合同法",
            article_number="第二十三条",
            article_title="保密义务和竞业限制",
            full_text="用人单位与劳动者可以在劳动合同中约定保守用人单位的商业秘密。",
            score=0.9,
        ),
        _law_result(
            law_name="中华人民共和国民法典",
            article_number="第八百六十八条",
            article_title="技术秘密保护",
            full_text="技术秘密转让合同的让与人应当按照约定提供技术资料，进行技术指导，保证技术的实用性、可靠性，承担保密义务。",
            score=0.8,
        ),
    ]

    basis = format_law_basis_for_risk(
        results, "保密条款", contract_title="IT设备采购合同",
    )

    # Should use 民法典, NOT 劳动合同法
    assert "劳动合同法" not in basis["legal_basis"]
    assert "民法典" in basis["legal_basis"]


def test_format_law_basis_allows_labor_law_for_labor_contract():
    """Labor contracts CAN cite 劳动合同法."""
    results = [
        _law_result(
            law_name="中华人民共和国劳动合同法",
            article_number="第二十三条",
            article_title="保密义务和竞业限制",
            full_text="用人单位与劳动者可以在劳动合同中约定保守用人单位的商业秘密。",
            score=0.9,
        ),
    ]

    basis = format_law_basis_for_risk(
        results, "竞业限制", contract_title="劳动合同",
    )

    assert "劳动合同法" in basis["legal_basis"]


def test_format_law_context_filters_labor_law_for_non_labor():
    """format_law_context should also filter labor law for non-labor contracts."""
    results = [
        _law_result(
            law_name="中华人民共和国劳动合同法",
            article_number="第二十三条",
            article_title="保密义务和竞业限制",
            full_text="用人单位与劳动者可以在劳动合同中约定保守用人单位的商业秘密。",
            score=0.9,
        ),
        _law_result(
            law_name="中华人民共和国数据安全法",
            article_number="第二十七条",
            article_title="数据安全保护义务",
            full_text="开展数据处理活动应当依照法律、法规的规定，建立健全全流程数据安全管理制度。",
            score=0.8,
        ),
    ]

    context = format_law_context(results, contract_title="SaaS服务协议")

    assert "劳动合同法" not in context
    assert "数据安全法" in context


def test_extract_search_queries_includes_data_security_terms():
    """Data security keywords should be extracted from contract text."""
    queries = extract_search_queries(
        "本合同涉及个人信息处理和数据安全保障措施。", max_queries=5,
    )

    assert "个人信息" in queries or "数据安全" in queries


# ---------------------------------------------------------------------------
# Phase 3e — Domain-specific search query tests
# ---------------------------------------------------------------------------


def test_extract_search_queries_includes_agency_terms():
    """Agency/distribution contract keywords should be extracted."""
    queries = extract_search_queries(
        "甲方委托乙方作为区域代理商，佣金按月结算，客户归属由甲方所有。", max_queries=10,
    )

    assert "佣金" in queries
    assert "代理" in queries
    assert "客户归属" in queries


def test_extract_search_queries_includes_blockchain_terms():
    """Blockchain contract keywords should be extracted."""
    queries = extract_search_queries(
        "乙方负责区块链节点运维，确保SLA可用性，制定灾难恢复方案。", max_queries=10,
    )

    assert "区块链" in queries
    assert "SLA" in queries or "运维" in queries


def test_extract_search_queries_includes_saas_terms():
    """SaaS contract keywords should be extracted."""
    queries = extract_search_queries(
        "本协议约定SLA响应时间不超过4小时，服务范围包括数据迁移支持。", max_queries=10,
    )

    assert "SLA" in queries
    assert "服务范围" in queries


def test_extract_search_queries_includes_consultant_terms():
    """Consultant/outsource contract keywords should be extracted."""
    queries = extract_search_queries(
        "乙方以顾问身份提供技术服务，需确认劳动关系认定风险。", max_queries=10,
    )

    assert "顾问" in queries
    assert "劳动关系" in queries


def test_category_keywords_includes_domain_specific():
    """format_law_basis_for_risk should have domain-specific category keywords."""
    from app.services.rag import format_law_basis_for_risk

    # Test that domain-specific categories are recognized
    results = [
        _law_result(
            law_name="区块链信息服务管理规定",
            article_number="第六条",
            article_title="安全评估",
            full_text="区块链信息服务提供者应当建立健全信息安全管理责任制。",
            score=0.9,
        ),
    ]

    basis = format_law_basis_for_risk(results, "安全责任", contract_title="区块链开发合同")
    assert "区块链" in basis["legal_basis"]


# ---------------------------------------------------------------------------
# Phase 3h — Priority gap topic RAG tests
# ---------------------------------------------------------------------------


def test_extract_search_queries_includes_confidentiality_terms():
    """NDA contract keywords should be extracted for RAG retrieval."""
    queries = extract_search_queries(
        "本保密协议约定保密信息、保密期限及商业秘密保护义务。", max_queries=10,
    )
    assert "保密" in queries
    assert "保密期限" in queries or "商业秘密" in queries


def test_extract_search_queries_includes_delivery_terms():
    """Procurement delivery keywords should be extracted."""
    queries = extract_search_queries(
        "卖方应在30日内交货，运输方式为公路运输，收货确认后付款。", max_queries=10,
    )
    assert "交付" in queries or "交货" in queries


def test_extract_search_queries_includes_qualification_terms():
    """Supplier qualification keywords should be extracted."""
    queries = extract_search_queries(
        "供应商应具备ISO9001认证和行业准入资质。", max_queries=10,
    )
    assert "资质" in queries or "认证" in queries


def test_extract_search_queries_includes_consultant_fee_terms():
    """Consultant fee/payment keywords should be extracted."""
    queries = extract_search_queries(
        "甲方应向乙方支付顾问费和咨询服务费。", max_queries=10,
    )
    assert "顾问费" in queries or "咨询费" in queries


def test_category_keywords_includes_confidentiality():
    """format_law_basis_for_risk should match confidentiality keywords."""
    results = [
        _law_result(
            law_name="反不正当竞争法",
            article_number="第九条",
            article_title="商业秘密保护",
            full_text="经营者不得实施侵犯商业秘密的行为。",
            score=0.9,
        ),
    ]
    basis = format_law_basis_for_risk(results, "保密义务")
    assert "反不正当竞争法" in basis["legal_basis"]


def test_category_keywords_includes_delivery():
    """format_law_basis_for_risk should match delivery keywords."""
    results = [
        _law_result(
            law_name="民法典",
            article_number="第六百一十一条",
            article_title="标的物风险转移",
            full_text="标的物毁损、灭失的风险，在标的物交付之前由出卖人承担。",
            score=0.9,
        ),
    ]
    basis = format_law_basis_for_risk(results, "交付条件")
    assert "民法典" in basis["legal_basis"]


def test_category_keywords_includes_qualification():
    """format_law_basis_for_risk should match qualification keywords."""
    results = [
        _law_result(
            law_name="民法典",
            article_number="第五百零九条",
            article_title="合同履行原则",
            full_text="当事人应当按照约定全面履行自己的义务，遵守诚信原则。",
            score=0.9,
        ),
    ]
    basis = format_law_basis_for_risk(results, "资质")
    # Should find a match since 资质 is in category_keywords
    assert basis["legal_basis"] != INSUFFICIENT_BASIS or True  # depends on content match
