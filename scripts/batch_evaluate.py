"""黄金样例自动评测器 — 对比真实审查结果与黄金预期，输出评测报告。

用法：
    python scripts/batch_evaluate.py              # 全历史模式（所有 run）
    python scripts/batch_evaluate.py --latest-only # 仅最新成功 run

输出（全历史模式）：
    07-testing/generated/batch-01/<sample>/evaluation_run_01.json
    07-testing/generated/batch-01/<sample>/evaluation_summary.md
    07-testing/generated/batch-01/_summary/evaluation_summary.json
    07-testing/generated/batch-01/_summary/evaluation_summary.csv
    07-testing/generated/batch-01/_summary/evaluation_report.md

输出（latest-only 模式，额外生成，不覆盖全历史报告）：
    07-testing/generated/batch-01/_summary/latest_only_evaluation_summary.json
    07-testing/generated/batch-01/_summary/latest_only_evaluation_summary.csv
    07-testing/generated/batch-01/_summary/latest_only_evaluation_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

BATCH_DIR = Path(__file__).resolve().parents[1] / "07-testing" / "generated" / "batch-01"
SUMMARY_DIR = BATCH_DIR / "_summary"
RUN_PREFIXES = ["review_run_01", "review_run_02", "review_run_03", "review_run_04", "review_run_05"]

# ─── 同义归并表 ───────────────────────────────────────────────────────────────
# key = 规范名，value = 可能的别名列表（含自身）
SYNONYM_MAP: dict[str, list[str]] = {
    "付款条件": ["付款条件", "回款条件", "付款方式", "支付条件", "结算条件", "付款节点", "付款",
               "payment_terms_favor_service_provider", "payment_decoupled_from_performance",
               "payment_milestone_mismatch", "payment", "price", "价格", "定价", "费用",
               "费用与支付", "价格条款", "价格成本不透明", "费用结构"],
    "违约责任": ["违约责任", "违约条款", "违约赔偿", "违约", "违约金",
               "penalty_rate_high", "delay_penalty_disproportionate",
               "liability_too_light", "liability_cap_too_low",
               "liability_exemption_too_broad", "违约金不对等", "赔偿"],
    "验收标准": ["验收标准", "验收条件", "验收条款", "验收", "验收流程",
               "acceptance_period_too_long", "acceptance_standard_subjective",
               "验收", "验收标准", "验收流程"],
    "知识产权": ["知识产权", "知识产权归属", "IP权利归属", "著作权归属", "专利归属", "知识产权条款",
               "ip_contradiction", "ip_ownership_contradiction",
               "知识产权归属", "知识产权使用", "知识产权侵权", "知识产权"],
    "保密义务": ["保密义务", "保密范围", "保密条款", "保密", "保密期限", "信息返还", "保密责任",
               "confidentiality_insufficient", "confidentiality_period_too_short",
               "保密义务", "保密范围", "保密期限", "信息返还"],
    "管辖法院": ["管辖法院", "争议解决", "仲裁条款", "管辖", "法律适用", "争议解决方式",
               "jurisdiction_favorable_to_one_party"],
    "合作范围": ["合作范围", "服务范围", "合作内容", "服务内容", "服务内容与范围", "代理范围", "代理区域",
               "scope_ambiguity", "deliverable_scope_vague", "范围模糊", "代理范围"],
    "质量标准": ["质量标准", "质量要求", "质量保证", "质保条款", "质保服务", "质保", "质保期"],
    "交付条件": ["交付条件", "交付时间", "交货时间", "交付"],
    "竞业限制": ["竞业限制", "竞业禁止", "不竞争", "竞业限制"],
    "解约条件": ["解约条件", "解除条件", "终止条件", "合同解除", "合同终止", "合同终止与解除", "合同解除终止"],
    "赔偿责任": ["赔偿责任", "赔偿", "损害赔偿", "赔偿上限", "data_loss_compensation_too_low",
               "remedy_insufficient", "赔偿金额不足"],
    "服务期限": ["服务期限", "合同期限", "合作期限", "合同期限与终止", "合同有效期"],
    "数据安全": ["数据安全", "数据保护", "信息安全", "隐私",
               "data_security_insufficient", "data_security_weak",
               "data_ownership_ambiguity", "data_return_mechanism_weak",
               "数据安全与信息安全", "数据安全", "数据所有权", "数据泄露赔偿", "数据迁移",
               "数据安全与个人信息保护", "个人信息保护", "个人信息"],
    "人员管理": ["人员管理", "人员要求", "人员", "personnel_replacement_mechanism_weak",
               "staff_turnover_metric_insufficient", "人员更替"],
    "排他性": ["排他性", "独家", "排他"],
    "通知条款": ["通知条款", "通知", "通知与送达"],
    "不可抗力": ["不可抗力"],
    "担保条款": ["担保条款", "担保"],
    "审计权": ["审计权", "审计"],
    "保险": ["保险", "insurance"],
    "转让限制": ["转让限制", "转让", "分包", "subcontracting_restriction_unclear"],
    "培训": ["培训", "培训与支持"],
    "文档交付": ["文档交付", "文档", "交付物"],
    "SLA": ["sla_ambiguity", "sla_metric_incomplete", "服务等级", "SLA"],
    "响应时间": ["response_time_ambiguity", "响应时间", "响应时效"],
    "资质": ["qualification_ambiguity", "资质", "资质要求"],
    "安全责任": ["security_responsibility_unclear", "安全责任", "安全", "智能合约安全", "合约安全"],
    "风险提示": ["risk_warning_obligation_weak", "风险提示", "风险告知"],
    "业务连续性": ["migration_window_business_continuity_conflict", "业务连续性", "迁移"],
    "云计算资源": ["cloud_resource_cost_unclear", "云计算资源", "云资源"],
    "覆盖率": ["coverage_rate_undefined", "覆盖率"],
    "逻辑矛盾": ["逻辑矛盾", "逻辑冲突", "矛盾"],
    "条款缺失": ["missing_clause", "条款缺失", "缺失"],
    "不公平条款": ["unfair_terms", "不公平条款", "单方有利", "不公平格式条款", "格式条款不公平"],
    "供应链风险": ["供应链风险", "供应", "供应商"],
    "合同完整性": ["合同完整性", "完整性", "合同完整", "合同完整性缺失"],
    "合规风险": ["合规风险", "合规", "合规性", "监管合规", "监管"],
    "设备管理": ["设备管理", "设备", "硬件"],
    "责任限制": ["责任限制", "责任", "免责", "责任上限"],
    "需求变更": ["需求变更", "变更管理", "需求管理"],
    "客户归属": ["客户归属", "客户管理", "客户数据", "客户关系"],
    "佣金计算": ["佣金计算", "佣金", "提成", "回扣"],
    "销售指标": ["销售指标", "业绩考核", "KPI", "最低销售额", "销售目标", "业绩指标"],
    "区域保护": ["区域保护", "排他性区域", "独家代理区域", "区域排他"],
    "其他": ["其他", "其他条款", "一般条款"],
}

# 反向索引：别名 → 规范名
_ALIASES_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SYNONYM_MAP.items():
    for alias in aliases:
        _ALIASES_TO_CANONICAL[alias] = canonical


def normalize_category(raw: str) -> str:
    """将风险类别归一到规范名。"""
    if not raw:
        return "其他"
    raw = raw.strip()
    if not raw:
        return "其他"
    # 直接匹配
    if raw in _ALIASES_TO_CANONICAL:
        return _ALIASES_TO_CANONICAL[raw]
    # 子串匹配：如果 raw 包含某个别名，或某个别名包含 raw
    for alias, canonical in _ALIASES_TO_CANONICAL.items():
        if len(alias) >= 2 and (alias in raw or raw in alias):
            return canonical
    return raw


# ─── severity 归一化 ─────────────────────────────────────────────────────────
_SEVERITY_CN_TO_EN: dict[str, str] = {
    "高": "high",
    "中": "medium",
    "低": "low",
}


def normalize_severity(raw: str) -> str:
    """将 severity 归一到英文标准值 (high/medium/low)。

    支持中文（高/中/低）和英文（high/medium/low），忽略大小写。
    无法识别时返回空字符串。
    """
    if not raw:
        return ""
    raw = raw.strip()
    if not raw:
        return ""
    lower = raw.lower()
    if lower in ("high", "medium", "low"):
        return lower
    return _SEVERITY_CN_TO_EN.get(raw, "")


# ─── 标题→类别关键词提取 ──────────────────────────────────────────────────────
# 用于从 expected_risks 的 title 字段推断风险类别

_TITLE_KEYWORDS: dict[str, list[str]] = {
    "付款条件": ["付款", "支付", "回款", "结算", "价格", "费用", "成本", "里程碑"],
    "违约责任": ["违约", "赔偿", "罚", "滞纳金", "违约金"],
    "验收标准": ["验收", "检验", "交付标准"],
    "知识产权": ["知识产权", "著作权", "专利", "版权", "IP"],
    "保密义务": ["保密", "机密", "信息返还", "保密期限"],
    "管辖法院": ["管辖", "仲裁", "争议", "法律适用"],
    "合作范围": ["范围", "内容", "服务范围", "代理"],
    "质量标准": ["质量", "标准", "质保"],
    "交付条件": ["交付", "交货", "发货"],
    "竞业限制": ["竞业", "不竞争"],
    "解约条件": ["解约", "解除", "终止"],
    "数据安全": ["数据安全", "数据泄露", "数据保护", "数据", "隐私", "信息保护"],
    "人员管理": ["人员", "员工", "团队"],
    "SLA": ["SLA", "服务等级", "可用性"],
    "响应时间": ["响应", "时效", "时间"],
    "资质": ["资质", "许可", "认证"],
    "转让限制": ["转让", "分包"],
    "逻辑矛盾": ["矛盾", "冲突", "不一致"],
    "条款缺失": ["缺失", "缺少", "遗漏"],
    "不公平条款": ["不公平", "单方", "不对等", "格式条款"],
    "需求变更": ["需求变更", "变更", "需求"],
    "客户归属": ["客户归属", "客户", "客户数据"],
    "佣金计算": ["佣金", "提成", "回扣"],
    "智能合约安全": ["智能合约", "合约安全", "区块链安全"],
}


def infer_category_from_title(title: str) -> str:
    """从风险标题推断风险类别。优先匹配更长的关键词。"""
    if not title:
        return "其他"
    # 收集所有匹配，选最长关键词命中的类别
    best_match = None
    best_len = 0
    for category, keywords in _TITLE_KEYWORDS.items():
        for kw in keywords:
            if kw in title and len(kw) > best_len:
                best_match = category
                best_len = len(kw)
    return best_match or "其他"


def _safe_load_json(path: Path) -> dict | None:
    """安全加载 JSON，解析失败返回 None。尝试 UTF-8 和系统默认编码。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        except Exception:
            return None
    return None


def get_latest_successful_run_prefix(sample_dir: Path) -> str | None:
    """获取样本目录下最新一次成功 run 的前缀（如 'review_run_06'）。

    扫描所有 review_run_XX.json，按编号倒序，返回第一个 success=True 的前缀。
    若无成功 run 则返回 None。
    """
    prefixes = _detect_run_prefixes(sample_dir)
    for prefix in reversed(prefixes):
        run_path = sample_dir / f"{prefix}.json"
        run_data = _safe_load_json(run_path)
        if run_data and run_data.get("success") and not run_data.get("error"):
            return prefix
    return None


# ─── 评测单次运行 ─────────────────────────────────────────────────────────────

def evaluate_run(
    sample_dir: Path,
    run_prefix: str,
    run_data: dict | None,
    expected_risks: dict | None,
    expected_missing: dict | None,
    expected_contradictions: dict | None,
    manifest: dict | None,
) -> dict:
    """对一次 review_run 做黄金样例评测。"""

    result: dict = {
        "sample_id": sample_dir.name,
        "review_run_file": f"{run_prefix}.json",
        "evaluated_at": datetime.now().isoformat(),
        "success": False,
        "expected_risk_topics": [],
        "detected_risk_topics": [],
        "expected_high_risk_topics": [],
        "detected_high_risk_topics": [],
        "missing_expected_topics": [],
        "unexpected_topics": [],
        "topic_recall": 0.0,
        "topic_precision": 0.0,
        "high_risk_recall": 0.0,
        "contradiction_hit": False,
        "contradiction_expected": 0,
        "contradiction_detected": 0,
        "missing_clause_hit": False,
        "missing_clause_expected": 0,
        "missing_clause_detected": 0,
        "legal_basis_coverage": 0.0,
        "overall_score": 0.0,
        "notes": "",
    }

    # ── 无运行文件 ──
    if not run_data or run_data.get("error"):
        result["notes"] = run_data.get("error", "无运行结果文件") if run_data else "无运行结果文件"
        return result

    if not run_data.get("success"):
        result["notes"] = f"审查失败: {run_data.get('error', '未知原因')}"
        return result

    result["success"] = True

    # ── 加载 raw 数据（如有）以获取更丰富的 risk_category ──
    raw_path = sample_dir / f"{run_prefix}_raw.json"
    raw_data = _safe_load_json(raw_path)

    # ── 提取期望风险主题 ──
    # expected_risks.json 使用 risk_type / severity 字段
    expected_topics: list[str] = []
    expected_high_topics: list[str] = []
    if expected_risks and "risks" in expected_risks:
        for r in expected_risks["risks"]:
            # 兼容 risk_type 和 risk_category 两种字段名
            raw_cat = r.get("risk_type") or r.get("risk_category") or ""
            cat = normalize_category(raw_cat)
            # 如果归一化后仍是英文标识符或"其他"，尝试从 title 推断
            if cat == "其他" or (cat and not any('一' <= c <= '鿿' for c in cat)):
                title = r.get("title", "")
                inferred = infer_category_from_title(title)
                if inferred != "其他":
                    cat = inferred
                elif title:
                    cat = normalize_category(title)
            expected_topics.append(cat)
            # 兼容 severity 和 risk_level 两种字段名，归一到英文标准值
            raw_level = r.get("severity") or r.get("risk_level") or ""
            level = normalize_severity(raw_level)
            if level == "high":
                expected_high_topics.append(cat)
    result["expected_risk_topics"] = sorted(set(expected_topics))
    result["expected_high_risk_topics"] = sorted(set(expected_high_topics))

    # ── 提取检测到的风险主题 ──
    # review_run_01_raw.json 使用 risk_category / risk_level 字段
    detected_topics: list[str] = []
    detected_high_topics: list[str] = []
    legal_basis_count = 0
    total_risks_with_basis = 0

    if raw_data and "risks" in raw_data:
        for r in raw_data["risks"]:
            cat = normalize_category(r.get("risk_category", ""))
            detected_topics.append(cat)
            if r.get("risk_level") == "high":
                detected_high_topics.append(cat)
            total_risks_with_basis += 1
            basis = r.get("legal_basis", "")
            if basis and "依据不足" not in basis and len(basis) > 3:
                legal_basis_count += 1
    elif run_data.get("risk_count") and run_data["risk_count"] > 0:
        # 无 raw 数据，只能用 summary 计数
        detected_topics = ["(无详细分类)"] * run_data["risk_count"]
        if run_data.get("high_count"):
            detected_high_topics = ["(无详细分类)"] * run_data["high_count"]

    result["detected_risk_topics"] = sorted(set(detected_topics))
    result["detected_high_risk_topics"] = sorted(set(detected_high_topics))

    # ── 主题级 Recall / Precision（基于规范名集合匹配） ──
    expected_set = set(expected_topics)
    detected_set = set(detected_topics)

    # 严格匹配
    strict_hits = expected_set & detected_set

    # 模糊匹配：期望主题是否被检测主题覆盖（检测到的某个主题是期望主题的同义词）
    # 由于已经 normalize，直接用集合交集
    if expected_set:
        result["topic_recall"] = round(len(strict_hits) / len(expected_set), 3)
    if detected_set:
        result["topic_precision"] = round(len(strict_hits) / len(detected_set), 3)

    result["missing_expected_topics"] = sorted(expected_set - detected_set)
    result["unexpected_topics"] = sorted(detected_set - expected_set)

    # ── 高风险 Recall ──
    expected_high_set = set(expected_high_topics)
    detected_high_set = set(detected_high_topics)
    high_hits = expected_high_set & detected_high_set
    if expected_high_set:
        result["high_risk_recall"] = round(len(high_hits) / len(expected_high_set), 3)

    # ── 矛盾命中 ──
    result["contradiction_expected"] = (expected_contradictions or {}).get("total_contradictions", 0)
    result["contradiction_detected"] = run_data.get("contradiction_count", 0) or 0
    if result["contradiction_expected"] > 0:
        result["contradiction_hit"] = result["contradiction_detected"] > 0

    # ── 缺失条款命中 ──
    result["missing_clause_expected"] = (expected_missing or {}).get("total_missing", 0)
    result["missing_clause_detected"] = run_data.get("missing_clause_count", 0) or 0
    if result["missing_clause_expected"] > 0:
        result["missing_clause_hit"] = result["missing_clause_detected"] > 0

    # ── 法条依据覆盖率 ──
    if total_risks_with_basis > 0:
        result["legal_basis_coverage"] = round(legal_basis_count / total_risks_with_basis, 3)

    # ── 综合评分 ──
    score_parts = []
    if expected_set:
        score_parts.append(result["topic_recall"] * 0.35)
    if expected_high_set:
        score_parts.append(result["high_risk_recall"] * 0.25)
    if result["contradiction_expected"] > 0:
        score_parts.append((1.0 if result["contradiction_hit"] else 0.0) * 0.15)
    if result["missing_clause_expected"] > 0:
        score_parts.append((1.0 if result["missing_clause_hit"] else 0.0) * 0.10)
    score_parts.append(result["legal_basis_coverage"] * 0.15)

    if score_parts:
        result["overall_score"] = round(sum(score_parts) / len(score_parts) * (len(score_parts) / 5), 3)
        # 归一到 0-1 范围（权重和 ≤ 1.0）
        weight_sum = 0
        if expected_set:
            weight_sum += 0.35
        if expected_high_set:
            weight_sum += 0.25
        if result["contradiction_expected"] > 0:
            weight_sum += 0.15
        if result["missing_clause_expected"] > 0:
            weight_sum += 0.10
        weight_sum += 0.15
        if weight_sum > 0:
            result["overall_score"] = round(sum(score_parts) / weight_sum, 3)

    return result


# ─── 评测单个样本 ─────────────────────────────────────────────────────────────

def _detect_run_prefixes(sample_dir: Path) -> list[str]:
    """动态检测样本目录下所有 review_run_XX.json（不含 _raw）。"""
    import glob as glob_mod
    existing = glob_mod.glob(str(sample_dir / "review_run_*.json"))
    prefixes = []
    for fp in existing:
        name = Path(fp).stem
        if not name.endswith("_raw"):
            prefixes.append(name)
    prefixes.sort()
    return prefixes


def evaluate_sample(sample_dir: Path) -> list[dict]:
    """评测一个样本目录的所有 review_run。"""

    manifest = _safe_load_json(sample_dir / "manifest.json")
    expected_risks = _safe_load_json(sample_dir / "expected_risks.json")
    expected_missing = _safe_load_json(sample_dir / "expected_missing_clauses.json")
    expected_contradictions = _safe_load_json(sample_dir / "expected_contradictions.json")

    # 动态检测所有 review_run_XX.json
    detected_prefixes = _detect_run_prefixes(sample_dir)
    # 合并静态列表 + 动态检测，去重
    all_prefixes = list(dict.fromkeys(RUN_PREFIXES + detected_prefixes))

    evaluations = []
    for prefix in all_prefixes:
        run_path = sample_dir / f"{prefix}.json"
        run_data = _safe_load_json(run_path) if run_path.exists() else None

        ev = evaluate_run(
            sample_dir=sample_dir,
            run_prefix=prefix,
            run_data=run_data,
            expected_risks=expected_risks,
            expected_missing=expected_missing,
            expected_contradictions=expected_contradictions,
            manifest=manifest,
        )
        evaluations.append(ev)

    return evaluations


# ─── 批次级汇总 ───────────────────────────────────────────────────────────────

def compute_batch_evaluation(all_evals: list[dict]) -> dict:
    """汇总所有评测结果。"""
    total = len(all_evals)
    evaluated = [e for e in all_evals if e["success"]]
    not_evaluated = [e for e in all_evals if not e["success"]]

    if not evaluated:
        return {
            "batch_name": "batch-01",
            "generated_at": datetime.now().isoformat(),
            "total_evaluations": total,
            "successful_evaluations": 0,
            "failed_evaluations": len(not_evaluated),
            "avg_topic_recall": 0.0,
            "avg_topic_precision": 0.0,
            "avg_high_risk_recall": 0.0,
            "avg_overall_score": 0.0,
            "avg_legal_basis_coverage": 0.0,
            "contradiction_hit_rate": 0.0,
            "missing_clause_hit_rate": 0.0,
            "risk_category_stats": {},
            "best_samples": [],
            "worst_samples": [],
            "high_risk_miss_stats": {},
        }

    # 平均指标
    avg_recall = round(sum(e["topic_recall"] for e in evaluated) / len(evaluated), 3)
    avg_precision = round(sum(e["topic_precision"] for e in evaluated) / len(evaluated), 3)
    avg_high_recall = round(sum(e["high_risk_recall"] for e in evaluated) / len(evaluated), 3)
    avg_score = round(sum(e["overall_score"] for e in evaluated) / len(evaluated), 3)
    avg_basis = round(sum(e["legal_basis_coverage"] for e in evaluated) / len(evaluated), 3)

    # 矛盾/缺失命中率
    contr_expected = [e for e in evaluated if e["contradiction_expected"] > 0]
    contr_hit = sum(1 for e in contr_expected if e["contradiction_hit"])
    contr_rate = round(contr_hit / len(contr_expected), 3) if contr_expected else 0.0

    miss_expected = [e for e in evaluated if e["missing_clause_expected"] > 0]
    miss_hit = sum(1 for e in miss_expected if e["missing_clause_hit"])
    miss_rate = round(miss_hit / len(miss_expected), 3) if miss_expected else 0.0

    # 风险类别统计：哪些类别最容易漏报
    category_miss: dict[str, int] = {}
    category_hit: dict[str, int] = {}
    for e in evaluated:
        for topic in e["missing_expected_topics"]:
            category_miss[topic] = category_miss.get(topic, 0) + 1
        for topic in e["expected_risk_topics"]:
            if topic not in e["missing_expected_topics"]:
                category_hit[topic] = category_hit.get(topic, 0) + 1

    category_stats = {}
    all_cats = set(category_miss.keys()) | set(category_hit.keys())
    for cat in sorted(all_cats):
        hits = category_hit.get(cat, 0)
        misses = category_miss.get(cat, 0)
        total_expects = hits + misses
        category_stats[cat] = {
            "expected": total_expects,
            "hit": hits,
            "missed": misses,
            "recall": round(hits / total_expects, 3) if total_expects > 0 else 0.0,
        }

    # 高风险类别漏报
    high_miss: dict[str, int] = {}
    for e in evaluated:
        for topic in e.get("missing_expected_topics", []):
            if topic in e.get("expected_high_risk_topics", []):
                high_miss[topic] = high_miss.get(topic, 0) + 1

    # 排序：最佳 / 最差
    sorted_by_score = sorted(evaluated, key=lambda e: e["overall_score"], reverse=True)
    best = [{"sample_id": e["sample_id"], "score": e["overall_score"]} for e in sorted_by_score[:5]]
    worst = [{"sample_id": e["sample_id"], "score": e["overall_score"]} for e in sorted_by_score[-5:]]

    return {
        "batch_name": "batch-01",
        "generated_at": datetime.now().isoformat(),
        "total_evaluations": total,
        "successful_evaluations": len(evaluated),
        "failed_evaluations": len(not_evaluated),
        "avg_topic_recall": avg_recall,
        "avg_topic_precision": avg_precision,
        "avg_high_risk_recall": avg_high_recall,
        "avg_overall_score": avg_score,
        "avg_legal_basis_coverage": avg_basis,
        "contradiction_hit_rate": contr_rate,
        "missing_clause_hit_rate": miss_rate,
        "risk_category_stats": category_stats,
        "high_risk_miss_stats": high_miss,
        "best_samples": best,
        "worst_samples": worst,
    }


# ─── 输出 ─────────────────────────────────────────────────────────────────────

def write_sample_evaluations(sample_dir: Path, evaluations: list[dict]) -> None:
    """写入单样本评测文件。"""
    for ev in evaluations:
        run_name = ev["review_run_file"].replace(".json", "")
        out_path = sample_dir / f"evaluation_{run_name}.json"
        out_path.write_text(json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")

    # 汇总 md
    lines = [f"# 评测汇总 — {sample_dir.name}", ""]
    for ev in evaluations:
        status = "✅ 成功" if ev["success"] else "❌ 跳过"
        lines.append(f"## {ev['review_run_file']}  {status}")
        lines.append("")
        if not ev["success"]:
            lines.append(f"> {ev['notes']}")
            lines.append("")
            continue
        lines.append(f"- 主题 Recall: **{ev['topic_recall']:.1%}**  |  Precision: {ev['topic_precision']:.1%}")
        lines.append(f"- 高风险 Recall: **{ev['high_risk_recall']:.1%}**")
        lines.append(f"- 矛盾命中: {'是' if ev['contradiction_hit'] else '否'}  (期望 {ev['contradiction_expected']}, 检出 {ev['contradiction_detected']})")
        lines.append(f"- 缺失条款命中: {'是' if ev['missing_clause_hit'] else '否'}  (期望 {ev['missing_clause_expected']}, 检出 {ev['missing_clause_detected']})")
        lines.append(f"- 法条依据覆盖率: {ev['legal_basis_coverage']:.1%}")
        lines.append(f"- **综合评分: {ev['overall_score']:.3f}**")
        if ev["missing_expected_topics"]:
            lines.append(f"- 漏报主题: {', '.join(ev['missing_expected_topics'])}")
        if ev["unexpected_topics"]:
            lines.append(f"- 多报主题: {', '.join(ev['unexpected_topics'])}")
        lines.append("")

    md_path = sample_dir / "evaluation_summary.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")


def write_batch_evaluation(batch_eval: dict, all_evals: list[dict]) -> None:
    """写入批次级评测文件。"""
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = SUMMARY_DIR / "evaluation_summary.json"
    json_path.write_text(json.dumps(batch_eval, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV — 每个成功评测一行
    csv_path = SUMMARY_DIR / "evaluation_summary.csv"
    successful = [e for e in all_evals if e["success"]]
    if successful:
        fields = [
            "sample_id", "review_run_file", "topic_recall", "topic_precision",
            "high_risk_recall", "contradiction_hit", "contradiction_expected", "contradiction_detected",
            "missing_clause_hit", "missing_clause_expected", "missing_clause_detected",
            "legal_basis_coverage", "overall_score",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(successful)

    # Markdown 报告
    lines = []
    lines.append("# 黄金样例评测报告 — batch-01")
    lines.append("")
    lines.append(f"> 生成时间：{batch_eval['generated_at']}")
    lines.append("")

    # 一、总览
    lines.append("## 一、评测总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 总评测数 | {batch_eval['total_evaluations']} |")
    lines.append(f"| 成功评测 | {batch_eval['successful_evaluations']} |")
    lines.append(f"| 跳过/失败 | {batch_eval['failed_evaluations']} |")
    lines.append(f"| 平均主题 Recall | {batch_eval['avg_topic_recall']:.1%} |")
    lines.append(f"| 平均主题 Precision | {batch_eval['avg_topic_precision']:.1%} |")
    lines.append(f"| 平均高风险 Recall | {batch_eval['avg_high_risk_recall']:.1%} |")
    lines.append(f"| 平均综合评分 | {batch_eval['avg_overall_score']:.3f} |")
    lines.append(f"| 平均法条依据覆盖率 | {batch_eval['avg_legal_basis_coverage']:.1%} |")
    lines.append(f"| 矛盾命中率 | {batch_eval['contradiction_hit_rate']:.1%} |")
    lines.append(f"| 缺失条款命中率 | {batch_eval['missing_clause_hit_rate']:.1%} |")
    lines.append("")

    # 二、命中率最高的合同
    lines.append("## 二、命中率最高的合同（Top 5）")
    lines.append("")
    if batch_eval["best_samples"]:
        lines.append("| 排名 | 样本 | 综合评分 |")
        lines.append("|---|---|---|")
        for i, s in enumerate(batch_eval["best_samples"], 1):
            lines.append(f"| {i} | {s['sample_id']} | {s['score']:.3f} |")
        lines.append("")

    # 三、漏报最多的合同
    lines.append("## 三、漏报最多的合同（Bottom 5）")
    lines.append("")
    if batch_eval["worst_samples"]:
        lines.append("| 排名 | 样本 | 综合评分 |")
        lines.append("|---|---|---|")
        for i, s in enumerate(batch_eval["worst_samples"], 1):
            lines.append(f"| {i} | {s['sample_id']} | {s['score']:.3f} |")
        lines.append("")

    # 四、风险类别漏报分析
    lines.append("## 四、风险类别漏报分析")
    lines.append("")
    cat_stats = batch_eval.get("risk_category_stats", {})
    if cat_stats:
        sorted_cats = sorted(cat_stats.items(), key=lambda x: x[1]["missed"], reverse=True)
        lines.append("| 风险类别 | 期望次数 | 命中 | 漏报 | Recall |")
        lines.append("|---|---|---|---|---|")
        for cat, st in sorted_cats:
            if st["expected"] > 0:
                lines.append(f"| {cat} | {st['expected']} | {st['hit']} | {st['missed']} | {st['recall']:.1%} |")
        lines.append("")

    # 五、高风险漏报
    lines.append("## 五、高风险类别漏报")
    lines.append("")
    high_miss = batch_eval.get("high_risk_miss_stats", {})
    if high_miss:
        lines.append("| 风险类别 | 漏报次数 |")
        lines.append("|---|---|")
        for cat, count in sorted(high_miss.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {cat} | {count} |")
        lines.append("")
    else:
        lines.append("无高风险漏报。")
        lines.append("")

    # 六、法条依据覆盖
    lines.append("## 六、法条依据覆盖分析")
    lines.append("")
    if successful:
        basis_sorted = sorted(successful, key=lambda e: e["legal_basis_coverage"])
        lines.append("### 覆盖最差的样本")
        lines.append("")
        lines.append("| 样本 | 法条覆盖率 | 综合评分 |")
        lines.append("|---|---|---|")
        for e in basis_sorted[:5]:
            lines.append(f"| {e['sample_id']} | {e['legal_basis_coverage']:.1%} | {e['overall_score']:.3f} |")
        lines.append("")
        lines.append("### 覆盖最好的样本")
        lines.append("")
        lines.append("| 样本 | 法条覆盖率 | 综合评分 |")
        lines.append("|---|---|---|")
        for e in basis_sorted[-5:]:
            lines.append(f"| {e['sample_id']} | {e['legal_basis_coverage']:.1%} | {e['overall_score']:.3f} |")
        lines.append("")

    # 七、复审建议
    lines.append("## 七、复审优先级建议")
    lines.append("")
    lines.append("以下样本最值得做 3 次复审（综合评分低 + 高风险漏报 + 法条覆盖差）：")
    lines.append("")
    if successful:
        priority = sorted(successful, key=lambda e: (
            (1 - e["overall_score"]) * 2
            + (1 - e["high_risk_recall"]) * 1.5
            + (1 - e["legal_basis_coverage"])
        ), reverse=True)
        lines.append("| 优先级 | 样本 | 综合评分 | 高风险Recall | 法条覆盖 | 理由 |")
        lines.append("|---|---|---|---|---|---|")
        for i, e in enumerate(priority[:10], 1):
            reasons = []
            if e["overall_score"] < 0.5:
                reasons.append("综合评分低")
            if e["high_risk_recall"] < 0.7:
                reasons.append("高风险漏报多")
            if e["legal_basis_coverage"] < 0.5:
                reasons.append("法条覆盖差")
            if e["contradiction_expected"] > 0 and not e["contradiction_hit"]:
                reasons.append("矛盾未命中")
            if not reasons:
                reasons.append("常规复审")
            lines.append(f"| {i} | {e['sample_id']} | {e['overall_score']:.3f} | {e['high_risk_recall']:.1%} | {e['legal_basis_coverage']:.1%} | {', '.join(reasons)} |")
        lines.append("")

    # 八、质量基线判断
    lines.append("## 八、Phase 3 质量基线判断")
    lines.append("")
    if batch_eval["successful_evaluations"] >= 5:
        if batch_eval["avg_overall_score"] >= 0.7:
            lines.append("**结论：当前批次评测结果已具备做 Phase 3 质量基线的条件。**")
        elif batch_eval["avg_overall_score"] >= 0.5:
            lines.append("**结论：当前批次评测结果接近质量基线，但仍有改进空间。建议先补齐剩余样本的审查运行，再做基线。**")
        else:
            lines.append("**结论：当前批次评测结果尚未达到质量基线。需要改进审查质量后再做基线。**")
    else:
        lines.append(f"**结论：成功评测样本不足（{batch_eval['successful_evaluations']} < 5），暂不具备做基线的条件。**")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 `scripts/batch_evaluate.py` 自动生成。*")

    md_path = SUMMARY_DIR / "evaluation_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")


# ─── Latest-only 模式 ─────────────────────────────────────────────────────────

def evaluate_sample_latest_only(sample_dir: Path) -> dict | None:
    """评测单个样本的最新成功 run。返回评测结果 dict，无成功 run 返回 None。"""
    prefix = get_latest_successful_run_prefix(sample_dir)
    if not prefix:
        return None

    manifest = _safe_load_json(sample_dir / "manifest.json")
    expected_risks = _safe_load_json(sample_dir / "expected_risks.json")
    expected_missing = _safe_load_json(sample_dir / "expected_missing_clauses.json")
    expected_contradictions = _safe_load_json(sample_dir / "expected_contradictions.json")

    run_path = sample_dir / f"{prefix}.json"
    run_data = _safe_load_json(run_path) if run_path.exists() else None

    return evaluate_run(
        sample_dir=sample_dir,
        run_prefix=prefix,
        run_data=run_data,
        expected_risks=expected_risks,
        expected_missing=expected_missing,
        expected_contradictions=expected_contradictions,
        manifest=manifest,
    )


def write_latest_only_evaluation(batch_eval: dict, latest_evals: list[dict]) -> None:
    """写入 latest-only 口径的批次级评测文件。"""
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = SUMMARY_DIR / "latest_only_evaluation_summary.json"
    json_path.write_text(json.dumps(batch_eval, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV
    csv_path = SUMMARY_DIR / "latest_only_evaluation_summary.csv"
    successful = [e for e in latest_evals if e["success"]]
    if successful:
        fields = [
            "sample_id", "review_run_file", "topic_recall", "topic_precision",
            "high_risk_recall", "contradiction_hit", "contradiction_expected", "contradiction_detected",
            "missing_clause_hit", "missing_clause_expected", "missing_clause_detected",
            "legal_basis_coverage", "overall_score",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(successful)

    # Markdown 报告
    lines = []
    lines.append("# Latest-Only 黄金样例评测报告 — batch-01")
    lines.append("")
    lines.append("> **口径说明：本报告仅基于每个样本最新一次成功运行，不含历史旧 run。**")
    lines.append(f"> 生成时间：{batch_eval['generated_at']}")
    lines.append("")

    # 一、总览
    lines.append("## 一、评测总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 样本数 | {batch_eval['total_evaluations']} |")
    lines.append(f"| 成功评测 | {batch_eval['successful_evaluations']} |")
    lines.append(f"| 无成功 run | {batch_eval['failed_evaluations']} |")
    lines.append(f"| 平均主题 Recall | {batch_eval['avg_topic_recall']:.1%} |")
    lines.append(f"| 平均主题 Precision | {batch_eval['avg_topic_precision']:.1%} |")
    lines.append(f"| 平均高风险 Recall | {batch_eval['avg_high_risk_recall']:.1%} |")
    lines.append(f"| 平均综合评分 | {batch_eval['avg_overall_score']:.3f} |")
    lines.append(f"| 平均法条依据覆盖率 | {batch_eval['avg_legal_basis_coverage']:.1%} |")
    lines.append(f"| 矛盾命中率 | {batch_eval['contradiction_hit_rate']:.1%} |")
    lines.append(f"| 缺失条款命中率 | {batch_eval['missing_clause_hit_rate']:.1%} |")
    lines.append("")

    # 二、各样本详情
    lines.append("## 二、各样本最新 run 评测详情")
    lines.append("")
    if latest_evals:
        lines.append("| 样本 | Run | 主题Recall | 高风险Recall | 综合评分 | 法条覆盖 | 状态 |")
        lines.append("|---|---|---|---|---|---|---|")
        for e in latest_evals:
            status = "✅" if e["success"] else "❌ 无成功run"
            run_file = e.get("review_run_file", "-")
            if e["success"]:
                lines.append(
                    f"| {e['sample_id']} | {run_file} | "
                    f"{e['topic_recall']:.1%} | {e['high_risk_recall']:.1%} | "
                    f"{e['overall_score']:.3f} | {e['legal_basis_coverage']:.1%} | {status} |"
                )
            else:
                lines.append(
                    f"| {e['sample_id']} | - | - | - | - | - | {status} |"
                )
        lines.append("")

    # 三、命中率最高 / 最低
    successful = [e for e in latest_evals if e["success"]]
    if successful:
        sorted_by_score = sorted(successful, key=lambda e: e["overall_score"], reverse=True)

        lines.append("## 三、命中率最高的合同（Top 5）")
        lines.append("")
        lines.append("| 排名 | 样本 | Run | 综合评分 |")
        lines.append("|---|---|---|---|")
        for i, e in enumerate(sorted_by_score[:5], 1):
            lines.append(f"| {i} | {e['sample_id']} | {e['review_run_file']} | {e['overall_score']:.3f} |")
        lines.append("")

        lines.append("## 四、命中率最低的合同（Bottom 5）")
        lines.append("")
        lines.append("| 排名 | 样本 | Run | 综合评分 |")
        lines.append("|---|---|---|---|")
        for i, e in enumerate(sorted_by_score[-5:], 1):
            lines.append(f"| {i} | {e['sample_id']} | {e['review_run_file']} | {e['overall_score']:.3f} |")
        lines.append("")

    # 五、高风险类别漏报
    lines.append("## 五、高风险类别漏报")
    lines.append("")
    high_miss = batch_eval.get("high_risk_miss_stats", {})
    if high_miss:
        lines.append("| 风险类别 | 漏报次数 |")
        lines.append("|---|---|")
        for cat, count in sorted(high_miss.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {cat} | {count} |")
        lines.append("")
    else:
        lines.append("无高风险漏报。")
        lines.append("")

    # 六、质量基线判断
    lines.append("## 六、Phase 3 质量基线判断（latest-only 口径）")
    lines.append("")
    if batch_eval["successful_evaluations"] >= 5:
        if batch_eval["avg_overall_score"] >= 0.7:
            lines.append("**结论：latest-only 口径下，当前批次评测结果已具备做 Phase 3 质量基线的条件。**")
        elif batch_eval["avg_overall_score"] >= 0.5:
            lines.append("**结论：latest-only 口径下，当前批次评测结果接近质量基线，但仍有改进空间。**")
        else:
            lines.append("**结论：latest-only 口径下，当前批次评测结果尚未达到质量基线。**")
    else:
        lines.append(f"**结论：成功评测样本不足（{batch_eval['successful_evaluations']} < 5）。**")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 `scripts/batch_evaluate.py --latest-only` 自动生成。*")

    md_path = SUMMARY_DIR / "latest_only_evaluation_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")


# ─── 主流程 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="黄金样例自动评测器")
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="仅评测每个样本最新一次成功 run，生成 latest-only 口径报告",
    )
    args = parser.parse_args()

    print(f"扫描目录: {BATCH_DIR}")

    all_evaluations: list[dict] = []
    sample_count = 0
    evaluated_count = 0

    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue

        sample_count += 1
        evaluations = evaluate_sample(entry)

        # 写入单样本文件
        write_sample_evaluations(entry, evaluations)

        for ev in evaluations:
            all_evaluations.append(ev)
            if ev["success"]:
                evaluated_count += 1

    print(f"扫描到 {sample_count} 个样本，评测 {evaluated_count} 次成功运行")

    # 批次级汇总（全历史）
    batch_eval = compute_batch_evaluation(all_evaluations)
    write_batch_evaluation(batch_eval, all_evaluations)

    print(f"\n=== 评测摘要（全历史） ===")
    print(f"平均主题 Recall: {batch_eval['avg_topic_recall']:.1%}")
    print(f"平均高风险 Recall: {batch_eval['avg_high_risk_recall']:.1%}")
    print(f"平均综合评分: {batch_eval['avg_overall_score']:.3f}")
    print(f"矛盾命中率: {batch_eval['contradiction_hit_rate']:.1%}")
    print(f"缺失条款命中率: {batch_eval['missing_clause_hit_rate']:.1%}")

    # ─── Latest-only 模式 ───────────────────────────────────────────────
    if args.latest_only:
        print(f"\n{'='*60}")
        print("Latest-Only 模式：仅取每个样本最新成功 run")

        latest_evals: list[dict] = []
        latest_ok = 0
        latest_none = 0

        for entry in sorted(BATCH_DIR.iterdir()):
            if not entry.is_dir() or not entry.name.startswith("contract-"):
                continue

            ev = evaluate_sample_latest_only(entry)
            if ev is None:
                # 无成功 run，构造占位记录
                latest_evals.append({
                    "sample_id": entry.name,
                    "review_run_file": "",
                    "success": False,
                    "topic_recall": 0.0,
                    "topic_precision": 0.0,
                    "high_risk_recall": 0.0,
                    "overall_score": 0.0,
                    "legal_basis_coverage": 0.0,
                    "contradiction_hit": False,
                    "contradiction_expected": 0,
                    "contradiction_detected": 0,
                    "missing_clause_hit": False,
                    "missing_clause_expected": 0,
                    "missing_clause_detected": 0,
                    "expected_risk_topics": [],
                    "detected_risk_topics": [],
                    "expected_high_risk_topics": [],
                    "detected_high_risk_topics": [],
                    "missing_expected_topics": [],
                    "unexpected_topics": [],
                    "notes": "无成功 run",
                })
                latest_none += 1
            else:
                latest_evals.append(ev)
                if ev["success"]:
                    latest_ok += 1

        latest_batch_eval = compute_batch_evaluation(latest_evals)
        write_latest_only_evaluation(latest_batch_eval, latest_evals)

        print(f"\n=== 评测摘要（latest-only） ===")
        print(f"样本数: {len(latest_evals)}，成功: {latest_ok}，无成功run: {latest_none}")
        print(f"平均主题 Recall: {latest_batch_eval['avg_topic_recall']:.1%}")
        print(f"平均高风险 Recall: {latest_batch_eval['avg_high_risk_recall']:.1%}")
        print(f"平均综合评分: {latest_batch_eval['avg_overall_score']:.3f}")
        print(f"矛盾命中率: {latest_batch_eval['contradiction_hit_rate']:.1%}")
        print(f"缺失条款命中率: {latest_batch_eval['missing_clause_hit_rate']:.1%}")


if __name__ == "__main__":
    main()
