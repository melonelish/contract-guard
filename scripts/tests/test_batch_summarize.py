"""Tests for batch_summarize.py — batch result aggregation tool."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def _make_run_data(success: bool, **overrides) -> dict:
    """Create a minimal review_run_01.json structure."""
    data = {
        "contract_id_dir": "contract-001-test",
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
        "rag_hit_count": 5,
        "rag_mode": "rag_enhanced",
        "schema_cleaned": False,
        "fallback_triggered": False,
        "error": None if success else "Review not completed: failed",
        "duration_sec": 60.0,
    }
    data.update(overrides)
    return data


def _setup_batch_dir(tmp_path: Path, samples: list[tuple[str, bool | None]]) -> Path:
    """Create a temporary batch directory with sample data.

    Args:
        tmp_path: pytest tmp_path fixture
        samples: list of (name, has_run) where has_run is True/False/None
                 True = successful run, False = failed run, None = no run
    """
    batch_dir = tmp_path / "batch-test"
    batch_dir.mkdir()

    for i, (name, has_run) in enumerate(samples):
        sample_dir = batch_dir / name
        sample_dir.mkdir()

        manifest = {
            "contract_id": f"contract-{i+1:03d}",
            "contract_type": "test",
            "title": f"Test Contract {i+1}",
            "difficulty": "medium",
        }
        (sample_dir / "manifest.json").write_text(json.dumps(manifest))

        if has_run is not None:
            run_data = _make_run_data(success=has_run)
            (sample_dir / "review_run_01.json").write_text(json.dumps(run_data))

    return batch_dir


def _run_summarize(batch_dir: Path) -> dict:
    """Run batch_summarize and return the summary JSON."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import batch_summarize

    summary_dir = batch_dir / "_summary"
    batch_summarize.BATCH_DIR = batch_dir
    batch_summarize.SUMMARY_DIR = summary_dir
    batch_summarize.main()

    return json.loads((summary_dir / "batch_summary.json").read_text())


class TestBatchSummarize:
    """Test batch_summarize.py with various scenarios."""

    def test_all_pending(self, tmp_path):
        """No runs yet — all samples should be pending."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", None),
            ("contract-002", None),
        ])
        summary = _run_summarize(batch_dir)

        assert summary["total_samples"] == 2
        assert summary["completed_samples"] == 0
        assert summary["failed_samples"] == 0
        assert summary["pending_samples"] == 2
        assert summary["total_runs"] == 0

    def test_mixed_results(self, tmp_path):
        """Mix of completed, failed, and pending samples."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", True),   # completed
            ("contract-002", False),  # failed
            ("contract-003", None),   # pending
        ])
        summary = _run_summarize(batch_dir)

        assert summary["total_samples"] == 3
        assert summary["completed_samples"] == 1
        assert summary["failed_samples"] == 1
        assert summary["pending_samples"] == 1

    def test_all_completed(self, tmp_path):
        """All samples completed successfully."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", True),
            ("contract-002", True),
            ("contract-003", True),
        ])
        summary = _run_summarize(batch_dir)

        assert summary["total_samples"] == 3
        assert summary["completed_samples"] == 3
        assert summary["failed_samples"] == 0
        assert summary["pending_samples"] == 0
        assert summary["token_stats"]["total_tokens"] == 9000

    def test_all_failed(self, tmp_path):
        """All samples failed."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", False),
            ("contract-002", False),
        ])
        summary = _run_summarize(batch_dir)

        assert summary["total_samples"] == 2
        assert summary["completed_samples"] == 0
        assert summary["failed_samples"] == 2
        assert summary["pending_samples"] == 0

    def test_token_stats(self, tmp_path):
        """Token stats should aggregate correctly."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", True),
            ("contract-002", True),
        ])
        summary = _run_summarize(batch_dir)

        assert summary["token_stats"]["total_prompt_tokens"] == 2000
        assert summary["token_stats"]["total_completion_tokens"] == 4000
        assert summary["token_stats"]["total_tokens"] == 6000
        assert summary["token_stats"]["avg_total_tokens"] == 3000

    def test_latency_stats(self, tmp_path):
        """Latency stats should aggregate correctly."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", True),
            ("contract-002", True),
        ])
        summary = _run_summarize(batch_dir)

        assert summary["latency_stats"]["avg_latency_ms"] == 50000
        assert summary["latency_stats"]["max_latency_ms"] == 50000
        assert summary["latency_stats"]["min_latency_ms"] == 50000

    def test_risk_stats(self, tmp_path):
        """Risk stats should aggregate correctly."""
        batch_dir = _setup_batch_dir(tmp_path, [
            ("contract-001", True),
            ("contract-002", True),
        ])
        summary = _run_summarize(batch_dir)

        assert summary["risk_stats"]["total_risks"] == 10
        assert summary["risk_stats"]["total_high"] == 4
        assert summary["risk_stats"]["total_contradictions"] == 2
        assert summary["risk_stats"]["total_missing_clauses"] == 6

    def test_output_files_exist(self, tmp_path):
        """All output files should be created."""
        batch_dir = _setup_batch_dir(tmp_path, [("contract-001", True)])
        _run_summarize(batch_dir)

        summary_dir = batch_dir / "_summary"
        assert (summary_dir / "batch_summary.json").exists()
        assert (summary_dir / "batch_summary.csv").exists()
        assert (summary_dir / "batch_report.md").exists()

    def test_csv_has_header(self, tmp_path):
        """CSV should have a header row."""
        batch_dir = _setup_batch_dir(tmp_path, [("contract-001", True)])
        _run_summarize(batch_dir)

        csv_path = batch_dir / "_summary" / "batch_summary.csv"
        lines = csv_path.read_text(encoding="utf-8-sig").strip().split("\n")
        assert len(lines) >= 2  # header + at least one data row

    def test_report_md_has_sections(self, tmp_path):
        """Markdown report should have expected sections."""
        batch_dir = _setup_batch_dir(tmp_path, [("contract-001", True)])
        _run_summarize(batch_dir)

        md_path = batch_dir / "_summary" / "batch_report.md"
        content = md_path.read_text(encoding="utf-8")
        assert "# 批跑汇总报告" in content
        assert "## 一、批次总览" in content
        assert "## 二、Token 消耗" in content
        assert "## 三、耗时统计" in content
        assert "## 四、风险统计" in content

    def test_empty_batch(self, tmp_path):
        """Empty batch directory should produce zero counts."""
        batch_dir = tmp_path / "empty-batch"
        batch_dir.mkdir()
        summary = _run_summarize(batch_dir)

        assert summary["total_samples"] == 0
        assert summary["completed_samples"] == 0
        assert summary["token_stats"]["total_tokens"] == 0

    def test_idempotent(self, tmp_path):
        """Running twice should produce same results."""
        batch_dir = _setup_batch_dir(tmp_path, [("contract-001", True)])

        summary1 = _run_summarize(batch_dir)
        summary2 = _run_summarize(batch_dir)

        assert summary1["total_samples"] == summary2["total_samples"]
        assert summary1["token_stats"]["total_tokens"] == summary2["token_stats"]["total_tokens"]
