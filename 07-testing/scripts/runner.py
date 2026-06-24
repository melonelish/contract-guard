#!/usr/bin/env python3
"""
ContractGuard — 评测运行器

支持 mock / real 双模式。
mock 模式零 token 验证通路。
real 模式预留 API 适配点，仅需接入真实审查调用即可使用。

用法:
  python runner.py --mode mock                        # 默认 mock 模式
  python runner.py --mode mock --samples 3            # mock 模式限制 3 份
  python runner.py --mode mock --limit 5              # 同上，别名
  python runner.py --mode real --samples 3            # 真实模式，抽 3 份
  python runner.py --compare run_001 run_002          # 对比两次结果
  python runner.py --list                             # 列出已完成的运行
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Windows console UTF-8 encoding workaround
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# 1. Paths
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent     # → 07-testing/
SAMPLES_DIR = BASE_DIR / "samples" / "real"
RESULTS_DIR = BASE_DIR / "results"
CONFIG_PATH = BASE_DIR / "runner_config.json"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 2. Result structure specification
# ═══════════════════════════════════════════════════════════
# Each result dict follows a three-layer structure:
#
#   [input_meta]    — sample identity, manifest data, run config
#   [execution]     — mock/real review output: parser, analyzer, duration_s
#   [expected]      — ground truth loaded from expected_output.json (present for directory-level samples)
#
# For --compare output, a fourth layer is appended:
#   [comparison]    — delta indicators: status_change, risk_delta, duration_delta


# ─────────────────────────────────────────────
# 2a. Mock implementation
# ─────────────────────────────────────────────
# Graded by sample type for varied mock feedback
MOCK_PROFILES = {
    "采购合同": {
        "parser": {"clauses_found": 18, "clauses_expected": 18, "accuracy": 1.0},
        "analyzer": {"risks_found": 9, "high_risks": 3, "medium_risks": 4, "low_risks": 2, "type_a_count": 0},
        "duration_s": 14.2,
    },
    "劳动合同": {
        "parser": {"clauses_found": 22, "clauses_expected": 22, "accuracy": 1.0},
        "analyzer": {"risks_found": 6, "high_risks": 1, "medium_risks": 3, "low_risks": 2, "type_a_count": 0},
        "duration_s": 12.8,
    },
    "技术开发合同": {
        "parser": {"clauses_found": 25, "clauses_expected": 25, "accuracy": 1.0},
        "analyzer": {"risks_found": 10, "high_risks": 2, "medium_risks": 6, "low_risks": 2, "type_a_count": 0},
        "duration_s": 18.5,
    },
    "保密协议": {
        "parser": {"clauses_found": 12, "clauses_expected": 12, "accuracy": 1.0},
        "analyzer": {"risks_found": 4, "high_risks": 1, "medium_risks": 2, "low_risks": 1, "type_a_count": 0},
        "duration_s": 9.6,
    },
    "租赁合同": {
        "parser": {"clauses_found": 16, "clauses_expected": 16, "accuracy": 1.0},
        "analyzer": {"risks_found": 6, "high_risks": 2, "medium_risks": 3, "low_risks": 1, "type_a_count": 0},
        "duration_s": 11.3,
    },
}

MOCK_DEFAULT = {
    "parser": {"clauses_found": 10, "clauses_expected": 10, "accuracy": 0.95},
    "analyzer": {"risks_found": 4, "high_risks": 1, "medium_risks": 2, "low_risks": 1, "type_a_count": 0},
    "duration_s": 10.0,
}


def _mock_response(sample_id: str, sample_dir: str = "") -> dict:
    """Return a deterministic mock response based on sample directory name."""
    for key, profile in MOCK_PROFILES.items():
        if key in sample_dir or key in sample_id:
            return {**profile, "note": "mock result — 非真实 LLM 调用"}
    return {**MOCK_DEFAULT, "note": "mock result (default) — 非真实 LLM 调用"}


# ─────────────────────────────────────────────
# 2b. Real-mode adapter point
# ─────────────────────────────────────────────
# 适配点: 替换此函数以接入真实审查接口
# 入参: sample_path (文件路径), sample_meta (dict, manifest 中的元数据)
# 返回: dict, 必须包含以下字段:
#   status: "passed" | "failed" | "skipped"
#   parser: {clauses_found, clauses_expected, accuracy}
#   analyzer: {risks_found, high_risks, medium_risks, low_risks, type_a_count,
#               false_positives, false_negatives}
#   duration_s: float

def run_real_review(sample_path: Path, sample_meta: dict | None = None) -> dict:
    """
    真实审查接口适配点。
    当前为 stub，直接返回 skipped。接入后替换为真实调用即可。
    """
    sample_id = sample_path.stem
    print(f"[REAL] 样本 {sample_id}: 真实审查接口未接入，跳过。")
    return {
        "status": "skipped",
        "note": "真实审查接口未接入，已跳过",
        "parser": {},
        "analyzer": {},
        "duration_s": 0,
    }


# ─────────────────────────────────────────────
# 3. Sample collection
# ─────────────────────────────────────────────

def collect_samples(max_samples: Optional[int] = None, sample_dir: Optional[str] = None) -> list[Path]:
    """Collect sample files from the directory tree.

    Priority: expected_output.json as sample anchor (directory-level sample).
    Falls back to .docx/.pdf/.json files for legacy compatibility.
    """
    search_dir = Path(sample_dir) if sample_dir else SAMPLES_DIR
    if not search_dir.exists():
        print(f"[WARN] 样本目录不存在: {search_dir}")
        return []

    samples: list[Path] = []
    seen_dirs: set[str] = set()

    # 1) Collect expected_output.json as sample anchors (one per directory)
    for root, _, files in os.walk(search_dir):
        if "expected_output.json" in files:
            p = Path(root) / "expected_output.json"
            samples.append(p)
            seen_dirs.add(str(root))

    # 2) Legacy: collect .docx/.pdf/.json in dirs without expected_output.json
    for root, _, files in os.walk(search_dir):
        if str(root) in seen_dirs:
            continue  # already covered by expected_output.json
        for f in files:
            if f == "expected_output.json":
                continue
            if f.endswith((".docx", ".pdf", ".json")):
                samples.append(Path(root) / f)

    if max_samples and max_samples < len(samples):
        samples = samples[:max_samples]

    return sorted(samples)


# ─────────────────────────────────────────────
# 4. Per-sample execution
# ─────────────────────────────────────────────

def _load_expected(sample_dir: Path) -> dict | None:
    """Load expected_output.json from a sample directory, if present."""
    expected_path = sample_dir / "expected_output.json"
    if not expected_path.exists():
        return None
    try:
        with open(expected_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] 无法解析 {expected_path}: {e}")
        return None


def _has_contract_source(sample_dir: Path) -> bool:
    """Check whether a contract_source.md exists in the directory."""
    return (sample_dir / "contract_source.md").exists()


def run_sample(sample_path: Path, mode: str = "mock", sample_meta: dict | None = None) -> dict:
    """Run a single sample evaluation.

    Returns a dict with three layers:
      [input_meta]  — sample_id, sample_file, mode, contract_type
      [execution]   — parser, analyzer, duration_s, status, note
      [expected]    — ground truth from expected_output.json (absent for legacy files)
    """
    # Detect whether this is an expected_output.json anchor or a legacy file
    is_expected_anchor = sample_path.name == "expected_output.json"
    sample_dir_path = sample_path.parent
    sample_dir = sample_dir_path.name

    if is_expected_anchor:
        sample_id = sample_dir  # use directory name e.g. "01-采购合同"
    else:
        sample_id = sample_path.stem

    # Detect contract type from directory name
    contract_type = ""
    for key in MOCK_PROFILES:
        if key in sample_dir or key in sample_id:
            contract_type = key
            break

    if mode == "real":
        result = run_real_review(sample_path, sample_meta)
        return {
            "sample_id": sample_id,
            "sample_file": sample_path.name,
            "contract_type": contract_type,
            "mode": "real",
            **result,
        }

    # Default: mock
    mock = _mock_response(sample_id, sample_dir)

    result = {
        # ── [input_meta] ──
        "sample_id": sample_id,
        "sample_file": sample_path.name,
        "contract_type": contract_type,
        "mode": "mock",
        # ── [execution] ──
        "status": "passed",
        "parser": mock["parser"],
        "analyzer": {
            **mock["analyzer"],
            "false_positives": [],
            "false_negatives": [],
        },
        "duration_s": mock["duration_s"],
        "note": mock.get("note", ""),
    }

    # If this is an expected_output.json anchor, enrich with ground-truth comparison
    if is_expected_anchor:
        expected = _load_expected(sample_dir_path)
        has_source = _has_contract_source(sample_dir_path)
        result["has_contract_source"] = has_source
        if expected:
            # ── [expected] ground truth layer ──
            result["expected"] = {
                "contract_type": expected.get("contract_type"),
                "priority": expected.get("priority"),
                "test_focus": expected.get("test_focus", []),
                "total_pages": expected.get("total_pages"),
                "clauses_expected": expected.get("clauses_expected"),
                "risks_count": {
                    "high": sum(1 for r in expected.get("expected_risks", []) if r.get("risk_level") == "high"),
                    "medium": sum(1 for r in expected.get("expected_risks", []) if r.get("risk_level") == "medium"),
                    "low": sum(1 for r in expected.get("expected_risks", []) if r.get("risk_level") == "low"),
                },
                "missing_clauses_count": len(expected.get("expected_missing_clauses", [])),
                "has_conflicts": expected.get("has_conflicts", False),
                "conflicts_count": len(expected.get("conflicts", [])),
                "type_a_forbidden": expected.get("type_a_forbidden", False),
            }
            # Align mock data with expected for meaningful comparison
            e_risks = result["expected"]["risks_count"]
            result["analyzer"]["high_risks"] = e_risks["high"]
            result["analyzer"]["medium_risks"] = e_risks["medium"]
            result["analyzer"]["low_risks"] = e_risks["low"]
            result["analyzer"]["risks_found"] = e_risks["high"] + e_risks["medium"] + e_risks["low"]
            result["parser"]["clauses_expected"] = expected.get("clauses_expected",
                                                               result["parser"].get("clauses_expected", 0))
            result["parser"]["clauses_found"] = result["parser"]["clauses_expected"]

    return result


# ─────────────────────────────────────────────
# 5. Batch run + markdown output
# ─────────────────────────────────────────────

def _build_run_summary(meta: dict, run_id: str) -> str:
    """Build markdown summary text for a batch run."""
    lines = [
        f"# 评测运行: `{run_id}`",
        "",
        f"| 项目 | 值 |",
        f"|---|---|",
        f"| 运行模式 | `{meta['mode']}` |",
        f"| 时间戳 | {meta['timestamp']} |",
        f"| 样本总数 | {meta['samples_count']} |",
        f"| 通过 | {meta['passed']} |",
        f"| 失败 | {meta['failed']} |",
        f"| 跳过 | {meta['skipped']} |",
        f"| Type-A 幻觉 | {meta['type_a_total']} |",
        "",
        "## 逐样本明细",
        "",
        "| 样本 | 合同类型 | 状态 | 高风险 | 中风险 | 低风险 | 缺失 | 冲突 | 耗时 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for r in meta.get("results", []):
        sid = r.get("sample_id", "?")
        ctype = r.get("contract_type", "-")
        status = r.get("status", "?")
        az = r.get("analyzer", {}) if isinstance(r.get("analyzer"), dict) else {}
        h = az.get("high_risks", "-")
        m = az.get("medium_risks", "-")
        lo = az.get("low_risks", "-")
        exp = r.get("expected", {}) if isinstance(r.get("expected"), dict) else {}
        mc = exp.get("missing_clauses_count", "-")
        cf = "Y" if exp.get("has_conflicts") else ("N" if "has_conflicts" in exp else "-")
        dur = f"{r.get('duration_s', 0):.1f}s"
        status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(status, "❓")
        lines.append(f"| {sid} | {ctype} | {status_emoji} {status} | {h} | {m} | {lo} | {mc} | {cf} | {dur} |")

    lines.append("")
    lines.append("> 完整结果见对应 JSON 文件。")
    return "\n".join(lines)


def _write_md_summary(run_id: str, data: dict) -> Path:
    """Write a markdown summary alongside the JSON result."""
    md_path = RESULTS_DIR / f"{run_id}.md"
    md_text = _build_run_summary(data, run_id)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    return md_path


def batch_run(mode: str = "mock", max_samples: Optional[int] = None) -> dict:
    """Run batch evaluation. Produces both .json and .md output files."""
    samples = collect_samples(max_samples)
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    results = [run_sample(s, mode) for s in samples]
    passed = sum(1 for r in results if r.get("status") == "passed")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    failed = sum(1 for r in results if r.get("status") == "failed")
    type_a_total = sum(
        r.get("analyzer", {}).get("type_a_count", 0) for r in results if isinstance(r.get("analyzer"), dict)
    )

    summary = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "samples_count": len(samples),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "type_a_total": type_a_total,
        "results": results,
    }

    # Write JSON
    json_path = RESULTS_DIR / f"{run_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Write Markdown summary
    md_path = _write_md_summary(run_id, summary)

    print(f"\n{'='*50}")
    print(f"✅ 运行完成: {run_id}")
    print(f"   样本数: {len(samples)}  通过: {passed}  失败: {failed}  跳过: {skipped}")
    print(f"   JSON : {json_path}")
    print(f"   MD   : {md_path}")
    print(f"{'='*50}")
    return summary


# ─────────────────────────────────────────────
# 6. Compare + save to file
# ─────────────────────────────────────────────

def compare_runs(run_a: str, run_b: str) -> Optional[dict]:
    """Compare two run results and save the comparison to a markdown file.

    Returns a comparison dict; also writes {RESULTS_DIR}/compare_{A}_vs_{B}.md

    Compares per-sample:
      - status changes (passed/failed/skipped)
      - risk counts (high/medium/low/total)
      - missing clauses count
      - conflicts presence
      - duration delta

    Gracefully degrades when a field is missing from either result.
    """
    def load(path: Path):
        if not path.exists():
            print(f"[ERROR] 找不到文件: {path}")
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _safe_get(d: dict, *keys, default=None) -> Any:
        """Safely navigate nested dict keys, returning default on any failure."""
        cur = d
        for k in keys:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k)
            if cur is None:
                return default
        return cur

    data_a = load(RESULTS_DIR / f"{run_a}.json")
    data_b = load(RESULTS_DIR / f"{run_b}.json")
    if not data_a or not data_b:
        return None

    # ── Build markdown output ──
    md_lines = [
        f"# 评测对比: `{run_a}` vs `{run_b}`",
        "",
        f"## 总体摘要",
        "",
    ]

    sc_a = data_a.get("samples_count", 0)
    sc_b = data_b.get("samples_count", 0)
    md_lines.append(f"| 指标 | 基准 ({run_a}) | 对比 ({run_b}) | 变化 |")
    md_lines.append(f"|---|---|---|---|")
    md_lines.append(f"| 样本数 | {sc_a} | {sc_b} | {sc_b - sc_a:+d} |")
    md_lines.append(f"| 通过 | {data_a.get('passed', '?')} | {data_b.get('passed', '?')} | - |")
    md_lines.append(f"| 失败 | {data_a.get('failed', '?')} | {data_b.get('failed', '?')} | - |")
    md_lines.append(f"| Type-A | {data_a.get('type_a_total', 0)} | {data_b.get('type_a_total', 0)} | - |")
    md_lines.append("")

    # ── Console output ──
    print(f"\n{'='*56}")
    print(f"  Compare: {run_a}  vs  {run_b}")
    print(f"{'='*56}")
    print(f"  Samples      : {sc_a} → {sc_b}  ({'+' if sc_b >= sc_a else ''}{sc_b - sc_a})")
    print(f"  Passed       : {data_a.get('passed', '?')} → {data_b.get('passed', '?')}")
    print(f"  Failed       : {data_a.get('failed', '?')} → {data_b.get('failed', '?')}")
    print(f"  Type-A total : {data_a.get('type_a_total', 0)} → {data_b.get('type_a_total', 0)}")
    print()

    # ── Per-sample detail ──
    results_a: list = data_a.get("results", [])
    results_b: list = data_b.get("results", [])
    map_a = {r.get("sample_id", "?"): r for r in results_a}
    map_b = {r.get("sample_id", "?"): r for r in results_b}
    all_ids = sorted(set(map_a) | set(map_b))

    md_lines.append("## 逐样本明细")
    md_lines.append("")
    md_lines.append("| Sample | Status | Risks(H/M/L) | Missing | Conflict | Duration |")
    md_lines.append("|---|---|---|---|---|---|")

    changes = 0
    print(f"  {'Sample':20s}  {'Status':8s}  {'Risks(H/M/L)':14s}  {'Missing':7s}  {'Conflict':8s}  {'Duration':8s}")
    print(f"  {'-'*20}  {'-'*8}  {'-'*14}  {'-'*7}  {'-'*8}  {'-'*8}")

    row_changes = 0  # track per-sample structural change count

    for sid in all_ids:
        ra = map_a.get(sid, {})
        rb = map_b.get(sid, {})

        # ── Status ──
        sta = ra.get("status", "?")
        stb = rb.get("status", "?")
        status_str = f"{sta}→{stb}" if sta != stb else sta
        if sta != stb:
            row_changes += 1

        # ── Risk counts ──
        def risk_str(r: dict) -> str:
            if not isinstance(r, dict):
                return "?/?/?"
            az = r.get("analyzer", {}) if isinstance(r.get("analyzer"), dict) else {}
            h = az.get("high_risks", "?")
            m = az.get("medium_risks", "?")
            l = az.get("low_risks", "?")
            return f"{h}/{m}/{l}"

        risk_a = risk_str(ra)
        risk_b = risk_str(rb)
        risk_str_out = f"{risk_a}→{risk_b}" if risk_a != risk_b else risk_a
        if risk_a != risk_b:
            row_changes += 1

        # ── Missing clauses ──
        mc_a = _safe_get(ra, "expected", "missing_clauses_count", default="?")
        mc_b = _safe_get(rb, "expected", "missing_clauses_count", default="?")
        mc_str = f"{mc_a}→{mc_b}" if mc_a != mc_b else str(mc_a)

        # ── Conflicts ──
        cf_a = _safe_get(ra, "expected", "has_conflicts")
        cf_b = _safe_get(rb, "expected", "has_conflicts")
        if cf_a is None and cf_b is None:
            cf_str = "-"
        elif cf_a == cf_b:
            cf_str = "Y" if cf_a else "N"
        else:
            cf_str = f"{'Y' if cf_a else 'N'}→{'Y' if cf_b else 'N'}"
            row_changes += 1

        # ── Duration ──
        da = ra.get("duration_s", 0) or 0
        db = rb.get("duration_s", 0) or 0
        dur_str = f"{da:.1f}s→{db:.1f}s" if abs(da - db) > 0.05 else f"{da:.1f}s"
        if abs(da - db) > 0.05:
            row_changes += 1

        print(f"  {sid:20s}  {status_str:8s}  {risk_str_out:14s}  {mc_str:7s}  {cf_str:8s}  {dur_str:8s}")
        md_lines.append(f"| {sid} | {status_str} | {risk_str_out} | {mc_str} | {cf_str} | {dur_str} |")

    changes = row_changes

    print()
    if changes == 0:
        print("  No changes detected between the two runs.")
        md_lines.append("")
        md_lines.append("**结论**: 两次运行结果完全一致，无变化。")
    else:
        print(f"  {changes} field(s) changed across all samples.")
        md_lines.append("")
        md_lines.append(f"**结论**: {changes} 处字段发生变化。")
    print(f"{'='*56}\n")

    # ── Save comparison markdown ──
    compare_id = f"compare_{run_a}_vs_{run_b}"
    md_path = RESULTS_DIR / f"{compare_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"📄 对比报告已保存: {md_path}")

    return {"compare_id": compare_id, "run_a": run_a, "run_b": run_b, "changes_count": changes}


# ─────────────────────────────────────────────
# 7. List runs
# ─────────────────────────────────────────────

def list_runs() -> None:
    """List completed runs."""
    runs = sorted(RESULTS_DIR.glob("run_*.json"), reverse=True)
    if not runs:
        print("  暂无已完成运行。")
        return
    print(f"\n{'='*50}")
    print("📋 已完成运行列表")
    print(f"{'='*50}")
    for r in runs:
        try:
            with open(r, encoding="utf-8") as f:
                d = json.load(f)
            status = f"✅ {d.get('passed', 0)}/{d.get('samples_count', 0)} 通过 | mode={d.get('mode','?')}"
            # Also check if .md companion exists
            md_file = r.with_suffix(".md")
            has_md = " + MD" if md_file.exists() else ""
        except Exception:
            status = "⚠ 解析失败"
        print(f"  {r.stem}  {status}{has_md}")
    print()


# ─────────────────────────────────────────────
# 8. CLI
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="ContractGuard 评测运行器")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock",
                        help="运行模式: mock(默认零token) / real(谨慎)")
    parser.add_argument("--samples", type=int, default=None,
                        help="限制样本数")
    parser.add_argument("--limit", type=int, default=None,
                        help="限制样本数（--samples 的别名）")
    parser.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"),
                        help="对比两次运行结果，同时保存对比报告")
    parser.add_argument("--list", action="store_true",
                        help="列出已完成运行")
    args = parser.parse_args()

    if args.list:
        list_runs()
    elif args.compare:
        compare_runs(args.compare[0], args.compare[1])
    else:
        max_n = args.samples or args.limit
        batch_run(mode=args.mode, max_samples=max_n)


if __name__ == "__main__":
    main()
