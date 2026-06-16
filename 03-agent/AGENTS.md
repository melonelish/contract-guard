# AGENTS.md — ContractGuard Multi-Agent System Design

> Version: v2.0 | Last Updated: 2026-06-15 | Classification: Core

---

## 1. Agent Architecture Overview

ContractGuard uses the **Orchestrator-Worker** pattern, consisting of 1 Supervisor Agent + 4 specialized Worker Agents.

```
                         ┌─────────────────┐
                         │   Supervisor     │
                         │   Agent          │
                         │                  │
                         │ · Receives docs  │
                         │ · Task dispatch  │
                         │ · Result merge   │
                         │ · Error handling │
                         └────┬───┬───┬────┘
              ┌───────────────┘   │   └───────────────┐
              ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │ Parser Agent  │   │Analyzer Agent │   │Report Agent   │
    │               │   │               │   │               │
    │ PDF→Structure │   │ Clause-level  │   │ Risk summary  │
    │ Table restore │   │ legal reasoning│   │ Rating        │
    │ OCR           │   │ Statute RAG   │   │ Suggestions   │
    │ Entity extract │   │ Precedent RAG │   │ Visualization │
    └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
            │                   │                   │
            └─────────┬─────────┴───────────────────┘
                      ▼
            ┌───────────────────┐
            │  Validator Agent  │
            │                   │
            │ · Hallucination   │
            │ · Format check    │
            │ · Citation verify │
            │ · Confidence audit│
            └───────────────────┘
                      │
                      ▼
            ┌───────────────────┐
            │    RAG Knowledge   │
            │    Bases           │
            │ ┌───────────────┐ │
            │ │ Statutes DB   │ │
            │ └───────────────┘ │
            │ ┌───────────────┐ │
            │ │ Precedents DB │ │
            │ └───────────────┘ │
            │ ┌───────────────┐ │
            │ │ Templates DB  │ │
            │ └───────────────┘ │
            │ ┌───────────────┐ │
            │ │ Review Rules  │ │
            │ └───────────────┘ │
            └───────────────────┘
```

---

## 2. Supervisor Agent

### 2.1 Responsibilities

The Supervisor is the **single entry point** for all contract review requests. It does not analyze contract content — it only coordinates tasks.

### 2.2 Core Flow

```
┌─────────────────────────────────────────────────────┐
│ Supervisor Agent Execution Flow                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Receive Request                                  │
│     ├── Verify user identity & permissions           │
│     ├── Validate file format & size                  │
│     └── Create review task (task_id)                 │
│                                                      │
│  2. Task Dispatch                                    │
│     ├── → Parser Agent: Parse document               │
│     ├── Wait for structured data from Parser         │
│     ├── → Analyzer Agent: Per-clause analysis        │
│     │   (Split contract into N clauses, N parallel)   │
│     ├── → Analyzer Agent: Cross-validation           │
│     ├── → Analyzer Agent: Missing clause detection   │
│     └── Collect all analysis results                 │
│                                                      │
│  3. Result Aggregation                               │
│     ├── → Report Agent: Generate review report       │
│     ├── → Validator Agent: Validate report           │
│     └── If validation fails → retry from analysis     │
│                                                      │
│  4. Return Result                                    │
│     ├── Store report in database                     │
│     ├── Update task status to completed              │
│     └── Return report ID + summary to frontend       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 2.3 System Prompt (excerpt)

```yaml
You are a task orchestrator (Supervisor) for a contract review system.

Your responsibilities:
1. Accept user-uploaded contract files
2. Coordinate Parser, Analyzer, Report, and Validator agents
3. Auto-retry on agent errors (max 3 attempts)
4. Do NOT analyze contract content — only orchestrate tasks

Strict rules:
- Every sub-agent call must include a task_id
- Validate output format integrity from each sub-agent
- Log all retries
- NEVER return results to user without Validator approval

Absolute "DO NOT"s:
- Do NOT make any legal judgments
- Do NOT skip the Validator
- Do NOT modify any sub-agent's output
```

### 2.4 Parallel Strategy

Clause analysis uses **per-clause parallelism**:

```python
# Pseudocode: parallel analysis strategy
clauses = parsed_result["clauses"]  # e.g., 50 clauses

# Each clause analyzed independently (no cross-dependency)
analysis_results = parallel_call(
    func=call_analyzer_agent,
    items=clauses,
    max_concurrency=10,
    timeout=60  # max 60s per clause
)

# After all clauses analyzed, run cross-validation (needs global context)
cross_validation = call_analyzer_agent(
    task="cross_validate",
    context={"all_clauses": clauses, "all_analyses": analysis_results}
)
```

---

## 3. Parser Agent

### 3.1 Responsibilities

Transforms unstructured contract files (PDF/Word/images) into structured JSON consumable by downstream agents.

### 3.2 I/O Specification

**Input:** Raw byte stream + file type identifier

**Output:** Structured JSON

```json
{
  "contract_id": "CT-2026-001",
  "meta": {
    "title": "Product Procurement Contract",
    "sign_date": "2026-06-01",
    "type": "Procurement",
    "page_count": 15
  },
  "parties": {
    "party_a": {
      "name": "Beijing XX Technology Co., Ltd.",
      "role": "Purchaser",
      "address": "Haidian District, Beijing...",
      "legal_rep": "Zhang San"
    },
    "party_b": {
      "name": "Shanghai YY Manufacturing Co., Ltd.",
      "role": "Supplier",
      "address": "Pudong New District, Shanghai...",
      "legal_rep": "Li Si"
    }
  },
  "clauses": [
    {
      "clause_id": "cl_001",
      "title": "Quality Standards",
      "category": "quality_standards",
      "page": 3,
      "position": {"line_start": 45, "line_end": 62},
      "full_text": "Products supplied shall comply with national standard GB/T...",
      "contains_table": false
    },
    {
      "clause_id": "cl_007",
      "title": "Payment Terms",
      "category": "payment_settlement",
      "page": 5,
      "position": {"line_start": 120, "line_end": 145},
      "full_text": "Payment schedule:\n| Milestone | % | Condition |\n...",
      "contains_table": true,
      "table_markdown": "| Milestone | % | Condition |\n|...|"
    }
  ],
  "signatures": [
    {
      "party": "Party A",
      "page": 14,
      "type": "seal",
      "ocr_text": "Beijing XX Technology Co., Ltd."
    }
  ]
}
```

### 3.3 Table Handling Strategy

```
Table region detected
    │
    ├── Simple table (no merged cells)
    │   → Pandoc to Markdown table
    │   → Preserve Markdown for LLM comprehension
    │
    └── Complex table (merged cells / page-break)
        → Layout analysis model to decompose cells
        → Reassemble into Markdown table
        → Flag: "This table contains merged cells; best-effort restoration"
```

---

## 4. Analyzer Agent ★ Core Agent

### 4.1 Responsibilities

The Analyzer Agent is ContractGuard's intelligence core. It consumes structured clauses from the Parser and performs **multi-dimensional legal reasoning** — the highest-AI-density component.

### 4.2 Analysis Task Types

| Task | Input | Output |
|---|---|---|
| **Single-clause analysis** | One clause text + category | Risk level + statute basis + revision suggestion |
| **Cross-validation** | Full text of all clauses | List of logical contradictions |
| **Missing clause detection** | Contract type + existing clause list | List of missing standard clauses |

### 4.3 Single-Clause Analysis Pipeline

```
Input: Single clause JSON
      │
      ▼
┌──────────────────────┐
│ Step 1: Classification│
│ What type of clause? │
│ Which legal domains? │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 2: Statute RAG   │
│ Which Civil Code art? │
│ Query knowledge base  │
│ Return statute text   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 3: Precedent RAG │
│ Similar case history? │
│ Court rulings?        │
│ Return case# + key pt │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 4: Risk Assess   │
│ Statute + precedent   │
│ → 🔴High/🟡Med/🟢Low │
│ Plain explanation     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Step 5: Suggestion    │
│ Specific clause edit  │
│ Confidence score      │
└──────────────────────┘
```

### 4.4 RAG Calling Convention

```python
# Standard RAG usage for Analyzer Agent

# Step 2: Statute retrieval
law_results = rag_search(
    query=clause_text,
    knowledge_base="laws",
    top_k=5,
    strategy="hybrid",     # Semantic + keyword
    filters={
        "status": "effective"  # Exclude repealed statutes
    }
)

# Step 3: Precedent retrieval
case_results = rag_search(
    query=legal_issue,
    knowledge_base="cases",
    top_k=3,
    strategy="hybrid",
    filters={
        "court_level": ["Supreme People's Court", "High People's Court"],
        "year_range": [2020, 2026]
    }
)
```

### 4.5 System Prompt (excerpt)

```yaml
You are a contract risk analysis expert (Analyzer Agent).

Your responsibility:
Analyze contract clauses for legal risks. Every conclusion MUST be backed by statute or precedent.

Analysis framework (execute in order):
1. Classify: What is this clause about?
2. Statute RAG: Look up relevant statutes
3. Precedent RAG: Look up similar cases
4. Risk assess: 🔴High / 🟡Medium / 🟢Low
5. Plain explanation: In non-legal language
6. Revision suggestion: Specific clause edit text
7. Confidence: How certain are you?

Hard rules:
❌ NEVER fabricate statute numbers
❌ NEVER give conclusions without statute backing
✅ If no statute found, mark "No direct statutory basis; based on legal reasoning"
✅ All citations must include source (law name + article number)

Output format: strict JSON Schema
{
  "clause_id": "cl_007",
  "risk_level": "high",
  "risk_category": "breach_penalty",
  "legal_analysis": "...",
  "law_references": [
    {"law": "Civil Code", "article": "Art. 585", "text": "...", "relevance": "direct"}
  ],
  "case_references": [
    {"case_id": "(2022) SPC Civil Final No.347", "relevance": "high", "key_point": "..."}
  ],
  "plain_explanation": "...",
  "suggested_revision": "...",
  "confidence": 0.85
}
```

---

## 5. Report Agent

### 5.1 Responsibilities

Aggregates the Analyzer's scattered analysis results into a single structured, readable review report.

### 5.2 Report Generation Pipeline

```
Input: All clause analyses + cross-validation + missing items
      │
      ▼
Step 1: Risk Aggregation
  ├── Count risks by level
  ├── Sort by severity
  └── Deduplicate (merge same statute references)
      │
      ▼
Step 2: Report Structuring
  ├── "Review Overview" section
  ├── "High Risk" section
  ├── "Medium Risk" section
  ├── "Low Risk Advisory" section
  ├── "Contradictions" section
  ├── "Missing Clauses" section
  └── "Statistics" data for charts
      │
      ▼
Step 3: Disclaimer Injection
  └── Auto-append legal disclaimer at report end
      │
      ▼
Output: Complete review report JSON
```

### 5.3 System Prompt (excerpt)

```yaml
You are a contract review report writer (Report Agent).

Your responsibility:
Organize scattered analysis into a complete, professional, readable review report.

Writing principles:
1. Overview first, then details
2. Severe first: Red > Yellow > Green — no reordering
3. Every item must include: original text + problem description + revision suggestion
4. Plain language: for business managers without legal background
5. Trustworthy citations: preserve all statute/precedent citations as-is

Required output sections:
- contract_info
- summary (total risks, distribution by level)
- high_risks (must include original text citations)
- medium_risks
- low_risks
- contradictions
- missing_clauses
- statistics (for chart rendering)
- disclaimer (fixed text)
```

---

## 6. Validator Agent

### 6.1 Responsibilities

The final gatekeeper. Performs multi-dimensional quality checks before the report reaches the user.

### 6.2 Validation Rules Matrix

| Dimension | Rule | On Failure |
|---|---|---|
| **Statute existence** | Every cited statute must exist in knowledge base | Remove citation, flag "pending verification" |
| **Original text fidelity** | Cited text vs. Parser output similarity > 0.95 | Replace with Parser's exact text |
| **Output format** | Must conform to predefined JSON Schema | Request Report Agent regeneration |
| **Risk count sanity** | Ordinary contract should not exceed 50 risk items | Manual flag, notify admin |
| **Missing items sanity** | Detection should not be empty (all contracts lack 2-3 standard clauses) | If empty → re-run detection |
| **Disclaimer** | Complete disclaimer text must be present | Auto-inject disclaimer |

### 6.3 System Prompt

```yaml
You are a review report quality validator (Validator Agent).

Your responsibility:
Final quality check before report delivery to the user.

Validation rules:
1. All statute citations must exist in knowledge base (no LLM hallucinations)
2. Original text citations must match contract source
3. Risk level distribution must be reasonable
4. Report format must be complete

What you do NOT do:
- Do NOT re-judge legal issues
- Do NOT modify analysis results

Your actions:
- Pass → mark as approved
- Fail → return specific failure reasons for Supervisor retry
```

---

## 7. Inter-Agent Communication Protocol

### 7.1 Communication Model

All agent communication routes through the **Supervisor**. Worker agents never communicate directly.

### 7.2 Message Format

```json
{
  "message_id": "msg-{uuid}",
  "task_id": "task-{uuid}",
  "from": "supervisor",
  "to": "analyzer",
  "type": "single_clause_analysis",
  "timestamp": "2026-06-15T10:30:00Z",
  "payload": {},
  "retry_count": 0
}
```

### 7.3 Error Handling

| Error Type | Handling Strategy |
|---|---|
| Agent timeout (60s no response) | Supervisor retry, max 3 attempts |
| Agent returns malformed output | Supervisor retry; after 3 failures, degrade output |
| 3 retries exhausted | Mark clause as "review failed", note in report |
| LLM service unavailable | Queue task; user sees "queued" status |

---

## 8. Drafter Agent (Draft-Review Loop)

> For the complete draft-review isolation design, see `drafting-review-loop-and-annotation-bridge.md`.

### 8.1 Responsibilities

The Drafter Agent is activated in the **contract drafting flow** (separate from the core review flow). It generates contract clauses with explicit annotation of drafting rationale, enabling the subsequent Review Agent to attack assumptions without circular reasoning.

### 8.2 Role in Architecture

```
User Request (e.g. "Draft a procurement contract")
      │
      ▼
┌──────────────────────┐
│   Supervisor Agent    │ ← Routes to Drafter (drafting) vs. Parser→Analyzer (reviewing)
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   Drafter Agent       │ ← Generates clauses with Annotation Bridge
│   · Clause generation │
│   · Assumption markup │
│   · Source attribution│
└──────┬───────────────┘
       │  Annotated draft
       ▼
┌──────────────────────┐
│   Review Agent Loop   │ ← Uses different model + KB; attacks assumptions, not content
└──────────────────────┘
```

### 8.3 Four-Layer Isolation from Review Agent

| Layer | Drafter | Reviewer | Why |
|---|---|---|---|
| **Model** | MiMo 2.5 | DeepSeek V4-Flash | Different reasoning blind spots |
| **Knowledge Base** | Contract template library | Statute library + Case library | Drafting uses "how contracts are written"; review uses "what laws say" |
| **Posture** | Constructive (build clauses) | Adversarial (attack assumptions) | Opposing incentives prevent echo chamber |
| **Annotation Bridge** | Marks every drafting assumption explicitly | Only challenges annotated assumptions | Review targets rationale, not wording |

### 8.4 Annotation JSON Schema

```json
{
  "clause_id": "draft_cl_003",
  "clause_text": "Liquidated damages shall be 20% of total contract value.",
  "annotations": [
    {
      "type": "assumption",
      "scope": "damages_ratio",
      "value": "20%",
      "rationale": "Based on Civil Code Art. 585 upper limit of 30%; 20% is industry median",
      "confidence": 0.7,
      "attack_surface": "If actual loss is lower, 20% may still be deemed excessive"
    }
  ]
}
```

### 8.5 Agent Count Clarification

| Flow | Agents Used |
|---|---|
| **Contract Review** (core) | Supervisor + Parser + Analyzer + Report + Validator = **5 Agents** |
| **Contract Drafting** (auxiliary) | Supervisor + Drafter + (then back to review flow) = **6th Agent** |

The Drafter is a **separate workflow entry point** and is not part of the standard review pipeline.
