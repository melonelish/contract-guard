"""Tests for batch_evaluate.py — golden sample evaluation tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_sample_dir(
    tmp_path: Path,
    name: str,
    expected_risks: dict | None = None,
    expected_missing: dict | None = None,
    expected_contradictions: dict | None = None,
    review_run: dict | None = None,
    raw_review: dict | None = None,
) -> Path:
    """Create a temporary sample directory with test data."""
    sample_dir = tmp_path / name
    sample_dir.mkdir()

    manifest = {
        "contract_id": name,
        "contract_type": "test",
        "title": f"Test Contract {name}",
        "difficulty": "medium",
    }
    (sample_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    if expected_risks:
        (sample_dir / "expected_risks.json").write_text(
            json.dumps(expected_risks, ensure_ascii=False), encoding="utf-8",
        )
    if expected_missing:
        (sample_dir / "expected_missing_clauses.json").write_text(
            json.dumps(expected_missing, ensure_ascii=False), encoding="utf-8",
        )
    if expected_contradictions:
        (sample_dir / "expected_contradictions.json").write_text(
            json.dumps(expected_contradictions, ensure_ascii=False), encoding="utf-8",
        )
    if review_run:
        (sample_dir / "review_run_01.json").write_text(
            json.dumps(review_run, ensure_ascii=False), encoding="utf-8",
        )
    if raw_review:
        (sample_dir / "review_run_01_raw.json").write_text(
            json.dumps(raw_review, ensure_ascii=False), encoding="utf-8",
        )

    return sample_dir


def _make_expected_risks(risk_types: list[str], severities: list[str] | None = None) -> dict:
    """Build expected_risks.json structure."""
    risks = []
    for i, rt in enumerate(risk_types):
        sev = severities[i] if severities and i < len(severities) else "medium"
        risks.append({
            "risk_id": f"R{i+1:03d}",
            "risk_type": rt,
            "severity": sev,
            "title": f"Risk {i+1}",
            "description": f"Description for {rt}",
        })
    return {"contract_id": "test", "total_risks": len(risks), "risks": risks}


def _make_review_run(success: bool = True, **overrides) -> dict:
    """Build review_run_01.json structure."""
    data = {
        "contract_id_dir": "test",
        "run_number": 1,
        "success": success,
        "status": "completed" if success else "failed",
        "provider_model": "mimo-v2.5-pro",
        "prompt_tokens": 1000,
        "completion_tokens": 2000,
        "total_tokens": 3000,
        "latency_ms": 50000,
        "risk_count": 5,
        "high_count": 2,
        "medium_count": 2,
        "low_count": 1,
        "contradiction_count": 1,
        "missing_clause_count": 3,
        "rag_enabled": True,
        "schema_cleaned": False,
        "fallback_triggered": False,
        "error": None if success else "Review failed",
        "duration_sec": 60.0,
    }
    data.update(overrides)
    return data


def _make_raw_review(categories: list[str], levels: list[str] | None = None) -> dict:
    """Build review_run_01_raw.json structure."""
    risks = []
    for i, cat in enumerate(categories):
        lvl = levels[i] if levels and i < len(levels) else "medium"
        risks.append({
            "clause_id": f"cl_{i+1:03d}",
            "clause_code": f"第{i+1}条",
            "risk_level": lvl,
            "risk_category": cat,
            "original_text": "Test clause text",
            "legal_analysis": "Analysis",
            "legal_basis": "《民法典》第123条",
            "basis_excerpt": "Law text",
            "basis_source": "民法典",
            "plain_explanation": "Explanation",
            "suggested_revision": "Fix suggestion",
            "confidence": 0.8,
        })
    return {
        "id": "test-review-id",
        "contract_id": "test-contract-id",
        "contract_title": "Test",
        "status": "completed",
        "progress": 100,
        "schema_version": "1.0",
        "summary": {
            "total_risks": len(risks),
            "high": sum(1 for r in risks if r["risk_level"] == "high"),
            "medium": sum(1 for r in risks if r["risk_level"] == "medium"),
            "low": sum(1 for r in risks if r["risk_level"] == "low"),
        },
        "risks": risks,
        "contradictions": [],
        "missing_clauses": [],
    }


class TestNormalizeCategory:
    """Test category normalization."""

    def test_direct_match(self):
        from scripts.batch_evaluate import normalize_category
        assert normalize_category("付款条件") == "付款条件"

    def test_synonym_match(self):
        from scripts.batch_evaluate import normalize_category
        assert normalize_category("回款条件") == "付款条件"

    def test_substring_match(self):
        from scripts.batch_evaluate import normalize_category
        result = normalize_category("数据安全与信息安全")
        assert result == "数据安全"

    def test_empty(self):
        from scripts.batch_evaluate import normalize_category
        assert normalize_category("") == "其他"

    def test_english_identifier(self):
        from scripts.batch_evaluate import normalize_category
        result = normalize_category("payment_terms_favor_service_provider")
        assert result == "付款条件"

    def test_quality_synonyms(self):
        from scripts.batch_evaluate import normalize_category
        assert normalize_category("质保条款") == "质量标准"
        assert normalize_category("质保服务") == "质量标准"


class TestInferCategoryFromTitle:
    """Test title-based category inference."""

    def test_payment_title(self):
        from scripts.batch_evaluate import infer_category_from_title
        assert infer_category_from_title("付款节点与验收脱钩") == "付款条件"

    def test_ip_title(self):
        from scripts.batch_evaluate import infer_category_from_title
        assert infer_category_from_title("知识产权归属不明确") == "知识产权"

    def test_data_security_title(self):
        from scripts.batch_evaluate import infer_category_from_title
        assert infer_category_from_title("数据泄露赔偿机制缺失") == "数据安全"

    def test_unknown_title(self):
        from scripts.batch_evaluate import infer_category_from_title
        assert infer_category_from_title("随机标题") == "其他"


class TestEvaluateRun:
    """Test single run evaluation."""

    def test_no_run_data(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()
        result = evaluate_run(sample_dir, "review_run_01", None, None, None, None, None)
        assert not result["success"]
        assert "无运行结果文件" in result["notes"]

    def test_failed_run(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()
        run_data = _make_review_run(success=False, error="Timeout")
        result = evaluate_run(sample_dir, "review_run_01", run_data, None, None, None, None)
        assert not result["success"]
        assert "Timeout" in result["notes"]

    def test_successful_run_with_matching(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected = _make_expected_risks(
            ["付款条件", "违约责任", "知识产权"],
            ["high", "high", "medium"],
        )
        raw = _make_raw_review(
            ["付款条件", "违约责任", "知识产权", "保密义务"],
            ["high", "high", "medium", "medium"],
        )
        run_data = _make_review_run(success=True)

        # Write raw file
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False))

        result = evaluate_run(sample_dir, "review_run_01", run_data, expected, None, None, None)

        assert result["success"]
        assert result["topic_recall"] == 1.0  # All 3 expected found
        assert result["topic_precision"] < 1.0  # Detected 4, only 3 expected
        assert result["high_risk_recall"] == 1.0  # Both high risks found
        assert len(result["unexpected_topics"]) > 0  # "保密义务" is unexpected

    def test_partial_match(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected = _make_expected_risks(["付款条件", "违约责任", "数据安全"])
        raw = _make_raw_review(["付款条件", "知识产权"])
        run_data = _make_review_run(success=True)
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False))

        result = evaluate_run(sample_dir, "review_run_01", run_data, expected, None, None, None)

        assert result["success"]
        assert result["topic_recall"] < 1.0
        assert "数据安全" in result["missing_expected_topics"] or "违约责任" in result["missing_expected_topics"]

    def test_contradiction_hit(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected_contradictions = {"total_contradictions": 2, "contradictions": []}
        run_data = _make_review_run(success=True, contradiction_count=1)

        result = evaluate_run(
            sample_dir, "review_run_01", run_data,
            None, None, expected_contradictions, None,
        )

        assert result["contradiction_expected"] == 2
        assert result["contradiction_detected"] == 1
        assert result["contradiction_hit"] is True

    def test_missing_clause_hit(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected_missing = {"total_missing": 3, "missing_clauses": []}
        run_data = _make_review_run(success=True, missing_clause_count=2)

        result = evaluate_run(
            sample_dir, "review_run_01", run_data,
            None, expected_missing, None, None,
        )

        assert result["missing_clause_expected"] == 3
        assert result["missing_clause_detected"] == 2
        assert result["missing_clause_hit"] is True

    def test_legal_basis_coverage(self, tmp_path):
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        # Raw with 3 risks, 2 have valid legal_basis
        raw = _make_raw_review(["付款条件", "违约责任", "知识产权"])
        raw["risks"][2]["legal_basis"] = "依据不足，基于法理分析"
        run_data = _make_review_run(success=True)
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

        result = evaluate_run(sample_dir, "review_run_01", run_data, None, None, None, None)

        assert result["legal_basis_coverage"] > 0.5
        assert result["legal_basis_coverage"] < 1.0

    def test_synonym_matching(self, tmp_path):
        """Verify synonym normalization works in evaluation."""
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected = _make_expected_risks(["回款条件", "质保条款"])
        raw = _make_raw_review(["付款条件", "质量标准"])
        run_data = _make_review_run(success=True)
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False))

        result = evaluate_run(sample_dir, "review_run_01", run_data, expected, None, None, None)

        # Both should match via synonyms
        assert result["topic_recall"] == 1.0


class TestEvaluateSample:
    """Test sample-level evaluation."""

    def test_sample_with_no_runs(self, tmp_path):
        from scripts.batch_evaluate import evaluate_sample
        sample_dir = _make_sample_dir(tmp_path, "contract-001")
        results = evaluate_sample(sample_dir)
        assert len(results) >= 3  # at least 3 run prefixes (dynamic detection may add more)
        assert all(not r["success"] for r in results)

    def test_sample_with_one_run(self, tmp_path):
        from scripts.batch_evaluate import evaluate_sample
        sample_dir = _make_sample_dir(
            tmp_path, "contract-001",
            expected_risks=_make_expected_risks(["付款条件"]),
            review_run=_make_review_run(success=True),
            raw_review=_make_raw_review(["付款条件"]),
        )
        results = evaluate_sample(sample_dir)
        assert len(results) >= 3
        assert results[0]["success"] is True
        # All remaining runs should fail (no run files)
        assert all(not r["success"] for r in results[1:])

    def test_output_files_created(self, tmp_path):
        from scripts.batch_evaluate import evaluate_sample, write_sample_evaluations
        sample_dir = _make_sample_dir(
            tmp_path, "contract-001",
            expected_risks=_make_expected_risks(["付款条件"]),
            review_run=_make_review_run(success=True),
            raw_review=_make_raw_review(["付款条件"]),
        )
        results = evaluate_sample(sample_dir)
        write_sample_evaluations(sample_dir, results)

        assert (sample_dir / "evaluation_review_run_01.json").exists()
        assert (sample_dir / "evaluation_review_run_02.json").exists()
        assert (sample_dir / "evaluation_review_run_03.json").exists()
        assert (sample_dir / "evaluation_summary.md").exists()


class TestBatchEvaluation:
    """Test batch-level evaluation."""

    def test_batch_with_mixed_samples(self, tmp_path):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import batch_evaluate as be_mod
        be_mod.BATCH_DIR = tmp_path

        # Sample 1: successful with matching
        _make_sample_dir(
            tmp_path, "contract-001",
            expected_risks=_make_expected_risks(["付款条件", "违约责任"]),
            review_run=_make_review_run(success=True),
            raw_review=_make_raw_review(["付款条件", "违约责任"]),
        )
        # Sample 2: failed
        _make_sample_dir(
            tmp_path, "contract-002",
            expected_risks=_make_expected_risks(["知识产权"]),
            review_run=_make_review_run(success=False),
        )
        # Sample 3: no run
        _make_sample_dir(
            tmp_path, "contract-003",
            expected_risks=_make_expected_risks(["保密义务"]),
        )

        all_evals = []
        for entry in sorted(tmp_path.iterdir()):
            if entry.is_dir() and entry.name.startswith("contract-"):
                all_evals.extend(be_mod.evaluate_sample(entry))

        batch_eval = be_mod.compute_batch_evaluation(all_evals)

        assert batch_eval["total_evaluations"] >= 9  # 3 samples * at least 3 runs each
        assert batch_eval["successful_evaluations"] == 1
        assert batch_eval["avg_topic_recall"] > 0

    def test_batch_json_output(self, tmp_path):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import batch_evaluate as be_mod
        be_mod.BATCH_DIR = tmp_path
        be_mod.SUMMARY_DIR = tmp_path / "_summary"

        _make_sample_dir(
            tmp_path, "contract-001",
            expected_risks=_make_expected_risks(["付款条件"]),
            review_run=_make_review_run(success=True),
            raw_review=_make_raw_review(["付款条件"]),
        )

        all_evals = []
        for entry in sorted(tmp_path.iterdir()):
            if entry.is_dir() and entry.name.startswith("contract-"):
                all_evals.extend(be_mod.evaluate_sample(entry))

        batch_eval = be_mod.compute_batch_evaluation(all_evals)
        be_mod.write_batch_evaluation(batch_eval, all_evals)

        assert (tmp_path / "_summary" / "evaluation_summary.json").exists()
        assert (tmp_path / "_summary" / "evaluation_summary.csv").exists()
        assert (tmp_path / "_summary" / "evaluation_report.md").exists()

        # Verify JSON content
        data = json.loads((tmp_path / "_summary" / "evaluation_summary.json").read_text(encoding="utf-8"))
        assert "avg_topic_recall" in data
        assert "risk_category_stats" in data

    def test_empty_batch(self, tmp_path):
        from scripts.batch_evaluate import compute_batch_evaluation
        batch_eval = compute_batch_evaluation([])
        assert batch_eval["total_evaluations"] == 0
        assert batch_eval["avg_overall_score"] == 0.0

    def test_idempotent(self, tmp_path):
        """Running twice should produce same results."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import batch_evaluate as be_mod
        be_mod.BATCH_DIR = tmp_path
        be_mod.SUMMARY_DIR = tmp_path / "_summary"

        _make_sample_dir(
            tmp_path, "contract-001",
            expected_risks=_make_expected_risks(["付款条件"]),
            review_run=_make_review_run(success=True),
            raw_review=_make_raw_review(["付款条件"]),
        )

        all_evals = []
        for entry in sorted(tmp_path.iterdir()):
            if entry.is_dir() and entry.name.startswith("contract-"):
                all_evals.extend(be_mod.evaluate_sample(entry))

        batch_eval = be_mod.compute_batch_evaluation(all_evals)
        be_mod.write_batch_evaluation(batch_eval, all_evals)
        data1 = json.loads((tmp_path / "_summary" / "evaluation_summary.json").read_text(encoding="utf-8"))

        # Run again
        all_evals2 = []
        for entry in sorted(tmp_path.iterdir()):
            if entry.is_dir() and entry.name.startswith("contract-"):
                all_evals2.extend(be_mod.evaluate_sample(entry))

        batch_eval2 = be_mod.compute_batch_evaluation(all_evals2)
        be_mod.write_batch_evaluation(batch_eval2, all_evals2)
        data2 = json.loads((tmp_path / "_summary" / "evaluation_summary.json").read_text(encoding="utf-8"))

        assert data1["avg_topic_recall"] == data2["avg_topic_recall"]


# ---------------------------------------------------------------------------
# Phase 3h — severity 归一化测试
# ---------------------------------------------------------------------------


class TestNormalizeSeverity:
    """Test severity normalization (CN/EN → EN standard)."""

    def test_english_high(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("high") == "high"

    def test_english_medium(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("medium") == "medium"

    def test_english_low(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("low") == "low"

    def test_english_case_insensitive(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("HIGH") == "high"
        assert normalize_severity("Medium") == "medium"
        assert normalize_severity("LOW") == "low"

    def test_chinese_high(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("高") == "high"

    def test_chinese_medium(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("中") == "medium"

    def test_chinese_low(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("低") == "low"

    def test_empty_string(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("") == ""

    def test_none_returns_empty(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity(None) == ""

    def test_unknown_returns_empty(self):
        from scripts.batch_evaluate import normalize_severity
        assert normalize_severity("critical") == ""
        assert normalize_severity("未知") == ""


class TestChineseSeverityInEvaluation:
    """Test that Chinese severity values are correctly handled in evaluation."""

    def test_chinese_high_risks_counted(self, tmp_path):
        """Chinese '高' should be counted as high risk in expected_high_risk_topics."""
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        # Expected risks with Chinese severity
        expected = {
            "contract_id": "test",
            "total_risks": 3,
            "risks": [
                {"risk_id": "R001", "risk_type": "付款条件", "severity": "高", "title": "付款风险"},
                {"risk_id": "R002", "risk_type": "违约责任", "severity": "中", "title": "违约风险"},
                {"risk_id": "R003", "risk_type": "知识产权", "severity": "低", "title": "知识产权风险"},
            ],
        }
        raw = _make_raw_review(
            ["付款条件", "违约责任", "知识产权"],
            ["high", "medium", "low"],
        )
        run_data = _make_review_run(success=True)
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False))

        result = evaluate_run(sample_dir, "review_run_01", run_data, expected, None, None, None)

        assert result["success"]
        assert "付款条件" in result["expected_high_risk_topics"]
        assert len(result["expected_high_risk_topics"]) == 1
        assert result["high_risk_recall"] == 1.0

    def test_mixed_severity_formats(self, tmp_path):
        """Mixed CN/EN severity in same file should all be recognized."""
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected = {
            "contract_id": "test",
            "total_risks": 3,
            "risks": [
                {"risk_id": "R001", "risk_type": "付款条件", "severity": "高", "title": "R1"},
                {"risk_id": "R002", "risk_type": "违约责任", "severity": "high", "title": "R2"},
                {"risk_id": "R003", "risk_type": "知识产权", "severity": "medium", "title": "R3"},
            ],
        }
        raw = _make_raw_review(
            ["付款条件", "违约责任", "知识产权"],
            ["high", "high", "medium"],
        )
        run_data = _make_review_run(success=True)
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False))

        result = evaluate_run(sample_dir, "review_run_01", run_data, expected, None, None, None)

        assert result["success"]
        assert len(result["expected_high_risk_topics"]) == 2
        assert result["high_risk_recall"] == 1.0

    def test_chinese_only_all_high(self, tmp_path):
        """All Chinese '高' severity risks should be detected as high."""
        from scripts.batch_evaluate import evaluate_run
        sample_dir = tmp_path / "test"
        sample_dir.mkdir()

        expected = {
            "contract_id": "test",
            "total_risks": 2,
            "risks": [
                {"risk_id": "R001", "risk_type": "合作范围", "severity": "高", "title": "采购范围定义模糊"},
                {"risk_id": "R002", "risk_type": "付款条件", "severity": "高", "title": "付款节点与验收脱钩"},
            ],
        }
        raw = _make_raw_review(
            ["合作范围", "付款条件"],
            ["high", "high"],
        )
        run_data = _make_review_run(success=True)
        (sample_dir / "review_run_01_raw.json").write_text(json.dumps(raw, ensure_ascii=False))

        result = evaluate_run(sample_dir, "review_run_01", run_data, expected, None, None, None)

        assert result["success"]
        assert len(result["expected_high_risk_topics"]) == 2
        assert result["high_risk_recall"] == 1.0
