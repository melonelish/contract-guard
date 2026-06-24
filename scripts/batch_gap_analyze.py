"""漏报归因分析工具 — 结构化黄金预期 + 漂移/漏报归因报告。

功能：
1. 为 batch-01 每个样本生成 expected_manifest.json（结构化黄金预期）
2. 基于评测结果输出漏报归因分析报告

用法：
    python scripts/batch_gap_analyze.py              # 全历史模式
    python scripts/batch_gap_analyze.py --latest-only # 仅最新成功 run

输出（全历史）：
    07-testing/generated/batch-01/_summary/gap_analysis.json
    07-testing/generated/batch-01/_summary/gap_analysis.csv
    07-testing/generated/batch-01/_summary/gap_analysis_report.md

输出（latest-only，额外生成，不覆盖全历史报告）：
    07-testing/generated/batch-01/_summary/latest_only_gap_analysis.json
    07-testing/generated/batch-01/_summary/latest_only_gap_analysis.csv
    07-testing/generated/batch-01/_summary/latest_only_gap_analysis_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

# 复用 batch_evaluate 的同义归一化
from batch_evaluate import (
    BATCH_DIR,
    _safe_load_json,
    evaluate_sample_latest_only,
    infer_category_from_title,
    normalize_category,
    normalize_severity,
)

SUMMARY_DIR = BATCH_DIR / "_summary"
RUN_PREFIXES = ["review_run_01", "review_run_02", "review_run_03"]


# ─── 第一步：为每个样本生成 expected_manifest.json ─────────────────────────

def build_expected_manifest(sample_dir: Path) -> dict | None:
    """从样本目录已有文件中提取结构化黄金预期。"""
    manifest = _safe_load_json(sample_dir / "manifest.json")
    expected_risks = _safe_load_json(sample_dir / "expected_risks.json")
    expected_missing = _safe_load_json(sample_dir / "expected_missing_clauses.json")
    expected_contradictions = _safe_load_json(sample_dir / "expected_contradictions.json")

    if not manifest:
        return None

    sample_id = sample_dir.name
    contract_type = manifest.get("contract_type", "")

    # 提取风险主题
    risk_topics: list[str] = []
    high_risk_topics: list[str] = []
    if expected_risks and "risks" in expected_risks:
        for r in expected_risks["risks"]:
            raw_cat = r.get("risk_type") or r.get("risk_category") or ""
            cat = normalize_category(raw_cat)
            if cat == "其他" or (cat and not any('一' <= c <= '鿿' for c in cat)):
                title = r.get("title", "")
                inferred = infer_category_from_title(title)
                if inferred != "其他":
                    cat = inferred
            risk_topics.append(cat)
            raw_level = r.get("severity") or r.get("risk_level") or ""
            level = normalize_severity(raw_level)
            if level == "high":
                high_risk_topics.append(cat)

    # 提取法条依据主题（从 legal_basis 字段提取关键词）
    legal_basis_topics: list[str] = []
    if expected_risks and "risks" in expected_risks:
        for r in expected_risks["risks"]:
            basis = r.get("legal_basis", "")
            if basis:
                # 提取法律名称
                import re
                law_names = re.findall(r"《([^》]+)》", basis)
                for ln in law_names:
                    if ln not in legal_basis_topics:
                        legal_basis_topics.append(ln)

    # 提取缺失条款名称
    missing_names: list[str] = []
    missing_high: list[str] = []
    if expected_missing and "missing_clauses" in expected_missing:
        for m in expected_missing["missing_clauses"]:
            name = m.get("clause_name", "")
            if name:
                missing_names.append(name)
            if m.get("importance") == "high":
                missing_high.append(name)

    # 提取矛盾摘要
    contradiction_summaries: list[str] = []
    if expected_contradictions and "contradictions" in expected_contradictions:
        for c in expected_contradictions["contradictions"]:
            desc = c.get("description", "")
            if desc:
                # 截取前 80 字作为摘要
                contradiction_summaries.append(desc[:80] + ("..." if len(desc) > 80 else ""))

    return {
        "sample_id": sample_id,
        "contract_type": contract_type,
        "title": manifest.get("title", ""),
        "difficulty": manifest.get("difficulty", ""),
        "expected_risk_topics": sorted(set(risk_topics)),
        "expected_high_risk_topics": sorted(set(high_risk_topics)),
        "expected_risk_count": manifest.get("risk_count", len(risk_topics)),
        "expected_high_risk_count": len(set(high_risk_topics)),
        "expected_contradictions": manifest.get("contradiction_count", 0),
        "contradiction_summaries": contradiction_summaries[:5],
        "expected_missing_clauses": manifest.get("missing_count", 0),
        "missing_clause_names": missing_names,
        "missing_clause_high": missing_high,
        "expected_legal_basis_topics": legal_basis_topics,
        "notes": "",
    }


def generate_all_manifests() -> dict[str, dict]:
    """为所有样本生成 expected_manifest.json，返回 sample_id → manifest 映射。"""
    results = {}
    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue
        manifest = build_expected_manifest(entry)
        if manifest:
            out_path = entry / "expected_manifest.json"
            out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            results[entry.name] = manifest
    return results


# ─── 第二步：加载评测结果 ────────────────────────────────────────────────────

def load_evaluations() -> list[dict]:
    """加载所有样本的 evaluation_review_run_01.json（首次运行结果）。"""
    evals = []
    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue
        ev_path = entry / "evaluation_review_run_01.json"
        if ev_path.exists():
            ev_data = _safe_load_json(ev_path)
            if ev_data:
                evals.append(ev_data)
    return evals


def load_evaluations_latest_only() -> list[dict]:
    """加载每个样本最新成功 run 的评测结果。"""
    evals = []
    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue
        ev = evaluate_sample_latest_only(entry)
        if ev and ev.get("success"):
            evals.append(ev)
    return evals


def load_review_runs() -> list[dict]:
    """加载所有样本的 review_run_01.json。"""
    runs = []
    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue
        run_path = entry / "review_run_01.json"
        if run_path.exists():
            run_data = _safe_load_json(run_path)
            if run_data:
                run_data["_sample_dir"] = entry.name
                runs.append(run_data)
    return runs


def load_review_runs_latest_only() -> list[dict]:
    """加载每个样本最新成功 run 的审查数据。"""
    from batch_evaluate import _detect_run_prefixes

    runs = []
    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue
        prefix = None
        prefixes = _detect_run_prefixes(entry)
        for p in reversed(prefixes):
            run_path = entry / f"{p}.json"
            run_data = _safe_load_json(run_path)
            if run_data and run_data.get("success") and not run_data.get("error"):
                run_data["_sample_dir"] = entry.name
                runs.append(run_data)
                prefix = p
                break
    return runs


# ─── 第三步：归因分析 ────────────────────────────────────────────────────────

def classify_gap_type(ev: dict, run: dict | None) -> str:
    """判断漏报/漂移的主要原因类型。"""
    if not ev.get("success"):
        notes = ev.get("notes", "")
        # 无运行结果文件 → not_run
        if "无运行结果文件" in notes:
            return "not_run"
        if run and run.get("error"):
            err = run["error"].lower()
            if "timeout" in err or "超时" in err:
                return "timeout"
            if "format" in err or "json" in err or "schema" in err:
                return "output_format"
            if "rate" in err or "limit" in err or "429" in err:
                return "rate_limit"
            if "auth" in err or "401" in err or "403" in err:
                return "auth_error"
        # 有审查运行但失败 → execution_failure
        if run:
            return "execution_failure"
        # 无审查运行也无运行结果 → not_run
        return "not_run"

    # 成功运行但有漏报
    missing = ev.get("missing_expected_topics", [])
    if not missing:
        return "no_gap"

    # 分类漏报原因
    high_recall = ev.get("high_risk_recall", 0)
    topic_recall = ev.get("topic_recall", 0)

    if topic_recall < 0.2:
        return "content_coverage_severe"
    if high_recall < 0.3:
        return "high_risk_miss"
    if topic_recall < 0.5:
        return "content_coverage_moderate"
    return "minor_gap"


def compute_gap_analysis(
    manifests: dict[str, dict],
    evaluations: list[dict],
    review_runs: list[dict],
) -> dict:
    """计算批次级漏报归因分析。"""
    run_map = {r["_sample_dir"]: r for r in review_runs}

    # 每样本归因
    sample_gaps: list[dict] = []
    for ev in evaluations:
        sid = ev.get("sample_id", "")
        manifest = manifests.get(sid, {})
        run = run_map.get(sid)
        gap_type = classify_gap_type(ev, run)

        sample_gaps.append({
            "sample_id": sid,
            "contract_type": manifest.get("contract_type", ""),
            "difficulty": manifest.get("difficulty", ""),
            "gap_type": gap_type,
            "topic_recall": ev.get("topic_recall", 0),
            "high_risk_recall": ev.get("high_risk_recall", 0),
            "overall_score": ev.get("overall_score", 0),
            "legal_basis_coverage": ev.get("legal_basis_coverage", 0),
            "missing_topics": ev.get("missing_expected_topics", []),
            "unexpected_topics": ev.get("unexpected_topics", []),
            "expected_risk_count": manifest.get("expected_risk_count", 0),
            "detected_risk_count": len(ev.get("detected_risk_topics", [])),
            "contradiction_hit": ev.get("contradiction_hit", False),
            "missing_clause_hit": ev.get("missing_clause_hit", False),
        })

    # 未运行的样本
    run_sids = {ev.get("sample_id") for ev in evaluations}
    for sid, manifest in manifests.items():
        if sid not in run_sids:
            sample_gaps.append({
                "sample_id": sid,
                "contract_type": manifest.get("contract_type", ""),
                "difficulty": manifest.get("difficulty", ""),
                "gap_type": "not_run",
                "topic_recall": 0,
                "high_risk_recall": 0,
                "overall_score": 0,
                "legal_basis_coverage": 0,
                "missing_topics": manifest.get("expected_risk_topics", []),
                "unexpected_topics": [],
                "expected_risk_count": manifest.get("expected_risk_count", 0),
                "detected_risk_count": 0,
                "contradiction_hit": False,
                "missing_clause_hit": False,
            })

    # 漏报主题统计
    topic_miss_count: dict[str, int] = {}
    topic_miss_samples: dict[str, list[str]] = {}
    for g in sample_gaps:
        for t in g.get("missing_topics", []):
            topic_miss_count[t] = topic_miss_count.get(t, 0) + 1
            topic_miss_samples.setdefault(t, []).append(g["sample_id"])

    # 高风险漏报统计
    high_risk_miss: dict[str, int] = {}
    for g in sample_gaps:
        manifest = manifests.get(g["sample_id"], {})
        for t in manifest.get("expected_high_risk_topics", []):
            if t in g.get("missing_topics", []):
                high_risk_miss[t] = high_risk_miss.get(t, 0) + 1

    # 漏报类型分布
    gap_type_dist: dict[str, int] = {}
    for g in sample_gaps:
        gt = g["gap_type"]
        gap_type_dist[gt] = gap_type_dist.get(gt, 0) + 1

    # "风险数不低但关键风险没抓住"的样本（仅分析已运行的样本）
    high_expected_low_recall = []
    for g in sample_gaps:
        if g["gap_type"] == "not_run":
            continue
        if g.get("expected_risk_count", 0) >= 8 and g.get("high_risk_recall", 1) < 0.3:
            high_expected_low_recall.append(g["sample_id"])

    # "法条依据弱但风险主题抓到了"的样本（仅分析已运行的样本）
    good_coverage_weak_basis = []
    for g in sample_gaps:
        if g["gap_type"] == "not_run":
            continue
        if g.get("topic_recall", 0) >= 0.5 and g.get("legal_basis_coverage", 1) < 0.5:
            good_coverage_weak_basis.append(g["sample_id"])

    # 修复优先级：按主题漏报频率 × 高风险权重排序
    topic_priority: list[dict] = []
    for topic, miss_count in sorted(topic_miss_count.items(), key=lambda x: x[1], reverse=True):
        is_high_miss = topic in high_risk_miss
        topic_priority.append({
            "topic": topic,
            "miss_count": miss_count,
            "is_high_risk_miss": is_high_miss,
            "affected_samples": topic_miss_samples.get(topic, []),
            "priority_score": miss_count * (2.0 if is_high_miss else 1.0),
        })
    topic_priority.sort(key=lambda x: x["priority_score"], reverse=True)

    # 推荐回归测试样本（漏报多 + 有代表性 contract_type）
    regression_candidates = []
    seen_types = set()
    for g in sorted(sample_gaps, key=lambda x: len(x.get("missing_topics", [])), reverse=True):
        ct = g.get("contract_type", "")
        if ct and ct not in seen_types and len(g.get("missing_topics", [])) > 0:
            regression_candidates.append(g["sample_id"])
            seen_types.add(ct)
        if len(regression_candidates) >= 10:
            break

    return {
        "batch_name": "batch-01",
        "generated_at": datetime.now().isoformat(),
        "total_samples": len(manifests),
        "analyzed_samples": len([g for g in sample_gaps if g["gap_type"] != "not_run"]),
        "not_run_samples": len([g for g in sample_gaps if g["gap_type"] == "not_run"]),
        "gap_type_distribution": gap_type_dist,
        "sample_gaps": sample_gaps,
        "topic_miss_stats": [
            {
                "topic": t,
                "miss_count": topic_miss_count[t],
                "is_high_risk_miss": t in high_risk_miss,
                "affected_samples": topic_miss_samples.get(t, []),
            }
            for t in sorted(topic_miss_count, key=lambda x: topic_miss_count[x], reverse=True)
        ],
        "high_expected_low_recall_samples": high_expected_low_recall,
        "good_coverage_weak_basis_samples": good_coverage_weak_basis,
        "topic_priority": topic_priority[:20],
        "regression_test_candidates": regression_candidates,
    }


# ─── 第四步：修复优先级表 ────────────────────────────────────────────────────

def build_fix_priority_table(analysis: dict) -> list[dict]:
    """生成 P0-P3 修复优先级表。"""
    priorities = []

    topic_stats = analysis.get("topic_miss_stats", [])
    gap_dist = analysis.get("gap_type_distribution", {})
    high_low = analysis.get("high_expected_low_recall_samples", [])
    weak_basis = analysis.get("good_coverage_weak_basis_samples", [])

    # P0: 最影响质量基线的问题
    p0_reasons = []
    if gap_dist.get("content_coverage_severe", 0) > 0:
        p0_reasons.append(f"{gap_dist['content_coverage_severe']} 个样本存在严重内容覆盖不足（Recall < 20%）")
    if gap_dist.get("execution_failure", 0) > 0:
        p0_reasons.append(f"{gap_dist['execution_failure']} 个样本审查执行失败")
    if gap_dist.get("timeout", 0) > 0:
        p0_reasons.append(f"{gap_dist['timeout']} 个样本超时")
    if high_low:
        p0_reasons.append(f"{len(high_low)} 个样本风险数不低但关键高风险漏报严重")
    if p0_reasons:
        priorities.append({"level": "P0", "description": "最影响质量基线的问题", "items": p0_reasons})

    # P1: 高频漏报主题（>=3 次漏报）
    p1_items = []
    for ts in topic_stats:
        if ts["miss_count"] >= 3:
            p1_items.append(f"「{ts['topic']}」漏报 {ts['miss_count']} 次，影响样本: {', '.join(ts['affected_samples'][:3])}")
    if p1_items:
        priorities.append({"level": "P1", "description": "高频漏报主题（≥3次）", "items": p1_items})

    # P2: 同义归并仍不足的主题（漏报 2 次）
    p2_items = []
    for ts in topic_stats:
        if 2 <= ts["miss_count"] < 3:
            p2_items.append(f"「{ts['topic']}」漏报 {ts['miss_count']} 次")
    if p2_items:
        priorities.append({"level": "P2", "description": "中频漏报主题（2次），可能需要扩展同义归并", "items": p2_items})

    # P3: 可以暂缓
    p3_items = []
    for ts in topic_stats:
        if ts["miss_count"] == 1 and not ts["is_high_risk_miss"]:
            p3_items.append(f"「{ts['topic']}」漏报 1 次")
    if p3_items:
        priorities.append({"level": "P3", "description": "低频漏报（1次且非高风险），可暂缓", "items": p3_items})

    return priorities


# ─── 第五步：输出 ────────────────────────────────────────────────────────────

def write_gap_outputs(analysis: dict, fix_table: list[dict]) -> None:
    """输出 gap_analysis.json / csv / md。"""
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    json_out = {**analysis, "fix_priority_table": fix_table}
    (SUMMARY_DIR / "gap_analysis.json").write_text(
        json.dumps(json_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # CSV
    csv_path = SUMMARY_DIR / "gap_analysis.csv"
    fields = [
        "sample_id", "contract_type", "difficulty", "gap_type",
        "topic_recall", "high_risk_recall", "overall_score",
        "legal_basis_coverage", "expected_risk_count", "detected_risk_count",
        "contradiction_hit", "missing_clause_hit", "missing_topics",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for g in analysis.get("sample_gaps", []):
            row = {**g, "missing_topics": "; ".join(g.get("missing_topics", []))}
            writer.writerow(row)

    # Markdown
    lines = _build_report_md(analysis, fix_table, mode="full")
    (SUMMARY_DIR / "gap_analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_gap_outputs_latest_only(analysis: dict, fix_table: list[dict]) -> None:
    """输出 latest-only 口径的 gap_analysis 文件。"""
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    json_out = {**analysis, "fix_priority_table": fix_table}
    (SUMMARY_DIR / "latest_only_gap_analysis.json").write_text(
        json.dumps(json_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # CSV
    csv_path = SUMMARY_DIR / "latest_only_gap_analysis.csv"
    fields = [
        "sample_id", "contract_type", "difficulty", "gap_type",
        "topic_recall", "high_risk_recall", "overall_score",
        "legal_basis_coverage", "expected_risk_count", "detected_risk_count",
        "contradiction_hit", "missing_clause_hit", "missing_topics",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for g in analysis.get("sample_gaps", []):
            row = {**g, "missing_topics": "; ".join(g.get("missing_topics", []))}
            writer.writerow(row)

    # Markdown
    lines = _build_report_md(analysis, fix_table, mode="latest_only")
    (SUMMARY_DIR / "latest_only_gap_analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def _build_report_md(analysis: dict, fix_table: list[dict], mode: str = "full") -> list[str]:
    """构建 Markdown 报告内容。mode: 'full' 或 'latest_only'。"""
    lines: list[str] = []
    if mode == "latest_only":
        lines.append("# Latest-Only 漏报归因分析报告 — batch-01")
        lines.append("")
        lines.append("> **口径说明：本报告仅基于每个样本最新一次成功运行，不含历史旧 run。**")
    else:
        lines.append("# 漏报归因分析报告 — batch-01")
    lines.append("")
    lines.append(f"> 生成时间：{analysis['generated_at']}")
    lines.append("")

    # 一、总览
    lines.append("## 一、分析总览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 总样本数 | {analysis['total_samples']} |")
    lines.append(f"| 已分析样本 | {analysis['analyzed_samples']} |")
    lines.append(f"| 未运行样本 | {analysis['not_run_samples']} |")
    lines.append("")

    # 漏报类型分布
    gap_dist = analysis.get("gap_type_distribution", {})
    if gap_dist:
        lines.append("### 漏报类型分布")
        lines.append("")
        lines.append("| 类型 | 数量 | 说明 |")
        lines.append("|---|---|---|")
        type_desc = {
            "no_gap": "无漏报",
            "minor_gap": "轻微漏报",
            "content_coverage_moderate": "中度覆盖不足",
            "content_coverage_severe": "严重覆盖不足",
            "high_risk_miss": "高风险漏报",
            "output_format": "输出格式问题",
            "timeout": "超时",
            "rate_limit": "限流",
            "auth_error": "认证错误",
            "execution_failure": "执行失败",
            "not_run": "未运行",
        }
        for gt, count in sorted(gap_dist.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {gt} | {count} | {type_desc.get(gt, '')} |")
        lines.append("")

    # 二、高频漏报主题
    lines.append("## 二、高频漏报主题（Top 10）")
    lines.append("")
    topic_stats = analysis.get("topic_miss_stats", [])
    if topic_stats:
        lines.append("| 主题 | 漏报次数 | 高风险漏报 | 影响样本 |")
        lines.append("|---|---|---|---|")
        for ts in topic_stats[:10]:
            high_flag = "⚠️ 是" if ts["is_high_risk_miss"] else "否"
            samples = ", ".join(ts["affected_samples"][:3])
            if len(ts["affected_samples"]) > 3:
                samples += f" 等{len(ts['affected_samples'])}个"
            lines.append(f"| {ts['topic']} | {ts['miss_count']} | {high_flag} | {samples} |")
        lines.append("")

    # 三、风险数不低但关键风险没抓住的样本
    lines.append("## 三、风险数不低但关键风险没抓住")
    lines.append("")
    high_low = analysis.get("high_expected_low_recall_samples", [])
    if high_low:
        lines.append("以下样本期望风险数 ≥ 8，但高风险 Recall < 30%：")
        lines.append("")
        for sid in high_low:
            lines.append(f"- `{sid}`")
        lines.append("")
    else:
        lines.append("无此类样本。")
        lines.append("")

    # 四、法条依据弱但风险主题抓到了
    lines.append("## 四、法条依据弱但风险主题抓到了")
    lines.append("")
    weak_basis = analysis.get("good_coverage_weak_basis_samples", [])
    if weak_basis:
        lines.append("以下样本主题 Recall ≥ 50%，但法条覆盖率 < 50%：")
        lines.append("")
        for sid in weak_basis:
            lines.append(f"- `{sid}`")
        lines.append("")
    else:
        lines.append("无此类样本。")
        lines.append("")

    # 五、失败类型分析
    lines.append("## 五、失败类型分析：格式问题 vs 内容覆盖问题")
    lines.append("")
    format_issues = gap_dist.get("output_format", 0) + gap_dist.get("timeout", 0)
    content_issues = gap_dist.get("content_coverage_severe", 0) + gap_dist.get("content_coverage_moderate", 0) + gap_dist.get("high_risk_miss", 0)
    exec_issues = gap_dist.get("execution_failure", 0) + gap_dist.get("rate_limit", 0) + gap_dist.get("auth_error", 0)
    lines.append("| 大类 | 数量 | 占比 |")
    lines.append("|---|---|---|")
    total_issues = format_issues + content_issues + exec_issues
    if total_issues > 0:
        lines.append(f"| 输出格式/超时问题 | {format_issues} | {format_issues/total_issues:.0%} |")
        lines.append(f"| 内容覆盖问题 | {content_issues} | {content_issues/total_issues:.0%} |")
        lines.append(f"| 执行/基础设施问题 | {exec_issues} | {exec_issues/total_issues:.0%} |")
    lines.append("")
    lines.append("**结论**：")
    if content_issues > format_issues and content_issues > exec_issues:
        lines.append("- 主要瓶颈在**内容覆盖**——模型未能识别出足够多的风险主题。")
        lines.append("- 建议优先优化 prompt 模板和 RAG 召回策略。")
    elif format_issues > content_issues:
        lines.append("- 主要瓶颈在**输出格式**——模型输出 JSON 格式不稳定。")
        lines.append("- 建议优化 system prompt 的格式约束和 schema 校验重试。")
    else:
        lines.append("- 各类问题分布较均匀，需综合改进。")
    lines.append("")

    # 六、推荐回归测试样本
    lines.append("## 六、推荐回归测试样本")
    lines.append("")
    reg = analysis.get("regression_test_candidates", [])
    if reg:
        lines.append("以下样本覆盖不同类型，漏报最多，最适合作为回归测试基准：")
        lines.append("")
        for sid in reg:
            lines.append(f"- `{sid}`")
        lines.append("")

    # 七、修复优先级表
    lines.append("## 七、修复优先级表")
    lines.append("")
    if fix_table:
        for p in fix_table:
            lines.append(f"### {p['level']}：{p['description']}")
            lines.append("")
            for item in p["items"]:
                lines.append(f"- {item}")
            lines.append("")

    # 八、最值得优先提升的 10 个主题
    lines.append("## 八、最值得优先提升的 10 个主题")
    lines.append("")
    priority_topics = analysis.get("topic_priority", [])
    if priority_topics:
        lines.append("| 排名 | 主题 | 漏报次数 | 高风险漏报 | 优先级分 |")
        lines.append("|---|---|---|---|---|")
        for i, tp in enumerate(priority_topics[:10], 1):
            high_flag = "⚠️" if tp["is_high_risk_miss"] else ""
            lines.append(f"| {i} | {tp['topic']} | {tp['miss_count']} | {high_flag} | {tp['priority_score']:.1f} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 `scripts/batch_gap_analyze.py` 自动生成。*")

    return lines


# ─── 主流程 ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="漏报归因分析工具")
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="仅分析每个样本最新一次成功 run",
    )
    args = parser.parse_args()

    print(f"扫描目录: {BATCH_DIR}")

    # Step 1: 生成 expected_manifest.json
    print("\n[Step 1] 生成结构化黄金预期...")
    manifests = generate_all_manifests()
    print(f"  已为 {len(manifests)} 个样本生成 expected_manifest.json")

    # Step 2: 加载评测结果（全历史）
    print("\n[Step 2] 加载评测结果（全历史）...")
    evaluations = load_evaluations()
    review_runs = load_review_runs()
    print(f"  评测结果: {len(evaluations)} 条, 审查运行: {len(review_runs)} 条")

    # Step 3: 归因分析（全历史）
    print("\n[Step 3] 执行漏报归因分析（全历史）...")
    analysis = compute_gap_analysis(manifests, evaluations, review_runs)

    # Step 4: 修复优先级表
    print("\n[Step 4] 生成修复优先级表...")
    fix_table = build_fix_priority_table(analysis)

    # Step 5: 输出（全历史）
    print("\n[Step 5] 写入输出文件（全历史）...")
    write_gap_outputs(analysis, fix_table)

    # 摘要
    print(f"\n=== 归因分析摘要（全历史） ===")
    print(f"总样本: {analysis['total_samples']}")
    print(f"已分析: {analysis['analyzed_samples']}")
    print(f"未运行: {analysis['not_run_samples']}")
    gap_dist = analysis.get("gap_type_distribution", {})
    print(f"漏报类型分布:")
    for gt, count in sorted(gap_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gt}: {count}")
    print(f"\n修复优先级:")
    for p in fix_table:
        print(f"  {p['level']}: {p['description']} ({len(p['items'])} 项)")

    # ─── Latest-only 模式 ───────────────────────────────────────────────
    if args.latest_only:
        print(f"\n{'='*60}")
        print("Latest-Only 模式：仅分析每个样本最新成功 run")

        evaluations_lo = load_evaluations_latest_only()
        review_runs_lo = load_review_runs_latest_only()
        print(f"  评测结果: {len(evaluations_lo)} 条, 审查运行: {len(review_runs_lo)} 条")

        analysis_lo = compute_gap_analysis(manifests, evaluations_lo, review_runs_lo)
        fix_table_lo = build_fix_priority_table(analysis_lo)
        write_gap_outputs_latest_only(analysis_lo, fix_table_lo)

        print(f"\n=== 归因分析摘要（latest-only） ===")
        print(f"总样本: {analysis_lo['total_samples']}")
        print(f"已分析: {analysis_lo['analyzed_samples']}")
        print(f"未运行: {analysis_lo['not_run_samples']}")
        gap_dist_lo = analysis_lo.get("gap_type_distribution", {})
        print(f"漏报类型分布:")
        for gt, count in sorted(gap_dist_lo.items(), key=lambda x: x[1], reverse=True):
            print(f"  {gt}: {count}")


if __name__ == "__main__":
    main()
