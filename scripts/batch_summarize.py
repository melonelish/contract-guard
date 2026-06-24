"""批跑结果汇总工具 — 扫描 batch-01 样本目录，生成批次级汇总报告。

用法：
    python scripts/batch_summarize.py              # 全历史模式
    python scripts/batch_summarize.py --latest-only # 仅最新成功 run

输出（全历史）：
    07-testing/generated/batch-01/_summary/batch_summary.json
    07-testing/generated/batch-01/_summary/batch_summary.csv
    07-testing/generated/batch-01/_summary/batch_report.md

输出（latest-only，额外生成，不覆盖全历史报告）：
    07-testing/generated/batch-01/_summary/latest_only_batch_summary.json
    07-testing/generated/batch-01/_summary/latest_only_batch_summary.csv
    07-testing/generated/batch-01/_summary/latest_only_batch_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

BATCH_DIR = Path(__file__).resolve().parents[1] / "07-testing" / "generated" / "batch-01"
SUMMARY_DIR = BATCH_DIR / "_summary"
RUN_PREFIXES = ["review_run_01", "review_run_02", "review_run_03"]


def _detect_all_run_prefixes(sample_dir: Path) -> list[str]:
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


def scan_samples() -> list[dict]:
    """扫描所有 contract-* 目录，收集 manifest + review_run 数据。"""
    samples = []

    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue

        sample: dict = {
            "dir_name": entry.name,
            "manifest": None,
            "runs": [],
            "status": "pending",
        }

        # 读取 manifest
        manifest_path = entry / "manifest.json"
        if manifest_path.exists():
            try:
                sample["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                sample["manifest"] = None

        # 动态检测所有 review_run_XX.json
        all_prefixes = _detect_all_run_prefixes(entry)
        # 合并静态列表 + 动态检测，去重
        merged_prefixes = list(dict.fromkeys(RUN_PREFIXES + all_prefixes))

        for prefix in merged_prefixes:
            run_path = entry / f"{prefix}.json"
            if run_path.exists():
                try:
                    run_data = json.loads(run_path.read_text(encoding="utf-8"))
                    sample["runs"].append(run_data)
                except Exception:
                    sample["runs"].append({"error": "JSON 解析失败", "run_number": int(prefix[-2:])})

        # 判断状态
        if not sample["runs"]:
            sample["status"] = "pending"
        else:
            valid_runs = [r for r in sample["runs"] if not r.get("error")]
            if not valid_runs:
                sample["status"] = "failed"
            elif all(r.get("success") for r in valid_runs):
                sample["status"] = "completed"
            elif any(r.get("success") for r in valid_runs):
                sample["status"] = "partial"
            else:
                sample["status"] = "failed"

        samples.append(sample)

    return samples


def scan_samples_latest_only() -> list[dict]:
    """扫描所有 contract-* 目录，仅保留每个样本最新一次成功 run。"""
    samples = []

    for entry in sorted(BATCH_DIR.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("contract-"):
            continue

        sample: dict = {
            "dir_name": entry.name,
            "manifest": None,
            "runs": [],
            "status": "pending",
        }

        # 读取 manifest
        manifest_path = entry / "manifest.json"
        if manifest_path.exists():
            try:
                sample["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                sample["manifest"] = None

        # 找到最新成功 run
        all_prefixes = _detect_all_run_prefixes(entry)
        latest_run = None
        for prefix in reversed(all_prefixes):
            run_path = entry / f"{prefix}.json"
            if run_path.exists():
                try:
                    run_data = json.loads(run_path.read_text(encoding="utf-8"))
                    if run_data.get("success") and not run_data.get("error"):
                        latest_run = run_data
                        break
                except Exception:
                    continue

        if latest_run:
            sample["runs"] = [latest_run]
            sample["status"] = "completed"
        else:
            # 检查是否有 run 但全部失败
            has_any_run = len(all_prefixes) > 0
            if has_any_run:
                sample["status"] = "failed"
            else:
                sample["status"] = "pending"

        samples.append(sample)

    return samples


def compute_summary(samples: list[dict]) -> dict:
    """计算批次级汇总统计。"""
    total = len(samples)
    completed = sum(1 for s in samples if s["status"] == "completed")
    partial = sum(1 for s in samples if s["status"] == "partial")
    failed = sum(1 for s in samples if s["status"] == "failed")
    pending = sum(1 for s in samples if s["status"] == "pending")

    all_runs = []
    for s in samples:
        for r in s["runs"]:
            if not r.get("error"):
                all_runs.append(r)

    successful_runs = [r for r in all_runs if r.get("success")]
    failed_runs = [r for r in all_runs if not r.get("success")]

    # Token 统计
    total_prompt = sum(r.get("prompt_tokens", 0) for r in successful_runs)
    total_completion = sum(r.get("completion_tokens", 0) for r in successful_runs)
    total_tokens = sum(r.get("total_tokens", 0) for r in successful_runs)

    # 耗时统计
    latencies = [r.get("latency_ms", 0) for r in successful_runs if r.get("latency_ms")]
    durations = [r.get("duration_sec", 0) for r in successful_runs if r.get("duration_sec")]

    # 风险统计
    total_risks = sum(r.get("risk_count", 0) for r in successful_runs)
    total_high = sum(r.get("high_count", 0) for r in successful_runs)
    total_contradictions = sum(r.get("contradiction_count", 0) for r in successful_runs)
    total_missing = sum(r.get("missing_clause_count", 0) for r in successful_runs)

    # Fallback 统计
    fallback_count = sum(1 for r in successful_runs if r.get("fallback_triggered"))

    # Schema 清洗统计
    schema_cleaned = sum(1 for r in successful_runs if r.get("schema_cleaned"))

    # RAG 统计
    rag_enabled = sum(1 for r in successful_runs if r.get("rag_enabled"))

    # 模型使用统计
    models: dict[str, int] = {}
    for r in successful_runs:
        model = r.get("provider_model", "unknown")
        models[model] = models.get(model, 0) + 1

    return {
        "batch_name": "batch-01",
        "generated_at": datetime.now().isoformat(),
        "total_samples": total,
        "completed_samples": completed,
        "partial_samples": partial,
        "failed_samples": failed,
        "pending_samples": pending,
        "total_runs": len(all_runs),
        "successful_runs": len(successful_runs),
        "failed_runs": len(failed_runs),
        "token_stats": {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "avg_prompt_tokens": round(total_prompt / len(successful_runs)) if successful_runs else 0,
            "avg_completion_tokens": round(total_completion / len(successful_runs)) if successful_runs else 0,
            "avg_total_tokens": round(total_tokens / len(successful_runs)) if successful_runs else 0,
        },
        "latency_stats": {
            "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "avg_duration_sec": round(sum(durations) / len(durations), 1) if durations else 0,
        },
        "risk_stats": {
            "total_risks": total_risks,
            "total_high": total_high,
            "total_contradictions": total_contradictions,
            "total_missing_clauses": total_missing,
            "avg_risks_per_contract": round(total_risks / len(successful_runs), 1) if successful_runs else 0,
        },
        "quality_stats": {
            "fallback_triggered": fallback_count,
            "schema_cleaned": schema_cleaned,
            "rag_enabled": rag_enabled,
        },
        "model_usage": models,
    }


def build_per_sample_rows(samples: list[dict]) -> list[dict]:
    """为 CSV 和报告构建每样本明细行。"""
    rows = []
    for s in samples:
        manifest = s.get("manifest") or {}
        dir_name = s["dir_name"]

        if not s["runs"]:
            rows.append({
                "dir_name": dir_name,
                "title": manifest.get("title", ""),
                "contract_type": manifest.get("contract_type", ""),
                "difficulty": manifest.get("difficulty", ""),
                "status": "待运行",
                "run_count": 0,
                "successful_runs": 0,
                "provider_model": "",
                "avg_prompt_tokens": 0,
                "avg_completion_tokens": 0,
                "avg_total_tokens": 0,
                "avg_latency_ms": 0,
                "avg_duration_sec": 0,
                "risk_count": 0,
                "high_count": 0,
                "contradiction_count": 0,
                "missing_clause_count": 0,
                "fallback_triggered": False,
                "schema_cleaned": False,
                "rag_enabled": False,
                "error": "",
            })
            continue

        successful = [r for r in s["runs"] if r.get("success") and not r.get("error")]
        failed = [r for r in s["runs"] if not r.get("success") and not r.get("error")]
        errors = [r for r in s["runs"] if r.get("error")]

        if successful:
            avg = lambda key: round(sum(r.get(key, 0) for r in successful) / len(successful))
            rows.append({
                "dir_name": dir_name,
                "title": manifest.get("title", ""),
                "contract_type": manifest.get("contract_type", ""),
                "difficulty": manifest.get("difficulty", ""),
                "status": "成功" if len(successful) == len(s["runs"]) else "部分成功",
                "run_count": len(s["runs"]),
                "successful_runs": len(successful),
                "provider_model": successful[-1].get("provider_model", ""),
                "avg_prompt_tokens": avg("prompt_tokens"),
                "avg_completion_tokens": avg("completion_tokens"),
                "avg_total_tokens": avg("total_tokens"),
                "avg_latency_ms": avg("latency_ms"),
                "avg_duration_sec": round(sum(r.get("duration_sec", 0) for r in successful) / len(successful), 1),
                "risk_count": avg("risk_count"),
                "high_count": avg("high_count"),
                "contradiction_count": avg("contradiction_count"),
                "missing_clause_count": avg("missing_clause_count"),
                "fallback_triggered": any(r.get("fallback_triggered") for r in successful),
                "schema_cleaned": any(r.get("schema_cleaned") for r in successful),
                "rag_enabled": any(r.get("rag_enabled") for r in successful),
                "error": "",
            })
        else:
            error_msg = ""
            if errors:
                error_msg = str(errors[0].get("error", ""))
            elif failed:
                error_msg = str(failed[-1].get("error", "审查失败"))
            rows.append({
                "dir_name": dir_name,
                "title": manifest.get("title", ""),
                "contract_type": manifest.get("contract_type", ""),
                "difficulty": manifest.get("difficulty", ""),
                "status": "失败",
                "run_count": len(s["runs"]),
                "successful_runs": 0,
                "provider_model": "",
                "avg_prompt_tokens": 0,
                "avg_completion_tokens": 0,
                "avg_total_tokens": 0,
                "avg_latency_ms": 0,
                "avg_duration_sec": 0,
                "risk_count": 0,
                "high_count": 0,
                "contradiction_count": 0,
                "missing_clause_count": 0,
                "fallback_triggered": False,
                "schema_cleaned": False,
                "rag_enabled": False,
                "error": error_msg,
            })

    return rows


def generate_report_md(summary: dict, rows: list[dict], mode: str = "full") -> str:
    """生成 Markdown 批次报告。mode: 'full' 或 'latest_only'。"""
    lines = []
    if mode == "latest_only":
        lines.append("# Latest-Only 批跑汇总报告 — batch-01")
        lines.append("")
        lines.append("> **口径说明：本报告仅基于每个样本最新一次成功运行，不含历史旧 run。**")
    else:
        lines.append("# 批跑汇总报告 — batch-01")
    lines.append("")
    lines.append(f"> 生成时间：{summary['generated_at']}")
    lines.append("")

    # 总览
    lines.append("## 一、批次总览")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|---|---|")
    lines.append(f"| 总样本数 | {summary['total_samples']} |")
    lines.append(f"| 已完成 | {summary['completed_samples']} |")
    lines.append(f"| 部分完成 | {summary['partial_samples']} |")
    lines.append(f"| 失败 | {summary['failed_samples']} |")
    lines.append(f"| 待运行 | {summary['pending_samples']} |")
    lines.append(f"| 总运行次数 | {summary['total_runs']} |")
    lines.append(f"| 成功次数 | {summary['successful_runs']} |")
    lines.append("")

    # Token 统计
    ts = summary["token_stats"]
    lines.append("## 二、Token 消耗")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|---|---|")
    lines.append(f"| 总 prompt tokens | {ts['total_prompt_tokens']:,} |")
    lines.append(f"| 总 completion tokens | {ts['total_completion_tokens']:,} |")
    lines.append(f"| 总 tokens | {ts['total_tokens']:,} |")
    lines.append(f"| 平均 prompt tokens | {ts['avg_prompt_tokens']:,} |")
    lines.append(f"| 平均 completion tokens | {ts['avg_completion_tokens']:,} |")
    lines.append(f"| 平均 total tokens | {ts['avg_total_tokens']:,} |")
    lines.append("")

    # 最耗 token 的合同
    token_rows = [r for r in rows if r["avg_total_tokens"] > 0]
    token_rows.sort(key=lambda r: r["avg_total_tokens"], reverse=True)
    if token_rows:
        lines.append("### 最耗 Token 的合同（Top 5）")
        lines.append("")
        lines.append("| 合同 | 类型 | 平均 total tokens |")
        lines.append(f"|---|---|---|")
        for r in token_rows[:5]:
            lines.append(f"| {r['title'] or r['dir_name']} | {r['contract_type']} | {r['avg_total_tokens']:,} |")
        lines.append("")

    # 耗时统计
    ls = summary["latency_stats"]
    lines.append("## 三、耗时统计")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|---|---|")
    lines.append(f"| 平均延迟 | {ls['avg_latency_ms']:,} ms |")
    lines.append(f"| 最大延迟 | {ls['max_latency_ms']:,} ms |")
    lines.append(f"| 最小延迟 | {ls['min_latency_ms']:,} ms |")
    lines.append(f"| 平均总耗时 | {ls['avg_duration_sec']} 秒 |")
    lines.append("")

    # 最耗时的合同
    latency_rows = [r for r in rows if r["avg_latency_ms"] > 0]
    latency_rows.sort(key=lambda r: r["avg_latency_ms"], reverse=True)
    if latency_rows:
        lines.append("### 耗时最长的合同（Top 5）")
        lines.append("")
        lines.append("| 合同 | 类型 | 平均延迟 (ms) | 平均耗时 (秒) |")
        lines.append(f"|---|---|---|---|")
        for r in latency_rows[:5]:
            lines.append(f"| {r['title'] or r['dir_name']} | {r['contract_type']} | {r['avg_latency_ms']:,} | {r['avg_duration_sec']} |")
        lines.append("")

    # 风险统计
    rs = summary["risk_stats"]
    lines.append("## 四、风险统计")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|---|---|")
    lines.append(f"| 总风险数 | {rs['total_risks']} |")
    lines.append(f"| 总高风险 | {rs['total_high']} |")
    lines.append(f"| 总矛盾数 | {rs['total_contradictions']} |")
    lines.append(f"| 总缺失条款 | {rs['total_missing_clauses']} |")
    lines.append(f"| 平均每合同风险数 | {rs['avg_risks_per_contract']} |")
    lines.append("")

    # 质量统计
    qs = summary["quality_stats"]
    lines.append("## 五、质量统计")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|---|---|")
    lines.append(f"| 触发 fallback | {qs['fallback_triggered']} 次 |")
    lines.append(f"| Schema 清洗 | {qs['schema_cleaned']} 次 |")
    lines.append(f"| RAG 启用 | {qs['rag_enabled']} 次 |")
    lines.append("")

    # 模型使用
    lines.append("## 六、模型使用分布")
    lines.append("")
    lines.append("| 模型 | 使用次数 |")
    lines.append(f"|---|---|")
    for model, count in summary["model_usage"].items():
        lines.append(f"| {model} | {count} |")
    lines.append("")

    # 失败与漂移分析
    failed_rows = [r for r in rows if r["status"] in ("失败", "待运行")]
    if failed_rows:
        lines.append("## 七、失败与待运行样本")
        lines.append("")
        lines.append("| 合同 | 状态 | 错误信息 |")
        lines.append(f"|---|---|---|")
        for r in failed_rows:
            error = r.get("error", "") or "未运行"
            lines.append(f"| {r['title'] or r['dir_name']} | {r['status']} | {error[:60]} |")
        lines.append("")

    # 复审建议
    lines.append("## 八、复审优先级建议")
    lines.append("")
    lines.append("以下合同最值得做 3 次复审：")
    lines.append("")

    # 高风险 + 高 token + 高耗时 的合同
    priority_rows = [r for r in rows if r["status"] == "成功"]
    priority_rows.sort(
        key=lambda r: (r["high_count"] * 3 + r["contradiction_count"] * 2 + r["avg_total_tokens"] / 1000),
        reverse=True,
    )
    if priority_rows:
        lines.append("| 优先级 | 合同 | 高风险 | 矛盾 | 平均 tokens | 理由 |")
        lines.append(f"|---|---|---|---|---|---|")
        for i, r in enumerate(priority_rows[:10], 1):
            reasons = []
            if r["high_count"] >= 3:
                reasons.append("高风险多")
            if r["contradiction_count"] >= 2:
                reasons.append("矛盾多")
            if r["avg_total_tokens"] > 3000:
                reasons.append("高 token")
            if r.get("fallback_triggered"):
                reasons.append("有 fallback")
            if r.get("schema_cleaned"):
                reasons.append("有 schema 清洗")
            if not reasons:
                reasons.append("常规复审")
            lines.append(f"| {i} | {r['title'] or r['dir_name']} | {r['high_count']} | {r['contradiction_count']} | {r['avg_total_tokens']:,} | {', '.join(reasons)} |")
        lines.append("")

    # 常见错误
    error_rows = [r for r in rows if r.get("error")]
    if error_rows:
        lines.append("## 九、常见错误")
        lines.append("")
        error_types: dict[str, int] = {}
        for r in error_rows:
            err = r["error"][:50] if r["error"] else "未知"
            error_types[err] = error_types.get(err, 0) + 1
        lines.append("| 错误类型 | 出现次数 |")
        lines.append(f"|---|---|")
        for err, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {err} | {count} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 `scripts/batch_summarize.py` 自动生成。*")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="批跑结果汇总工具")
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="仅汇总每个样本最新一次成功 run",
    )
    args = parser.parse_args()

    print(f"扫描目录: {BATCH_DIR}")

    # ─── 全历史模式 ─────────────────────────────────────────────────────
    samples = scan_samples()
    print(f"找到 {len(samples)} 个样本目录")

    summary = compute_summary(samples)
    rows = build_per_sample_rows(samples)

    # 创建输出目录
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    # 输出 JSON
    json_path = SUMMARY_DIR / "batch_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成: {json_path}")

    # 输出 CSV
    csv_path = SUMMARY_DIR / "batch_summary.csv"
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"已生成: {csv_path}")

    # 输出 Markdown 报告
    report_md = generate_report_md(summary, rows)
    md_path = SUMMARY_DIR / "batch_report.md"
    md_path.write_text(report_md, encoding="utf-8")
    print(f"已生成: {md_path}")

    # 打印摘要
    print(f"\n=== 批次摘要（全历史） ===")
    print(f"总样本: {summary['total_samples']}")
    print(f"已完成: {summary['completed_samples']}, 部分: {summary['partial_samples']}, 失败: {summary['failed_samples']}, 待运行: {summary['pending_samples']}")
    print(f"总 tokens: {summary['token_stats']['total_tokens']:,}")
    print(f"平均延迟: {summary['latency_stats']['avg_latency_ms']:,} ms")

    # ─── Latest-only 模式 ───────────────────────────────────────────────
    if args.latest_only:
        print(f"\n{'='*60}")
        print("Latest-Only 模式：仅汇总每个样本最新成功 run")

        samples_lo = scan_samples_latest_only()
        summary_lo = compute_summary(samples_lo)
        rows_lo = build_per_sample_rows(samples_lo)

        # 输出 JSON
        json_path_lo = SUMMARY_DIR / "latest_only_batch_summary.json"
        json_path_lo.write_text(json.dumps(summary_lo, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已生成: {json_path_lo}")

        # 输出 CSV
        csv_path_lo = SUMMARY_DIR / "latest_only_batch_summary.csv"
        if rows_lo:
            with open(csv_path_lo, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=rows_lo[0].keys())
                writer.writeheader()
                writer.writerows(rows_lo)
            print(f"已生成: {csv_path_lo}")

        # 输出 Markdown 报告
        report_md_lo = generate_report_md(summary_lo, rows_lo, mode="latest_only")
        md_path_lo = SUMMARY_DIR / "latest_only_batch_report.md"
        md_path_lo.write_text(report_md_lo, encoding="utf-8")
        print(f"已生成: {md_path_lo}")

        # 打印摘要
        print(f"\n=== 批次摘要（latest-only） ===")
        print(f"总样本: {summary_lo['total_samples']}")
        print(f"已完成: {summary_lo['completed_samples']}, 部分: {summary_lo['partial_samples']}, 失败: {summary_lo['failed_samples']}, 待运行: {summary_lo['pending_samples']}")
        print(f"总 tokens: {summary_lo['token_stats']['total_tokens']:,}")
        print(f"平均延迟: {summary_lo['latency_stats']['avg_latency_ms']:,} ms")


if __name__ == "__main__":
    main()
