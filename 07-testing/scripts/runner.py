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

# ─────────────────────────────────────────────
# 1. Paths
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent     # → 07-testing/
SAMPLES_DIR = BASE_DIR / "samples" / "real"
RESULTS_DIR = BASE_DIR / "results"
CONFIG_PATH = BASE_DIR / "runner_config.json"

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# 2. Mock implementation
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
# 3. Real-mode adapter point
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
# 4. Core logic
# ─────────────────────────────────────────────

def collect_samples(max_samples: Optional[int] = None, sample_dir: Optional[str] = None) -> list[Path]:
    """Collect sample files from the directory tree."""
    search_dir = Path(sample_dir) if sample_dir else SAMPLES_DIR
    if not search_dir.exists():
        print(f"[WARN] 样本目录不存在: {search_dir}")
        return []

    samples: list[Path] = []
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f.endswith((".docx", ".pdf", ".json")):
                samples.append(Path(root) / f)

    if max_samples and max_samples < len(samples):
        samples = samples[:max_samples]

    return sorted(samples)


def run_sample(sample_path: Path, mode: str = "mock", sample_meta: dict | None = None) -> dict:
    """Run a single sample evaluation."""
    sample_id = sample_path.stem
    sample_dir = sample_path.parent.name

    if mode == "real":
        result = run_real_review(sample_path, sample_meta)
        return {"sample_id": sample_id, "sample_file": sample_path.name, "mode": "real", **result}

    # Default: mock
    mock = _mock_response(sample_id, sample_dir)
    return {
        "sample_id": sample_id,
        "sample_file": sample_path.name,
        "mode": "mock",
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


def batch_run(mode: str = "mock", max_samples: Optional[int] = None) -> dict:
    """Run batch evaluation."""
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

    result_path = RESULTS_DIR / f"{run_id}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 运行完成: {run_id}")
    print(f"   样本数: {len(samples)}  通过: {passed}  失败: {failed}  跳过: {skipped}")
    print(f"   结果文件: {result_path}")
    print(f"{'='*50}")
    return summary


def compare_runs(run_a: str, run_b: str) -> None:
    """Human-friendly comparison of two run results."""
    def load(path: Path):
        if not path.exists():
            print(f"[ERROR] 找不到文件: {path}")
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    data_a = load(RESULTS_DIR / f"{run_a}.json")
    data_b = load(RESULTS_DIR / f"{run_b}.json")
    if not data_a or not data_b:
        return

    print(f"\n{'='*50}")
    print(f"📊 对比: {run_a}  vs  {run_b}")
    print(f"{'='*50}")
    print(f"  基准通过数: {data_a.get('passed', '?')}/{data_a.get('samples_count', '?')}")
    print(f"  对比通过数: {data_b.get('passed', '?')}/{data_b.get('samples_count', '?')}")
    print(f"  Type A 变化: {data_a.get('type_a_total', 0)} → {data_b.get('type_a_total', 0)}")
    print()

    # Per-sample comparison
    results_a: list = data_a.get("results", [])
    results_b: list = data_b.get("results", [])
    map_a = {r["sample_id"]: r for r in results_a}
    map_b = {r["sample_id"]: r for r in results_b}
    changed = 0
    for sid in set(map_a) | set(map_b):
        ra = map_a.get(sid, {})
        rb = map_b.get(sid, {})
        if ra.get("status") != rb.get("status"):
            changed += 1
            sa = ra.get("status", "?")
            sb = rb.get("status", "?")
            print(f"   ⚠ {sid}: {sa} → {sb}" if ra else f"   + {sid}: - → {sb}" if rb else f"   - {sid}: {sa} → -")
        else:
            da = ra.get("duration_s", 0) or 0
            db = rb.get("duration_s", 0) or 0
            if da != db:
                print(f"   ~ {sid}: 耗时 {da}s → {db}s")

    if changed == 0:
        print("  ✅ 两次运行结果一致，无状态变化。")


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
        except Exception:
            status = "⚠ 解析失败"
        print(f"  {r.stem}  {status}")
    print()


# ─────────────────────────────────────────────
# 5. CLI
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
                        help="对比两次运行结果")
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
