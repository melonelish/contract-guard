"""Tests for batch_gap_analyze.py — 漏报归因分析工具。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestBuildExpectedManifest:
    """测试 expected_manifest.json 生成。"""

    def test_basic_manifest(self, tmp_path):
        """从已有文件正确提取结构化预期。"""
        from batch_gap_analyze import build_expected_manifest

        sample = tmp_path / "contract-001-test"
        sample.mkdir()

        # manifest.json
        (sample / "manifest.json").write_text(json.dumps({
            "contract_id": "contract-001",
            "contract_type": "采购合同",
            "title": "测试合同",
            "difficulty": "hard",
            "risk_count": 3,
            "missing_count": 1,
            "contradiction_count": 1,
        }), encoding="utf-8")

        # expected_risks.json
        (sample / "expected_risks.json").write_text(json.dumps({
            "contract_id": "contract-001",
            "risks": [
                {"risk_id": "R001", "risk_type": "付款条件", "severity": "high", "title": "付款风险",
                 "legal_basis": "《民法典》第六百二十八条"},
                {"risk_id": "R002", "risk_type": "验收标准", "severity": "medium", "title": "验收模糊"},
                {"risk_id": "R003", "risk_type": "data_security_weak", "severity": "high", "title": "数据安全不足"},
            ],
        }), encoding="utf-8")

        # expected_missing_clauses.json
        (sample / "expected_missing_clauses.json").write_text(json.dumps({
            "total_missing": 1,
            "missing_clauses": [
                {"clause_id": "M001", "clause_name": "知识产权条款", "importance": "high"},
            ],
        }), encoding="utf-8")

        # expected_contradictions.json
        (sample / "expected_contradictions.json").write_text(json.dumps({
            "total_contradictions": 1,
            "contradictions": [
                {"contradiction_id": "C001", "description": "测试矛盾描述"},
            ],
        }), encoding="utf-8")

        result = build_expected_manifest(sample)

        assert result is not None
        assert result["sample_id"] == "contract-001-test"
        assert result["contract_type"] == "采购合同"
        assert "付款条件" in result["expected_risk_topics"]
        assert "验收标准" in result["expected_risk_topics"]
        assert "数据安全" in result["expected_risk_topics"]  # 英文映射
        assert result["expected_contradictions"] == 1
        assert result["expected_missing_clauses"] == 1
        assert len(result["expected_legal_basis_topics"]) > 0

    def test_missing_manifest_returns_none(self, tmp_path):
        """无 manifest.json 时返回 None。"""
        from batch_gap_analyze import build_expected_manifest

        sample = tmp_path / "contract-empty"
        sample.mkdir()
        result = build_expected_manifest(sample)
        assert result is None

    def test_partial_data(self, tmp_path):
        """部分信息缺失时仍可运行。"""
        from batch_gap_analyze import build_expected_manifest

        sample = tmp_path / "contract-partial"
        sample.mkdir()
        (sample / "manifest.json").write_text(json.dumps({
            "contract_id": "contract-partial",
            "contract_type": "NDA",
            "title": "保密协议",
            "difficulty": "medium",
        }), encoding="utf-8")

        result = build_expected_manifest(sample)
        assert result is not None
        assert result["expected_risk_topics"] == []
        assert result["expected_contradictions"] == 0


class TestClassifyGapType:
    """测试漏报类型分类。"""

    def test_not_run(self):
        from batch_gap_analyze import classify_gap_type
        ev = {"success": False, "notes": "无运行结果文件"}
        assert classify_gap_type(ev, None) == "not_run"

    def test_execution_failure(self):
        from batch_gap_analyze import classify_gap_type
        ev = {"success": False, "notes": "审查失败: timeout"}
        run = {"error": "timeout waiting for response"}
        assert classify_gap_type(ev, run) == "timeout"

    def test_output_format(self):
        from batch_gap_analyze import classify_gap_type
        ev = {"success": False, "notes": "审查失败"}
        run = {"error": "JSON parse error in response"}
        assert classify_gap_type(ev, run) == "output_format"

    def test_no_gap(self):
        from batch_gap_analyze import classify_gap_type
        ev = {"success": True, "missing_expected_topics": []}
        assert classify_gap_type(ev, None) == "no_gap"

    def test_content_coverage_severe(self):
        from batch_gap_analyze import classify_gap_type
        ev = {
            "success": True,
            "topic_recall": 0.1,
            "high_risk_recall": 0.0,
            "missing_expected_topics": ["数据安全", "合规风险"],
        }
        assert classify_gap_type(ev, None) == "content_coverage_severe"


class TestComputeGapAnalysis:
    """测试归因分析计算。"""

    def test_basic_analysis(self):
        from batch_gap_analyze import compute_gap_analysis

        manifests = {
            "contract-001": {
                "sample_id": "contract-001",
                "contract_type": "采购合同",
                "difficulty": "hard",
                "expected_risk_topics": ["付款条件", "数据安全"],
                "expected_high_risk_topics": ["付款条件"],
                "expected_risk_count": 10,
            },
        }
        evaluations = [{
            "sample_id": "contract-001",
            "success": True,
            "topic_recall": 0.5,
            "high_risk_recall": 0.0,
            "overall_score": 0.3,
            "legal_basis_coverage": 0.8,
            "missing_expected_topics": ["数据安全"],
            "unexpected_topics": ["保密义务"],
            "detected_risk_topics": ["付款条件", "保密义务"],
            "contradiction_hit": False,
            "missing_clause_hit": False,
            "contradiction_expected": 1,
            "missing_clause_expected": 2,
        }]
        review_runs = []

        result = compute_gap_analysis(manifests, evaluations, review_runs)

        assert result["total_samples"] == 1
        assert result["analyzed_samples"] == 1
        assert len(result["sample_gaps"]) == 1
        assert result["sample_gaps"][0]["gap_type"] == "high_risk_miss"

    def test_not_run_samples_excluded_from_metrics(self):
        from batch_gap_analyze import compute_gap_analysis

        manifests = {
            "contract-001": {
                "sample_id": "contract-001",
                "expected_risk_topics": ["付款条件"],
                "expected_high_risk_topics": [],
                "expected_risk_count": 5,
            },
            "contract-002": {
                "sample_id": "contract-002",
                "expected_risk_topics": ["数据安全"],
                "expected_high_risk_topics": [],
                "expected_risk_count": 10,
            },
        }
        evaluations = [{
            "sample_id": "contract-001",
            "success": False,
            "notes": "无运行结果文件",
            "topic_recall": 0,
            "high_risk_recall": 0,
            "overall_score": 0,
            "legal_basis_coverage": 0,
            "missing_expected_topics": ["付款条件"],
            "unexpected_topics": [],
            "detected_risk_topics": [],
            "contradiction_hit": False,
            "missing_clause_hit": False,
        }]
        review_runs = []

        result = compute_gap_analysis(manifests, evaluations, review_runs)

        # contract-001 should be not_run, contract-002 not in evaluations at all
        assert result["not_run_samples"] >= 1
        high_low = result["high_expected_low_recall_samples"]
        # not_run samples should NOT be in this list
        assert "contract-001" not in high_low


class TestBuildFixPriorityTable:
    """测试修复优先级表生成。"""

    def test_basic_priority(self):
        from batch_gap_analyze import build_fix_priority_table

        analysis = {
            "gap_type_distribution": {
                "content_coverage_severe": 2,
                "execution_failure": 3,
            },
            "topic_miss_stats": [
                {"topic": "数据安全", "miss_count": 5, "is_high_risk_miss": True, "affected_samples": ["s1", "s2"]},
                {"topic": "合规风险", "miss_count": 2, "is_high_risk_miss": False, "affected_samples": ["s1"]},
            ],
            "high_expected_low_recall_samples": ["s1"],
            "good_coverage_weak_basis_samples": [],
        }

        table = build_fix_priority_table(analysis)

        assert len(table) >= 2
        assert table[0]["level"] == "P0"
        assert any("P1" in p["level"] for p in table)

    def test_empty_analysis(self):
        from batch_gap_analyze import build_fix_priority_table

        analysis = {
            "gap_type_distribution": {},
            "topic_miss_stats": [],
            "high_expected_low_recall_samples": [],
            "good_coverage_weak_basis_samples": [],
        }

        table = build_fix_priority_table(analysis)
        # Should not crash, may return empty
        assert isinstance(table, list)


class TestWriteGapOutputs:
    """测试输出文件生成。"""

    def test_json_csv_md_created(self, tmp_path):
        from batch_gap_analyze import write_gap_outputs, SUMMARY_DIR
        import batch_gap_analyze

        # Patch SUMMARY_DIR
        batch_gap_analyze.SUMMARY_DIR = tmp_path

        analysis = {
            "batch_name": "batch-01",
            "generated_at": "2026-01-01",
            "total_samples": 1,
            "analyzed_samples": 1,
            "not_run_samples": 0,
            "gap_type_distribution": {"minor_gap": 1},
            "sample_gaps": [{
                "sample_id": "s1",
                "contract_type": "test",
                "difficulty": "medium",
                "gap_type": "minor_gap",
                "topic_recall": 0.8,
                "high_risk_recall": 0.5,
                "overall_score": 0.6,
                "legal_basis_coverage": 0.9,
                "expected_risk_count": 5,
                "detected_risk_count": 4,
                "contradiction_hit": True,
                "missing_clause_hit": False,
                "missing_topics": ["数据安全"],
                "unexpected_topics": [],
            }],
            "topic_miss_stats": [
                {"topic": "数据安全", "miss_count": 1, "is_high_risk_miss": False, "affected_samples": ["s1"]},
            ],
            "high_expected_low_recall_samples": [],
            "good_coverage_weak_basis_samples": [],
            "topic_priority": [
                {"topic": "数据安全", "miss_count": 1, "is_high_risk_miss": False, "affected_samples": ["s1"], "priority_score": 1.0},
            ],
            "regression_test_candidates": ["s1"],
        }
        fix_table = [{"level": "P3", "description": "test", "items": ["item1"]}]

        write_gap_outputs(analysis, fix_table)

        assert (tmp_path / "gap_analysis.json").exists()
        assert (tmp_path / "gap_analysis.csv").exists()
        assert (tmp_path / "gap_analysis_report.md").exists()

        # Check JSON content
        data = json.loads((tmp_path / "gap_analysis.json").read_text(encoding="utf-8"))
        assert data["batch_name"] == "batch-01"
        assert len(data["fix_priority_table"]) == 1

        # Check CSV has header + 1 row
        csv_content = (tmp_path / "gap_analysis.csv").read_text(encoding="utf-8-sig")
        lines = csv_content.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row

        # Check MD has content
        md_content = (tmp_path / "gap_analysis_report.md").read_text(encoding="utf-8")
        assert "漏报归因分析报告" in md_content
        assert "修复优先级表" in md_content


class TestTopicMissStats:
    """测试高频漏报主题统计。"""

    def test_topic_miss_counting(self):
        from batch_gap_analyze import compute_gap_analysis

        manifests = {}
        for i in range(5):
            sid = f"contract-{i:03d}"
            manifests[sid] = {
                "sample_id": sid,
                "expected_risk_topics": ["数据安全", "付款条件"],
                "expected_high_risk_topics": ["数据安全"],
                "expected_risk_count": 10,
            }

        evaluations = []
        for i in range(5):
            evaluations.append({
                "sample_id": f"contract-{i:03d}",
                "success": True,
                "topic_recall": 0.5,
                "high_risk_recall": 0.0,
                "overall_score": 0.3,
                "legal_basis_coverage": 0.8,
                "missing_expected_topics": ["数据安全"],  # All miss 数据安全
                "unexpected_topics": [],
                "detected_risk_topics": ["付款条件"],
                "contradiction_hit": False,
                "missing_clause_hit": False,
            })

        result = compute_gap_analysis(manifests, evaluations, [])

        # 数据安全 should be missed 5 times
        data_security = [ts for ts in result["topic_miss_stats"] if ts["topic"] == "数据安全"]
        assert len(data_security) == 1
        assert data_security[0]["miss_count"] == 5
        assert data_security[0]["is_high_risk_miss"] is True
