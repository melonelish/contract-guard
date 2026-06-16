# ContractGuard — Intelligent Contract Risk Review System

> Project Codename: ContractGuard  
> Version: v1.0  
> Last Updated: 2026-06-15  
> Classification: Internal

---

## 1. Overview

ContractGuard is an enterprise-grade intelligent contract risk review system powered by LLMs and a multi-Agent collaborative architecture. Its core value proposition — "upload a contract PDF, auto-generate a review report" — compresses traditional manual clause-by-clause review (avg. 3 hours/contract) to 15 minutes, while boosting risk detection coverage from ~70% (human review) to ~95%.

### Core Capabilities

| Capability | Description |
|---|---|
| Deep Document Parsing | Supports PDF/Word/scanned documents; auto-extracts body text, tables, and signature regions |
| Intelligent Clause Analysis | Per-clause legal qualification, cross-referencing statutes and precedents, outputting risk levels |
| Cross-Reference Validation | Detects logical contradictions between different clauses within the same contract |
| Missing Clause Detection | Auto-identifies standard clauses that should be present but are absent |
| Structured Reporting | Auto-generates review reports with original text citations, legal references, and amendment suggestions |

### Delivery Models

- **SaaS Cloud Edition**: Targeting SMEs, pay-per-contract pricing
- **On-Premise Deployment**: Targeting large enterprises / law firms, Docker/K8s deployment
- **WeChat Mini Program**: Convenient upload and instant viewing

---

## 2. Document Navigation

```
ContractGuard/docs/
├── 00-README.md                    ← This document
├── 01-business/                    ← Business Case Layer (7 docs)
│   ├── business-plan.md
│   ├── market-analysis.md
│   ├── product-positioning.md
│   ├── business-model.md
│   ├── financial-projections.md
│   ├── competitive-analysis.md
│   └── pricing-and-cost-control.md  ★ New
├── 02-product/                     ← Product Definition Layer (5 docs)
│   ├── PRD.md
│   ├── user-personas.md
│   ├── user-journey-map.md
│   ├── prototype-design.md
│   └── dual-pane-comparison-and-diff.md  ★ New (Review-Edit-Print Loop)
├── 03-agent/                       ← AI Agent Layer ★Core★ (7 docs)
│   ├── AGENTS.md
│   ├── system-prompts.md
│   ├── agent-responsibilities.md
│   ├── agent-collaboration-protocol.md
│   ├── agent-evaluation.md
│   ├── tool-specifications.md
│   └── drafting-review-loop-and-annotation-bridge.md  ★ New
├── 04-technical/                   ← Technical Design Layer
│   ├── architecture-design.md
│   ├── technology-selection.md
│   ├── database-design.md
│   ├── API-design.md
│   ├── module-division.md
│   ├── deployment-architecture.md
│   ├── security-design.md
│   └── preview/                     ★ New
│       └── index.html               ← Product preview page (design system + interaction prototype)
├── 05-ai-coding/                   ← AI Coding Standards Layer
│   ├── coding-standards.md
│   ├── testing-standards.md
│   ├── code-review-standards.md
│   └── commit-standards.md
├── 06-project/                     ← Project Management Layer
│   ├── project-charter.md
│   ├── execution-plan.md
│   ├── WBS.md
│   ├── milestones.md
│   ├── risk-management.md
│   └── meeting-minutes.md
└── 07-testing/                     ← Testing & Acceptance Layer
    ├── test-plan.md
    ├── test-cases.md
    ├── acceptance-criteria.md
    ├── test-report.md
    └── performance-test-report.md
```

---

## 3. Reading Guide

| Role | Recommended Reading Order |
|---|---|
| Investors / Decision Makers | 00 → business-plan → financial-projections → pricing-and-cost-control |
| Product Managers | 00 → PRD → user-personas → dual-pane-comparison-and-diff |
| AI Engineers | 00 → AGENTS → agent-collaboration-protocol → drafting-review-loop-and-annotation-bridge → agent-evaluation |
| Backend Engineers | 00 → architecture-design → API-design → security-design |
| Frontend Engineers | 00 → dual-pane-comparison-and-diff → architecture-design |
| Project Managers | 00 → project-charter → execution-plan → risk-management |
| QA Engineers | 00 → test-plan → test-cases → acceptance-criteria |

---

## 4. Key Metrics

| Metric | Target |
|---|---|
| Review Turnaround | ≤ 15 min (baseline: 3 hours manual) |
| Risk Detection Accuracy | ≥ 90% (vs. licensed attorney review) |
| System Availability | 99.9% |
| API Response Latency | P95 ≤ 30s (including LLM inference) |
| Supported Formats | PDF / Word / Scanned / Image |
| Max File Size | 50MB |
| Concurrent Reviews | ≥ 100 contracts/sec |

---

## 5. Quick Start

### 5.1 Preview the Prototype

```bash
# Open the interactive prototype directly in your browser
open 04-technical/preview/index.html
```

The prototype demonstrates the core user experience: document viewer with inline risk marks, collapsible risk cards, dual-pane comparison, built-in editor (TipTap-based) with AI suggestion cards, and print-ready layout. No server required — open directly in any modern browser.

### 5.2 Run Full Stack (Development)

```bash
# 1. Clone and configure
cp .env.example .env       # Edit .env with your LLM API keys

# 2. Start all services
docker compose up -d       # PostgreSQL, Redis, ES, Milvus, MinIO, Vault

# 3. Install backend dependencies
pip install -e ".[dev]"    # See pyproject.toml for full list

# 4. Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# 5. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

---

*This documentation system follows the "Evolution of Documentation Systems in the AI-Driven Development Era" standard, suitable for enterprise-grade AI project delivery at scale.*
