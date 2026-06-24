#!/usr/bin/env python3
"""
ContractGuard — 评测运行器

用法:
  python runner.py --mode mock                        # mock 模式（默认，零 token）
  python runner.py --mode mock --samples 3            # mock 模式，只跑 3 份
  python runner.py --mode real --samples 3            # 真实模式，只抽 3 份（谨慎）
  python runner.py --compare run_001 run_002          # 对比两次结果
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Paths ──
BASE_DIR = Path(__file__).resolve().parent.parent  # 07-testing/
SAMPLES_DIR = BASE_DIR / "samples" / "real"
RESULTS_DIR = BASE_DIR / "results"
MANIFEST_PATH = BASE_DIR / "测试资产清单与规范.md"

os.makedirs(RESULTS_DIR, exist_ok=True)


# ── Mock data ──
MOCK_SAMPLE = {
    "parser": {"clauses_found": 18, "clauses_expected": 18, "accuracy": 1.0},
    "analyzer": {
        "risks_found": 5,
        "high_risks": 3,
        "medium_risks": 4,
        "low_risks": 2,
        "type_a_count": 0,
        "false_positives": [],
        "false_negatives": [],
    },
    "duration_s": 14.2,
    "note": "mock — 非真实 LLM 调用，仅供脚本通路验证",
}


# ── Core ──
def run_sample(sample_path: Path, mode: str = "mock") -> dict:
    """运行单个样本评测"""
    sample_id = sample_path.stem

    if mode == "mock":
        return {
            "sample_id": sample_id,
            "sample_file": sample_path.name,
            "status": "passed",
            "mode": "mock",
            **MOCK_SAMPLE,
        }

    # 真实模式：仅做接口占位，不实际调用 LLM
    print(f"[WARN] 真实审查接口未接入，请勿批量触发。样本 {sample_id} 跳过。")
    return {
        "sample_id": sample_id,
        "sample_file": sample_path.name,
        "status": "skipped",
        "mode": "real",
        "note": "接口未接入，已跳过",
    }


def collect_samples(max_samples: Optional[int] = None) -> list[Path]:
    """收集样本文件"""
    if not SAMPLES_DIR.exists():
        print(f"[WARN] 样本目录不存在: {SAMPLES_DIR}")
        print("  预期结构: 07-testing/samples/real/01-采购合同/sample_001.docx")
        return []

    samples = []
    for root, _, files in os.walk(SAMPLES_DIR):
        for f in files:
            if f.endswith((".docx", ".pdf", ".json")):
                samples.append(Path(root) / f)

    if max_samples and max_samples < len(samples):
        samples = samples[:max_samples]

    return sorted(samples)


def batch_run(mode: str = "mock", max_samples: Optional[int] = None) -> dict:
    """批量运行"""
    samples = collect_samples(max_samples)
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    results = [run_sample(s, mode) for s in samples]

    passed = sum(1 for r in results if r["status"] == "passed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    overall = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "samples_count": len(samples),
        "passed": passed,
        "skipped": skipped,
        "type_a_total": sum(r.get("analyzer", {}).get("type_a_count", 0) for r in results),
        "results": results,
    }

    # 保存结果
    result_path = RESULTS_DIR / f"{run_id}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(overall, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 运行完成: {run_id}")
    print(f"   样本数: {len(samples)}  通过: {passed}  跳过: {skipped}")
    print(f"   结果文件: {result_path}")
    return overall


def compare_runs(run_a: str, run_b: str) -> None:
    """对比两次运行结果"""
    path_a = RESULTS_DIR / f"{run_a}.json"
    path_b = RESULTS_DIR / f"{run_b}.json"

    for p, label in [(path_a, "基准"), (path_b, "对比")]:
        if not p.exists():
            print(f"[ERROR] 找不到 {label} 结果文件: {p}")
            return

    with open(path_a, encoding="utf-8") as f:
        data_a = json.load(f)
    with open(path_b, encoding="utf-8") as f:
        data_b = json.load(f)

    print(f"\n📊 对比: {run_a} vs {run_b}")
    print(f"   基准通过: {data_a.get('passed', '?')}/{data_a.get('samples_count', '?')}")
    print(f"   对比通过: {data_b.get('passed', '?')}/{data_b.get('samples_count', '?')}")


# ── CLI ──
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContractGuard 评测运行器")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock",
                        help="运行模式: mock(默认) / real(谨慎)")
    parser.add_argument("--samples", type=int, default=None,
                        help="限制运行样本数")
    parser.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"),
                        help="对比两次运行结果")
    args = parser.parse_args()

    if args.compare:
        compare_runs(args.compare[0], args.compare[1])
    else:
        batch_run(mode=args.mode, max_samples=args.samples)
