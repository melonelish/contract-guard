"""
批量真实审查脚本：上传 DOCX → 触发审查 → 轮询 → 保存结果。

用法:
    python scripts/batch_review.py [--contracts CONTRACT_DIR ...] [--runs N]

依赖: requests
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000/api/v1"
BATCH_ROOT = Path("D:/FaLvXM/07-testing/generated/batch-01")

# 前 10 高价值样本
TOP10 = [
    "contract-004-procurement-it",
    "contract-013-custom-erp",
    "contract-016-custom-blockchain",
    "contract-015-custom-ai",
    "contract-011-saas-hr",
    "contract-020-nda-partner",
    "contract-010-saas-erp",
    "contract-021-consultant-tech",
    "contract-025-agency-regional",
    "contract-026-agency-product",
]


def get_token():
    """注册/登录获取 token。"""
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"batch-{int(time.time())}@contractguard.com",
        "password": "BatchTest123!",
        "name": "Batch Tester",
        "tenant_name": "Batch Test Tenant",
    })
    if resp.status_code == 200:
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]["access_token"]
    # Fallback: try login
    resp2 = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "test@contractguard.com",
        "password": "Test123456!",
    })
    if resp2.status_code == 200:
        data = resp2.json()
        if data.get("code") == 0:
            return data["data"]["access_token"]
    raise RuntimeError(f"Auth failed: {resp.text[:200]}")


def upload_contract(token, docx_path):
    """上传合同 DOCX，返回 contract_id。"""
    with open(docx_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/contracts/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (os.path.basename(docx_path), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Upload failed: {data}")
    return data["data"]["id"]


def trigger_review(token, contract_id):
    """触发审查，返回 review_id。"""
    resp = requests.post(
        f"{BASE_URL}/contracts/{contract_id}/review",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Trigger failed: {data}")
    return data["data"]["id"]


def poll_review(token, review_id, timeout=300, interval=10):
    """轮询审查状态，返回最终状态。"""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{BASE_URL}/reviews/{review_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json().get("data", {})
        status = data.get("status", "unknown")
        if status in ("completed", "failed"):
            return data
        time.sleep(interval)
    return {"status": "timeout"}


def get_report(token, review_id):
    """获取完整审查报告。"""
    resp = requests.get(
        f"{BASE_URL}/reviews/{review_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json().get("data", {})


def get_next_run_number(contract_dir: Path) -> int:
    """扫描已有 review_run_XX.json，返回下一个可用编号，绝不覆盖。"""
    import glob
    existing = glob.glob(str(contract_dir / "review_run_*.json"))
    # 排除 _raw.json
    existing = [p for p in existing if not p.endswith("_raw.json")]
    if not existing:
        return 1
    numbers = []
    for p in existing:
        name = Path(p).stem  # review_run_01
        parts = name.split("_")
        try:
            numbers.append(int(parts[-1]))
        except ValueError:
            continue
    return max(numbers, default=0) + 1


def run_single_review(token, contract_dir, run_number):
    """对单个合同执行一次审查，返回结果 dict。"""
    contract_name = contract_dir.name
    docx_path = contract_dir / "contract_source.docx"
    pdf_path = contract_dir / "contract_source.pdf"

    result = {
        "contract_id_dir": contract_name,
        "run_number": run_number,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "upload_success": False,
        "trigger_success": False,
        "poll_success": False,
        "review_id": None,
        "contract_id": None,
        "status": None,
        "provider_model": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "latency_ms": None,
        "risk_count": None,
        "high_count": None,
        "medium_count": None,
        "low_count": None,
        "contradiction_count": None,
        "missing_clause_count": None,
        "rag_enabled": None,
        "rag_hit_count": None,
        "rag_mode": None,
        "schema_cleaned": False,
        "fallback_triggered": False,
        "error": None,
        "started_at": None,
        "completed_at": None,
        "duration_sec": None,
    }

    log_lines = [f"# 执行日志 - {contract_name} - Run {run_number}", ""]
    log_lines.append(f"开始时间: {datetime.now().isoformat()}")

    # Step 1: Upload
    upload_file = docx_path if docx_path.exists() else pdf_path
    if not upload_file.exists():
        result["error"] = "No docx or pdf found"
        log_lines.append(f"[FAIL] 上传文件不存在: {upload_file}")
        return result, "\n".join(log_lines)

    log_lines.append(f"上传文件: {upload_file.name} ({upload_file.stat().st_size} bytes)")

    try:
        contract_id = upload_contract(token, str(upload_file))
        result["contract_id"] = contract_id
        result["upload_success"] = True
        log_lines.append(f"[OK] 上传成功: contract_id={contract_id}")
    except Exception as e:
        result["error"] = f"Upload: {e}"
        log_lines.append(f"[FAIL] 上传失败: {e}")
        return result, "\n".join(log_lines)

    # Step 2: Trigger review
    try:
        review_id = trigger_review(token, contract_id)
        result["review_id"] = review_id
        result["trigger_success"] = True
        result["started_at"] = datetime.now().isoformat()
        log_lines.append(f"[OK] 触发审查成功: review_id={review_id}")
    except Exception as e:
        result["error"] = f"Trigger: {e}"
        log_lines.append(f"[FAIL] 触发审查失败: {e}")
        return result, "\n".join(log_lines)

    # Step 3: Poll
    try:
        status_data = poll_review(token, review_id, timeout=300, interval=10)
        result["status"] = status_data.get("status", "unknown")
        result["poll_success"] = status_data.get("status") in ("completed", "failed")
        result["completed_at"] = datetime.now().isoformat()
        log_lines.append(f"[OK] 轮询完成: status={result['status']}")
    except Exception as e:
        result["error"] = f"Poll: {e}"
        log_lines.append(f"[FAIL] 轮询失败: {e}")
        return result, "\n".join(log_lines)

    if result["status"] != "completed":
        result["error"] = f"Review not completed: {result['status']}"
        error_detail = status_data.get("error_detail", "")
        if error_detail:
            result["error"] += f" | {error_detail}"
        log_lines.append(f"[FAIL] 审查未完成: {result['status']}")
        if error_detail:
            log_lines.append(f"  错误详情: {error_detail}")
        return result, "\n".join(log_lines)

    # Step 4: Get report
    try:
        report = get_report(token, review_id)

        # Extract summary
        summary = report.get("summary", {})
        result["risk_count"] = summary.get("total_risks", 0)
        result["high_count"] = summary.get("high", 0)
        result["medium_count"] = summary.get("medium", 0)
        result["low_count"] = summary.get("low", 0)

        # Extract counts
        result["contradiction_count"] = len(report.get("contradictions", []))
        result["missing_clause_count"] = len(report.get("missing_clauses", []))

        # Extract LLM meta
        llm_meta = report.get("llm_meta", {})
        result["provider_model"] = llm_meta.get("provider_model")
        result["prompt_tokens"] = llm_meta.get("prompt_tokens")
        result["completion_tokens"] = llm_meta.get("completion_tokens")
        result["latency_ms"] = llm_meta.get("latency_ms")

        if result["prompt_tokens"] and result["completion_tokens"]:
            result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"]

        # Extract RAG meta
        rag_meta = report.get("rag_meta", {})
        result["rag_enabled"] = rag_meta.get("enabled")
        result["rag_hit_count"] = rag_meta.get("hit_count")
        result["rag_mode"] = rag_meta.get("mode")

        # Calculate duration
        if result["started_at"] and result["completed_at"]:
            start_dt = datetime.fromisoformat(result["started_at"])
            end_dt = datetime.fromisoformat(result["completed_at"])
            result["duration_sec"] = round((end_dt - start_dt).total_seconds(), 1)

        result["success"] = True
        log_lines.append(f"[OK] 报告获取成功")
        log_lines.append(f"  模型: {result['provider_model']}")
        log_lines.append(f"  tokens: {result['prompt_tokens']}+{result['completion_tokens']}={result['total_tokens']}")
        log_lines.append(f"  latency: {result['latency_ms']}ms")
        log_lines.append(f"  风险: {result['risk_count']} (高{result['high_count']} 中{result['medium_count']} 低{result['low_count']})")
        log_lines.append(f"  矛盾: {result['contradiction_count']}")
        log_lines.append(f"  缺失: {result['missing_clause_count']}")
        log_lines.append(f"  RAG: enabled={result['rag_enabled']}, hits={result['rag_hit_count']}")

        # Save full report
        report_path = contract_dir / f"review_run_{run_number:02d}_raw.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            log_lines.append(f"[OK] 原始报告已保存: {report_path.name}")
        except Exception as e:
            log_lines.append(f"[WARN] 原始报告保存失败: {e}")

    except Exception as e:
        result["error"] = f"Report: {e}"
        log_lines.append(f"[FAIL] 报告获取失败: {e}")

    log_lines.append(f"\n结束时间: {datetime.now().isoformat()}")
    if result["duration_sec"]:
        log_lines.append(f"总耗时: {result['duration_sec']}秒")

    return result, "\n".join(log_lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", nargs="*", help="Contract directory names")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per contract")
    parser.add_argument("--all", action="store_true", help="Run all 33 contracts")
    args = parser.parse_args()

    if args.all:
        contract_dirs = sorted([BATCH_ROOT / d for d in os.listdir(BATCH_ROOT)
                                if d.startswith("contract-") and (BATCH_ROOT / d).is_dir()])
    elif args.contracts:
        contract_dirs = [BATCH_ROOT / c for c in args.contracts]
    else:
        contract_dirs = [BATCH_ROOT / c for c in TOP10]

    num_runs = args.runs
    print(f"批量审查: {len(contract_dirs)} 份合同, 每份 {num_runs} 次")
    print(f"模型优先级: MiMo 2.5 Pro → DeepSeek V4-Flash fallback\n")

    # Get auth token
    print("获取认证 token...")
    try:
        token = get_token()
        print(f"Token 获取成功 (len={len(token)})\n")
    except Exception as e:
        print(f"Token 获取失败: {e}")
        sys.exit(1)

    all_results = []

    for contract_dir in contract_dirs:
        contract_name = contract_dir.name
        print(f"{'='*60}")
        print(f"[{contract_name}]")

        run_results = []
        base_run = get_next_run_number(contract_dir)
        for i in range(num_runs):
            run_num = base_run + i
            print(f"  Run {run_num} (auto-increment)...", end="", flush=True)
            result, log_text = run_single_review(token, contract_dir, run_num)
            run_results.append(result)

            # Save execution log
            log_path = contract_dir / f"execution_log_run_{run_num:02d}.md"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(log_text)

            # Save review_run_XX.json
            run_path = contract_dir / f"review_run_{run_num:02d}.json"
            with open(run_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

            if result["success"]:
                print(f" OK ({result['duration_sec']}s, {result['risk_count']} risks, {result['total_tokens']} tokens)")
            else:
                print(f" FAILED: {result['error']}")

            # Rate limit protection
            time.sleep(3)

        all_results.extend(run_results)

    # Generate comparison report
    print(f"\n{'='*60}")
    print("生成对比报告...")

    # Group by contract — 包含本次新跑的 + 历史已有的
    from collections import defaultdict
    import glob as glob_mod
    by_contract: dict[str, list[dict]] = defaultdict(list)

    # 先把本次结果按 contract 分组
    for r in all_results:
        by_contract[r["contract_id_dir"]].append(r)

    # 再扫描每个 contract_dir 下所有已有 review_run_XX.json（不含 _raw）
    for contract_dir in contract_dirs:
        cname = contract_dir.name
        existing = glob_mod.glob(str(contract_dir / "review_run_*.json"))
        existing = [p for p in existing if not p.endswith("_raw.json")]
        seen_runs = {r["run_number"] for r in by_contract.get(cname, [])}
        for fp in existing:
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                rn = data.get("run_number")
                if rn and rn not in seen_runs:
                    by_contract[cname].append(data)
                    seen_runs.add(rn)
            except Exception:
                pass

    for contract_name, runs in by_contract.items():
        # Sort by run_number for consistent display
        runs.sort(key=lambda r: r.get("run_number", 0))
        comparison_path = BATCH_ROOT / contract_name / "review_comparison.md"
        lines = [f"# 审查对比报告 - {contract_name}", ""]
        lines.append(f"审查次数: {len(runs)}")
        lines.append(f"生成时间: {datetime.now().isoformat()}")
        lines.append("")

        # Summary table
        lines.append("## 各次审查结果")
        lines.append("")
        lines.append("| 指标 | " + " | ".join(f"Run {r.get('run_number', i+1)}" for i, r in enumerate(runs)) + " |")
        lines.append("|---|" + "|".join("---" for _ in runs) + "|")
        lines.append(f"| 状态 | " + " | ".join("OK" if r["success"] else "FAIL" for r in runs) + " |")
        lines.append(f"| 模型 | " + " | ".join(str(r.get("provider_model","?")) for r in runs) + " |")
        lines.append(f"| 风险总数 | " + " | ".join(str(r.get("risk_count","?")) for r in runs) + " |")
        lines.append(f"| 高风险 | " + " | ".join(str(r.get("high_count","?")) for r in runs) + " |")
        lines.append(f"| 中风险 | " + " | ".join(str(r.get("medium_count","?")) for r in runs) + " |")
        lines.append(f"| 低风险 | " + " | ".join(str(r.get("low_count","?")) for r in runs) + " |")
        lines.append(f"| 矛盾数 | " + " | ".join(str(r.get("contradiction_count","?")) for r in runs) + " |")
        lines.append(f"| 缺失条款 | " + " | ".join(str(r.get("missing_clause_count","?")) for r in runs) + " |")
        lines.append(f"| prompt_tokens | " + " | ".join(str(r.get("prompt_tokens","?")) for r in runs) + " |")
        lines.append(f"| completion_tokens | " + " | ".join(str(r.get("completion_tokens","?")) for r in runs) + " |")
        lines.append(f"| latency_ms | " + " | ".join(str(r.get("latency_ms","?")) for r in runs) + " |")
        lines.append(f"| RAG hits | " + " | ".join(str(r.get("rag_hit_count","?")) for r in runs) + " |")
        lines.append("")

        # Stability analysis
        if len(runs) > 1:
            lines.append("## 稳定性分析")
            lines.append("")
            risk_counts = [r["risk_count"] for r in runs if r["risk_count"] is not None]
            high_counts = [r["high_count"] for r in runs if r["high_count"] is not None]
            contra_counts = [r["contradiction_count"] for r in runs if r["contradiction_count"] is not None]
            missing_counts = [r["missing_clause_count"] for r in runs if r["missing_clause_count"] is not None]

            if risk_counts:
                lines.append(f"- 风险总数范围: {min(risk_counts)}-{max(risk_counts)} (标准差: {(sum((x-sum(risk_counts)/len(risk_counts))**2 for x in risk_counts)/len(risk_counts))**0.5:.1f})")
            if high_counts:
                lines.append(f"- 高风险范围: {min(high_counts)}-{max(high_counts)}")
            if contra_counts:
                lines.append(f"- 矛盾识别范围: {min(contra_counts)}-{max(contra_counts)}")
            if missing_counts:
                lines.append(f"- 缺失条款范围: {min(missing_counts)}-{max(missing_counts)}")

            # Token usage
            tokens = [r["total_tokens"] for r in runs if r["total_tokens"] is not None]
            if tokens:
                lines.append(f"- Token 总量范围: {min(tokens)}-{max(tokens)}")
            lines.append("")

        with open(comparison_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # Final summary
    successful = sum(1 for r in all_results if r["success"])
    failed = sum(1 for r in all_results if not r["success"])
    total_tokens = sum(r.get("total_tokens") or 0 for r in all_results if r["success"])

    print(f"\n{'='*60}")
    print(f"批量审查完成:")
    print(f"  成功: {successful}/{len(all_results)}")
    print(f"  失败: {failed}/{len(all_results)}")
    print(f"  总 token 消耗: {total_tokens}")
    print(f"  平均 token/份: {total_tokens // max(successful,1)}")


if __name__ == "__main__":
    main()
