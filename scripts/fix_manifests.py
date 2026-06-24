"""校验并修正 batch-01 中所有 manifest.json 的统计值。"""

import json
import os
import re
import sys


def count_chinese(filepath):
    """统计文件中的中文字符数。"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def safe_load_json(filepath):
    """安全加载 JSON 文件，失败返回 None。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  [WARN] JSON 加载失败: {filepath} -> {e}")
        return None


def fix_manifest(contract_dir):
    """修正单个合同目录的 manifest.json。"""
    contract_name = os.path.basename(contract_dir)
    manifest_path = os.path.join(contract_dir, "manifest.json")
    md_path = os.path.join(contract_dir, "contract_source.md")
    risks_path = os.path.join(contract_dir, "expected_risks.json")
    missing_path = os.path.join(contract_dir, "expected_missing_clauses.json")
    contradictions_path = os.path.join(contract_dir, "expected_contradictions.json")

    # 加载现有 manifest
    manifest = safe_load_json(manifest_path)
    if manifest is None:
        print(f"  [SKIP] manifest.json 不存在或无法解析: {contract_name}")
        return False

    changed = False

    # 统计中文字符数
    if os.path.exists(md_path):
        word_count = count_chinese(md_path)
        if manifest.get("word_count") != word_count:
            print(f"  word_count: {manifest.get('word_count')} -> {word_count}")
            manifest["word_count"] = word_count
            changed = True

    # 统计风险数
    risks_data = safe_load_json(risks_path)
    if risks_data is not None:
        actual_risk_count = len(risks_data.get("risks", []))
        if manifest.get("risk_count") != actual_risk_count:
            print(f"  risk_count: {manifest.get('risk_count')} -> {actual_risk_count}")
            manifest["risk_count"] = actual_risk_count
            changed = True

    # 统计缺失条款数
    missing_data = safe_load_json(missing_path)
    if missing_data is not None:
        actual_missing_count = len(missing_data.get("missing_clauses", []))
        if manifest.get("missing_count") != actual_missing_count:
            print(f"  missing_count: {manifest.get('missing_count')} -> {actual_missing_count}")
            manifest["missing_count"] = actual_missing_count
            changed = True

    # 统计矛盾数
    contradictions_data = safe_load_json(contradictions_path)
    if contradictions_data is not None:
        actual_contradiction_count = len(contradictions_data.get("contradictions", []))
        if manifest.get("contradiction_count") != actual_contradiction_count:
            print(f"  contradiction_count: {manifest.get('contradiction_count')} -> {actual_contradiction_count}")
            manifest["contradiction_count"] = actual_contradiction_count
            changed = True

    if changed:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"  [UPDATED] {contract_name}")
        return True
    else:
        print(f"  [OK] {contract_name} (无变化)")
        return False


def main():
    base = "D:/FaLvXM/07-testing/generated/batch-01"
    updated = 0
    total = 0

    for d in sorted(os.listdir(base)):
        contract_dir = os.path.join(base, d)
        if not os.path.isdir(contract_dir) or not d.startswith("contract-"):
            continue
        manifest_path = os.path.join(contract_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            continue

        total += 1
        print(f"[{d}]")
        if fix_manifest(contract_dir):
            updated += 1

    print(f"\n修正完成: {updated}/{total} 份 manifest 被更新")


if __name__ == "__main__":
    main()
