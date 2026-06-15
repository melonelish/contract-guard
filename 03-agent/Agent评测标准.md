# Agent Evaluation Standards

> Version: v1.0 | Last Updated: 2026-06-15

---

## 1. Evaluation System Overview

```
                  ┌─────────────────────────┐
                  │  End-to-End Evaluation   │
                  │  Review results vs        │
                  │  Lawyer-annotated GT      │
                  └───────────┬─────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐   ┌────────▼───────┐   ┌────────▼───────┐
│ Parser Eval   │   │ Analyzer Eval   │   │ Report Eval    │
│ Structuring   │   │ Risk Detection   │   │ Report Quality  │
│ Accuracy      │   │ Accuracy         │   │                 │
└───────────────┘   └────────────────┘   └───────────────┘
```

---

## 2. Evaluation Dataset

### 2.1 Data Sources

| Source | Quantity | Purpose |
|---|---|---|
| Public court judgment documents (contract disputes) | 500 | Training/Validation set |
| Law firm collaboration (anonymized) | 200 | Test set |
| Legal consultant manually constructed | 50 | Edge case testing |
| Real user uploads (authorized & anonymized) | Continuously growing | Ongoing evaluation |

### 2.2 Annotation Standards

Each contract is **independently annotated by 2 licensed lawyers**, including:
- Risk level per clause (High/Medium/Low)
- Associated legal article numbers
- Standard revision suggestions

Inter-Annotator Agreement (IAA): ≥ 85% (intersection taken as Ground Truth once threshold met)

---

## 3. Parser Agent Evaluation

| Metric | Definition | Target |
|---|---|---|
| Clause Segmentation Accuracy | Correctly identified clauses / Total actual clauses | ≥ 98% |
| Table Restoration Accuracy | Correctly restored tables / Total actual tables | ≥ 95% |
| Party Identification Rate | Contracts with correctly identified Party A/B names/roles | ≥ 99% |
| Page Location Accuracy | Clauses located within ±1 page | ≥ 95% |

---

## 4. Analyzer Agent Evaluation (Core)

### 4.1 Quantitative Metrics

| Metric | Definition | Target |
|---|---|---|
| **Risk Detection Precision** | TP / (TP + FP) | ≥ 88% |
| **Risk Detection Recall** | TP / (TP + FN) | ≥ 90% |
| **Risk Level Classification Accuracy** | Three-tier classification exact match rate | ≥ 85% |
| **Legal Citation Accuracy** | Cited legal provisions actually exist and are relevant | ≥ 98% |
| **Case Relevance** | Retrieved cases relevant to dispute focus | ≥ 80% |
| **Suggestion Usability** | Lawyer assessment: "usable as-is or with minor edits" | ≥ 70% |

### 4.2 Qualitative Evaluation

Every 50 test samples, extract 5 for in-depth review by legal consultants:

| Dimension | Score (1-5) | Target |
|---|---|---|
| Legal Analysis Depth | Not just surface-level | ≥ 4.0 |
| Logical Consistency | Analysis process and conclusions align | ≥ 4.5 |
| Business Practicality | Suggested revisions are actionable | ≥ 3.5 |

---

## 5. Hallucination Evaluation (Specialized)

### 5.1 Hallucination Categories

| Type | Definition | Example |
|---|---|---|
| **Type A: Fabricated Laws** | Citing non-existent legal articles | "Civil Code Article 999" (Civil Code goes to 1260, but Article 999's content may be fabricated) |
| **Type B: Text Tampering** | Altered original contract wording | Contract says "may" → AI writes "shall" |
| **Type C: Over-interpretation** | Inferred non-existent content from clauses | Contract never mentions "IP" → AI says "IP ownership issues exist" |
| **Type D: Confirmation Bias** | Misjudgment influenced by context | Previous clause was high risk → tend to judge next as high risk too |

### 5.2 Evaluation Method

```python
# Run hallucination check on every Analyzer output
def hallucination_check(analysis, clause_text, law_db):
    checks = []
    
    # Type A detection: Does the legal article number exist in the database
    for law_ref in analysis["law_references"]:
        if not law_db.exists(law_ref["law"], law_ref["article"]):
            checks.append({"type": "A", "detail": f"Legal article {law_ref['article']} does not exist"})
    
    # Type B detection: Similarity between quoted text and original contract text
    if analysis.get("original_quote"):
        similarity = semantic_similarity(analysis["original_quote"], clause_text)
        if similarity < 0.90:
            checks.append({"type": "B", "detail": f"Original text similarity only {similarity:.2f}"})
    
    return checks
```

### 5.3 Targets

| Hallucination Type | Acceptable Rate |
|---|---|
| Type A (Fabricated Laws) | **0%** — Zero tolerance |
| Type B (Text Tampering) | < 1% |
| Type C (Over-interpretation) | < 5% |
| Type D (Confirmation Bias) | < 3% |

---

## 6. End-to-End Evaluation

| Metric | Definition | Target |
|---|---|---|
| Overall F1 Score | 2 × Precision × Recall / (Precision + Recall) | ≥ 0.88 |
| High-Risk Detection Rate | Lawyer-annotated high-risk clauses also marked high-risk by AI | ≥ 95% |
| False Positive Rate | AI marked high-risk but lawyer marked low-risk | < 10% |
| Average Review Time | Time from upload to report return | < 15 minutes |
| Report Structure Completeness | Contracts with all six sections present | 100% |

---

## 7. Continuous Evaluation Mechanism

```
On every model update / Prompt change:
  
  1. Run 200-item fixed test set
  2. Auto-generate evaluation report (Precision/Recall/F1)
  3. Compare with previous version (Degradation Check)
     ├── If metrics drop > 2% → Block release, manual investigation
     └── If metrics rise/stable → Auto-pass
  4. Weekly: extract 20 real user data samples (anonymized) for supplementary evaluation
  5. Monthly: legal consultant spot-checks 10 samples, outputs qualitative review comments
```
