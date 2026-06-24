"""RAG retrieval service — legal basis search using PostgreSQL full-text search.

Phase 3: Minimal RAG for law article retrieval.
Uses PostgreSQL's built-in tsvector + tsquery for keyword-based search.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("contractguard.rag")

INSUFFICIENT_BASIS = "依据不足，基于法理分析"

# Phase 3d: Contract-type-based law filtering to prevent mis-citation
_LABOR_CONTRACT_KEYWORDS = ["劳动", "雇佣", "用工", "员工", "人事", "劳务"]
# Non-labor contracts must NOT cite these laws
_NON_LABOR_FORBIDDEN_LAWS = {"中华人民共和国劳动合同法"}


def _is_labor_contract(contract_title: str) -> bool:
    """Check if a contract is a labor/employment contract based on title."""
    if not contract_title:
        return False
    return any(kw in contract_title for kw in _LABOR_CONTRACT_KEYWORDS)


@dataclass
class LawSearchResult:
    """A single law article search result."""

    id: str
    law_name: str
    article_number: str
    article_title: str
    full_text: str
    chapter: str
    section: str
    score: float


def extract_search_queries(contract_text: str, max_queries: int = 5) -> list[str]:
    """Extract search queries from contract text for RAG retrieval.

    Strategy: identify key legal terms and contract clauses that are likely
    to have corresponding law articles.
    """
    # High-priority legal terms for contract review
    legal_terms = [
        "违约金", "违约责任", "损害赔偿",
        "格式条款", "免责条款",
        "合同解除", "合同变更",
        "质量标准", "验收", "瑕疵",
        "付款", "价款", "报酬",
        "知识产权", "保密", "竞业限制",
        "不可抗力",
        "定金", "预付款",
        "交付", "风险转移",
        "争议解决", "仲裁", "管辖",
        "试用期", "劳动报酬", "社会保险",
        "技术开发", "技术秘密",
        "情势变更",
        "缔约过失",
        "同时履行", "不安抗辩",
        # Phase 3d: data security terms
        "个人信息", "数据安全", "数据保护", "网络安全",
        "数据泄露", "数据出境", "信息安全",
        # Phase 3e: domain-specific terms for low-recall samples
        "佣金", "代理", "经销", "培训",
        "客户归属", "客户数据", "客户信息",
        "区域保护", "排他性", "最低销售额", "回款周期",
        "安全责任", "安全事件", "安全审计",
        "技术方案", "技术路线", "技术文档",
        "运维", "SLA", "灾难恢复", "业务连续",
        "服务范围", "服务标准", "服务期限",
        "响应时间", "故障", "可用性",
        "区块链", "智能合约", "节点",
        "顾问", "外包", "兼职",
        "社保", "工伤", "劳动关系",
        "商业秘密", "反不正当竞争",
        # Phase 3f: agency-specific terms
        "销售指标", "业绩考核", "KPI", "窜货", "渠道冲突",
        "代理权", "代理佣金", "代理期限", "代理终止",
        "市场推广", "品牌使用", "商标许可",
        # Phase 3f: SaaS / tech-service / procurement terms
        "服务质量", "服务标准", "服务水平",
        "系统可用", "故障", "恢复时间",
        "数据备份", "数据恢复", "数据导出",
        "供应商", "供应链", "原材料",
        "退换货", "质保期", "保修",
        "资质", "许可", "认证", "准入",
        "运输", "保险", "风险转移",
        "单方变更", "自动续约", "格式条款",
        "验收标准", "验收流程",
        # Phase 3h: priority gap topics
        "保密信息", "保密期限", "商业秘密", "机密信息",
        "交货", "交期", "运输方式", "收货确认",
        "安全认证", "行业准入", "经营资质",
        "顾问费", "服务费", "咨询费", "报酬",
        "库存", "平台规则", "数据归属",
    ]

    # Find which legal terms appear in the contract text
    found_terms = []
    for term in legal_terms:
        if term in contract_text:
            found_terms.append(term)

    # If we found specific terms, use them as queries
    if found_terms:
        # Prioritize by relevance (order in the list)
        queries = found_terms[:max_queries]
    else:
        # Fallback: extract sentences that look like clause content
        # Look for sentences with numbers, percentages, or legal keywords
        sentences = re.split(r'[。；\n]', contract_text)
        relevant = []
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and len(s) < 200:
                # Check for legal-relevant content
                if any(kw in s for kw in ["应当", "不得", "可以", "约定", "责任", "义务", "权利"]):
                    relevant.append(s[:100])  # Truncate for search
        queries = relevant[:max_queries]

    # Always include a general contract review query
    if not queries:
        queries = ["合同 权利 义务 违约责任"]

    logger.info("rag.queries", extra={"queries": queries, "found_terms": found_terms[:10]})
    return queries


async def search_law_articles(
    session: AsyncSession,
    queries: list[str],
    top_k: int = 10,
) -> list[LawSearchResult]:
    """Search law articles using PostgreSQL full-text search.

    Args:
        session: Database session.
        queries: List of search queries (extracted from contract text).
        top_k: Maximum number of results to return.

    Returns:
        List of LawSearchResult, ranked by relevance.
    """
    if not queries:
        return []

    # Build OR query from all search terms
    # Use plainto_tsquery for each query, then combine with OR
    query_conditions = []
    params: dict[str, Any] = {}
    for i, q in enumerate(queries):
        param_name = f"q{i}"
        query_conditions.append(
            f"search_vector @@ plainto_tsquery('simple', :{param_name})"
        )
        params[param_name] = q

    where_clause = " OR ".join(query_conditions)

    # Rank by number of matching queries and text length (prefer specific articles)
    sql = f"""
        SELECT
            id::text,
            law_name,
            article_number,
            COALESCE(article_title, '') as article_title,
            full_text,
            COALESCE(chapter, '') as chapter,
            COALESCE(section, '') as section,
            ts_rank(search_vector, q) as score
        FROM law_articles,
             plainto_tsquery('simple', :rank_query) q
        WHERE {where_clause}
        ORDER BY score DESC, length(full_text) ASC
        LIMIT :limit
    """

    # Use the first query for ranking, but match on all
    params["rank_query"] = queries[0] if queries else ""
    params["limit"] = top_k

    try:
        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        results = []
        seen = set()
        for row in rows:
            key = f"{row[1]}_{row[2]}"
            if key in seen:
                continue
            seen.add(key)
            results.append(LawSearchResult(
                id=row[0],
                law_name=row[1],
                article_number=row[2],
                article_title=row[3],
                full_text=row[4],
                chapter=row[5],
                section=row[6],
                score=float(row[7]),
            ))

        logger.info("rag.search", extra={
            "queries": queries,
            "total_found": len(results),
            "top_results": [
                {"law": r.law_name, "article": r.article_number, "score": r.score}
                for r in results[:3]
            ],
        })
        return results

    except Exception as exc:
        logger.error("rag.search_error", extra={"error": str(exc), "queries": queries})
        return []


def format_law_context(
    results: list[LawSearchResult],
    max_chars: int = 8000,
    contract_title: str = "",
) -> str:
    """Format search results into a context string for LLM injection.

    Args:
        results: Search results from search_law_articles.
        max_chars: Maximum character limit for the context.
        contract_title: Contract title for type-based law filtering.

    Returns:
        Formatted string with law articles for LLM context.
    """
    if not results:
        return ""

    # Phase 3d: Filter out forbidden laws for non-labor contracts
    is_labor = _is_labor_contract(contract_title)
    if not is_labor:
        results = [r for r in results if r.law_name not in _NON_LABOR_FORBIDDEN_LAWS]

    if not results:
        return ""

    parts = ["以下是与合同内容相关的法律法规条文，请在分析时参考：\n"]
    current_len = len(parts[0])

    for r in results:
        article_text = (
            f"【{r.law_name}】{r.article_number}"
            f"{' ' + r.article_title if r.article_title else ''}\n"
            f"{r.full_text}\n"
        )
        if current_len + len(article_text) > max_chars:
            break
        parts.append(article_text)
        current_len += len(article_text)

    return "\n".join(parts)


def format_law_basis_for_risk(
    results: list[LawSearchResult],
    risk_category: str,
    preferred_text: str = "",
    max_results: int = 2,
    contract_title: str = "",
) -> dict[str, str]:
    """Select the most relevant law articles for a specific risk.

    Args:
        results: All search results.
        risk_category: The risk category (e.g., "违约责任", "付款条件").
        max_results: Max articles to return per risk.
        contract_title: Contract title for type-based law filtering.

    Returns:
        Dict with legal_basis, basis_excerpt, basis_source.
    """
    # Phase 3d: Filter out forbidden laws based on contract type
    is_labor = _is_labor_contract(contract_title)
    if not is_labor:
        results = [r for r in results if r.law_name not in _NON_LABOR_FORBIDDEN_LAWS]

    if not results:
        return {
            "legal_basis": INSUFFICIENT_BASIS,
            "basis_excerpt": "",
            "basis_source": "",
        }

    # Try to find results that match the risk category
    category_keywords = {
        "违约责任": ["违约金", "违约", "损害赔偿", "赔偿损失"],
        "付款条件": ["付款", "价款", "报酬", "预付", "佣金"],
        "质量标准": ["质量", "瑕疵", "验收", "标的物"],
        "知识产权": ["知识产权", "专利", "技术秘密", "著作权"],
        "保密条款": ["保密", "商业秘密"],
        "竞业限制": ["竞业限制", "竞业"],
        "合同解除": ["解除合同", "解除"],
        "争议解决": ["争议", "仲裁", "管辖"],
        "格式条款": ["格式条款"],
        "不可抗力": ["不可抗力"],
        "交付条款": ["交付", "风险转移"],
        # Phase 3e: domain-specific risk categories
        "数据安全": ["数据安全", "个人信息", "网络安全", "数据保护"],
        "服务范围": ["服务范围", "合作范围", "委托"],
        "合规风险": ["合规", "监管", "资质", "许可"],
        "安全责任": ["安全", "责任", "事故"],
        "运营管理": ["运维", "SLA", "可用性", "灾难恢复"],
        "技术管理": ["技术方案", "技术路线", "验收标准"],
        "佣金计算": ["佣金", "报酬", "价款"],
        "培训义务": ["培训", "指导", "支持"],
        "客户归属": ["客户", "客户数据", "客户信息"],
        "劳动关系": ["劳动关系", "劳动报酬", "社会保险", "工伤"],
        "响应时间": ["响应", "故障", "恢复", "可用"],
        "SLA": ["服务等级", "SLA", "可用性"],
        "不公平条款": ["格式条款", "免责", "单方变更"],
        "供应链风险": ["供应商", "供应链", "原材料"],
        "交付条件": ["交付", "交货", "运输", "风险转移"],
        "业务连续性": ["业务连续", "灾难恢复", "应急"],
        "合同完整性": ["完整性", "缺失", "遗漏"],
        "保密义务": ["保密", "商业秘密", "机密", "保密信息", "保密期限"],
        "交付条件": ["交付", "交货", "交期", "运输", "风险转移", "收货"],
        "付款条件": ["付款", "价款", "报酬", "结算", "预付", "顾问费", "服务费", "咨询费"],
        "资质": ["资质", "许可", "认证", "准入", "经营资质", "安全认证"],
        "平台规则": ["平台", "规则", "数据归属"],
        "库存管理": ["库存", "存货", "退换货"],
    }

    keywords = category_keywords.get(risk_category, [risk_category])

    selected: list[LawSearchResult] = []

    preferred_text = preferred_text.strip()
    if preferred_text:
        preferred_matches = []
        for r in results:
            # Phase 3d: skip forbidden laws in preferred matching too
            if not is_labor and r.law_name in _NON_LABOR_FORBIDDEN_LAWS:
                continue
            reference = f"《{r.law_name}》{r.article_number}"
            if reference in preferred_text or f"{r.law_name}{r.article_number}" in preferred_text:
                preferred_matches.append(r)
        if preferred_matches:
            selected = preferred_matches[:max_results]

    # Score results by keyword match
    if not selected:
        scored = []
        for r in results:
            match_score = 0
            for kw in keywords:
                if kw in r.full_text or kw in (r.article_title or "") or kw in (r.section or ""):
                    match_score += 1
            scored.append((r, match_score))

        scored.sort(key=lambda x: (x[1], x[0].score), reverse=True)
        selected = [s[0] for s in scored[:max_results] if s[1] > 0]

    if not selected:
        return {
            "legal_basis": INSUFFICIENT_BASIS,
            "basis_excerpt": "",
            "basis_source": "",
        }

    # Format output
    basis_parts = []
    excerpt_parts = []
    source_parts = []

    for r in selected:
        source = f"《{r.law_name}》{r.article_number}"
        if r.article_title:
            source += f"（{r.article_title}）"
        basis_parts.append(source)
        # Truncate excerpt to 200 chars
        excerpt = r.full_text[:200] + ("..." if len(r.full_text) > 200 else "")
        excerpt_parts.append(excerpt)
        source_parts.append(source)

    return {
        "legal_basis": "；".join(basis_parts),
        "basis_excerpt": "\n".join(excerpt_parts),
        "basis_source": "；".join(source_parts),
    }
