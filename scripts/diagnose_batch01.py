"""
诊断 batch-01 合同测试资产完整性。
输出 JSON 报告供后续修复使用。
"""

import json
import os
import re
from pathlib import Path

ROOT = Path("D:/FaLvXM/07-testing/generated/batch-01")
REQUIRED_FILES = [
    "contract_source.md",
    "contract_source.docx",
    "expected_risks.json",
    "expected_missing_clauses.json",
    "expected_contradictions.json",
    "generation_notes.md",
    "manifest.json",
]


def count_chinese(text: str) -> int:
    return sum(1 for c in text if "\u4e00" <= c <= "\u9fff")


def extract_body_text(md_path: str) -> str:
    """提取合同正文（去掉标题/引用块/代码块等，只算正文段落）。"""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    lines = content.split("\n")
    body_lines = []
    in_code = False
    past_header = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        # Skip pure markdown formatting lines
        if stripped.startswith("#") and not past_header:
            past_header = True
            continue
        if stripped.startswith(">"):
            continue
        if re.match(r"^[-*_]{3,}$", stripped):
            continue
        if stripped:
            body_lines.append(stripped)

    return "\n".join(body_lines)


def validate_json_file(filepath: str) -> dict:
    """尝试解析 JSON，返回 {valid, error, data}。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"valid": True, "error": None, "data": data}
    except json.JSONDecodeError as e:
        return {"valid": False, "error": str(e), "data": None}
    except Exception as e:
        return {"valid": False, "error": str(e), "data": None}


def diagnose_contract(contract_dir: Path) -> dict:
    name = contract_dir.name
    result = {
        "name": name,
        "path": str(contract_dir),
        "missing_files": [],
        "md_chinese_chars": 0,
        "md_too_short": False,
        "json_errors": {},
        "manifest_inconsistencies": [],
        "docx_exists": False,
        "pdf_exists": False,
    }

    # 1. Check file completeness
    for f in REQUIRED_FILES:
        fpath = contract_dir / f
        if not fpath.exists():
            result["missing_files"].append(f)

    result["docx_exists"] = (contract_dir / "contract_source.docx").exists()
    result["pdf_exists"] = (contract_dir / "contract_source.pdf").exists()

    # 2. Check MD content length
    md_path = contract_dir / "contract_source.md"
    if md_path.exists():
        body = extract_body_text(str(md_path))
        cn_count = count_chinese(body)
        result["md_chinese_chars"] = cn_count
        result["md_too_short"] = cn_count < 3000

    # 3. Validate JSON files
    for jf in ["expected_risks.json", "expected_missing_clauses.json",
                "expected_contradictions.json", "manifest.json"]:
        jpath = contract_dir / jf
        if jpath.exists():
            vr = validate_json_file(str(jpath))
            if not vr["valid"]:
                result["json_errors"][jf] = vr["error"]

    # 4. Check manifest consistency
    manifest_path = contract_dir / "manifest.json"
    risks_path = contract_dir / "expected_risks.json"
    missing_path = contract_dir / "expected_missing_clauses.json"
    contra_path = contract_dir / "expected_contradictions.json"

    if manifest_path.exists() and not result["json_errors"].get("manifest.json"):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            # Check risk_count
            if risks_path.exists() and not result["json_errors"].get("expected_risks.json"):
                with open(risks_path, "r", encoding="utf-8") as f:
                    risks = json.load(f)
                actual_risks = risks.get("total_risks", len(risks.get("risks", [])))
                if manifest.get("risk_count") != actual_risks:
                    result["manifest_inconsistencies"].append(
                        f"risk_count: manifest={manifest.get('risk_count')} actual={actual_risks}"
                    )

            # Check missing_count
            if missing_path.exists() and not result["json_errors"].get("expected_missing_clauses.json"):
                with open(missing_path, "r", encoding="utf-8") as f:
                    missing = json.load(f)
                actual_missing = missing.get("total_missing", len(missing.get("missing_clauses", [])))
                if manifest.get("missing_count") != actual_missing:
                    result["manifest_inconsistencies"].append(
                        f"missing_count: manifest={manifest.get('missing_count')} actual={actual_missing}"
                    )

            # Check contradiction_count
            if contra_path.exists() and not result["json_errors"].get("expected_contradictions.json"):
                with open(contra_path, "r", encoding="utf-8") as f:
                    contra = json.load(f)
                actual_contra = contra.get("total_contradictions", len(contra.get("contradictions", [])))
                if manifest.get("contradiction_count") != actual_contra:
                    result["manifest_inconsistencies"].append(
                        f"contradiction_count: manifest={manifest.get('contradiction_count')} actual={actual_contra}"
                    )

            # Check word_count against actual
            if md_path.exists():
                body = extract_body_text(str(md_path))
                actual_chars = count_chinese(body)
                manifest_wc = manifest.get("word_count", 0)
                # Allow 20% tolerance
                if manifest_wc > 0 and abs(manifest_wc - actual_chars) > actual_chars * 0.3:
                    result["manifest_inconsistencies"].append(
                        f"word_count: manifest={manifest_wc} actual={actual_chars}"
                    )

        except Exception as e:
            result["manifest_inconsistencies"].append(f"read error: {e}")

    return result


def main():
    dirs = sorted([d for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("contract-")])
    print(f"扫描到 {len(dirs)} 个合同目录\n")

    all_results = []
    summary = {
        "total": len(dirs),
        "complete_files": 0,
        "missing_files": 0,
        "short_md": [],
        "json_errors": [],
        "manifest_errors": [],
        "no_docx": [],
        "no_pdf": [],
    }

    for d in dirs:
        r = diagnose_contract(d)
        all_results.append(r)

        if not r["missing_files"]:
            summary["complete_files"] += 1
        else:
            summary["missing_files"] += 1

        if r["md_too_short"]:
            summary["short_md"].append({
                "name": r["name"],
                "chars": r["md_chinese_chars"]
            })

        if r["json_errors"]:
            summary["json_errors"].append({
                "name": r["name"],
                "errors": r["json_errors"]
            })

        if r["manifest_inconsistencies"]:
            summary["manifest_errors"].append({
                "name": r["name"],
                "issues": r["manifest_inconsistencies"]
            })

        if not r["docx_exists"]:
            summary["no_docx"].append(r["name"])

        if not r["pdf_exists"]:
            summary["no_pdf"].append(r["name"])

    # Print summary
    print("=" * 70)
    print(f"文件完整性: {summary['complete_files']}/{summary['total']} 目录具备全部 7 个文件")
    if summary["missing_files"] > 0:
        for r in all_results:
            if r["missing_files"]:
                print(f"  {r['name']}: 缺少 {r['missing_files']}")

    print(f"\nDOCX 缺失: {len(summary['no_docx'])} 份")
    print(f"PDF  缺失: {len(summary['no_pdf'])} 份")

    print(f"\n正文低于 3000 中文字: {len(summary['short_md'])} 份")
    for item in sorted(summary["short_md"], key=lambda x: x["chars"]):
        print(f"  {item['name']}: {item['chars']} 字")

    print(f"\nJSON 解析失败: {len(summary['json_errors'])} 份")
    for item in summary["json_errors"]:
        for jf, err in item["errors"].items():
            print(f"  {item['name']}/{jf}: {err[:80]}")

    print(f"\nManifest 统计不一致: {len(summary['manifest_errors'])} 份")
    for item in summary["manifest_errors"]:
        print(f"  {item['name']}: {item['issues']}")

    # Save detailed report
    report_path = ROOT / "_diagnostic_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "details": all_results}, f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存: {report_path}")


if __name__ == "__main__":
    main()
