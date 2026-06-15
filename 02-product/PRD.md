# Product Requirements Document (PRD)

> Version: v1.0 | Author: Product Team | Last Updated: 2026-06-15

---

## 1. Document Information

| Item | Content |
|---|---|
| Product Name | ContractGuard Intelligent Contract Review System |
| Product Version | v1.0 MVP |
| Document Status | Reviewed |
| Target Release | September 2026 (M3) |

---

## 2. Product Overview

### 2.1 One-Line Description

Users upload contract files, and the system automatically analyzes and outputs a structured risk review report, annotating each risk with legal basis, case references, and modification suggestions.

### 2.2 Core Scenarios

| Scenario # | Description | Priority |
|---|---|---|
| S01 | User uploads a PDF contract; system automatically completes review and generates report | P0 |
| S02 | User views review report, checking each risk detail and modification suggestion (contract on left + risk list on right) | P0 |
| S03 | Clicking a risk item in the review report auto-scrolls and pulse-highlights the corresponding clause in the left-side contract | P0 |
| S04 | User clicks "Enter Edit Mode" to directly modify the contract in the built-in editor | P0 |
| S05 | In the editor, AI review suggestions are embedded in the contract text as colored annotations, with one-click apply | P0 |
| S06 | After modifications, user submits "Re-Review"; the system incrementally reviews changed clauses | P0 |
| S07 | User downloads/prints the modified contract (supports three formats: Final, Tracked Changes, Comparison) | P1 |
| S08 | Editor provides undo/redo, font size adjustment, paragraph formatting, and other basic writing features | P1 |
| S09 | User uploads multiple contracts, managed on a unified list page | P1 |
| S10 | User quickly uploads image-based contracts via WeChat Mini Program | P2 |
| S11 | Enterprise admin configures custom risk rules | P2 |
| S12 | Enterprise admin views team member review history | P2 |
| S13 | Dual-pane comparison mode (Original vs. Modified side by side) | P2 |

---

## 3. Functional Requirements

### 3.1 Contract Upload Module (P0)

**FR-01: File Upload**
- Supported formats: PDF, DOCX, DOC, PNG, JPG
- Single file limit: 50MB
- Supports drag-and-drop and click-to-upload
- Progress bar during upload
- Automatically triggers review upon upload completion

**FR-02: File Preprocessing**
- Automatically detects whether the file is a contract (non-contracts are rejected)
- Automatic OCR recognition for PDF images
- Large files (>10MB) may be slower; estimated wait time is displayed

### 3.2 Contract Review Engine (P0 — Core Technology)

**FR-03: Document Structure Parsing**

See `03-agent/AGENTS.md` for detailed design.

| Parsed Content | Description |
|---|---|
| Contract title, signing date | Basic information extraction |
| Party A/B names, addresses | Signing entity information |
| Clause text | Full text extraction |
| Table content | Restored in Markdown Table format |
| Signature/seal areas | Position coordinates + OCR text |

**FR-04: Clause-Level Risk Analysis**

Four-dimensional analysis for each clause:

| Analysis Dimension | Output |
|---|---|
| Risk Level | 🔴 High / 🟡 Medium / 🟢 Low |
| Legal Basis | Linked original text of relevant laws (e.g., Civil Code) |
| Case Reference | Supreme Court / High Court rulings on similar disputes |
| Modification Suggestion | Specific clause rewriting suggestion text |

**FR-05: Cross-Validation**

- Detects logical contradictions between clauses within the same contract
- Example: Liquidated damages clause vs. General Provisions cap clause → if damages calculated by percentage may exceed the total cap, flag the contradiction

**FR-06: Missing Clause Detection**

Based on contract type (procurement, labor, technology development, etc.), automatically detect standard clauses that should exist but are missing:

| Contract Type | Required Clauses |
|---|---|
| Procurement Contract | Quality standards, acceptance method, payment terms, breach liability, confidentiality, dispute resolution |
| Labor Contract | Job description, work location, compensation, social insurance, termination conditions |
| Technology Development | IP ownership, acceptance criteria, maintenance support, confidentiality |
| Lease Contract | Rent, deposit, repair responsibility, sublease restrictions, early termination conditions |

### 3.3 Review Report Module (P0)

**FR-07: Report Content Structure**

```
Review Report
├── Contract Basic Info (title, parties, signing date, contract type)
├── Review Summary (total risks, high/medium/low counts)
├── Risk List (itemized display)
│   ├── Risk level + tag
│   ├── Original clause citation (precise to page/paragraph)
│   ├── Legal analysis (legal reasoning)
│   ├── Legal basis (original text citation)
│   ├── Similar cases (case number + key ruling points)
│   ├── Risk explanation (plain-language rewrite)
│   └── Modification suggestion (specific text)
├── Cross-Contradictions (inter-clause conflicts)
├── Missing Items (clauses that should exist but don't)
├── Risk Statistics Chart (pie chart / bar chart)
└── Disclaimer
```

**FR-08: Report Interaction Features**
- Click a risk item to navigate to the corresponding location in the original contract
- Support filtering by risk level
- Support filtering by risk type (breach liability / payment terms / IP, etc.)
- Support one-click copy of modification suggestion text

### 3.4 Contract Management Module (P1)

**FR-09: Contract List**
- Sorted by upload time descending
- Displays contract title, review status, risk statistics, upload time
- Supports search and filtering

### 3.5 Team Management Module (P2)

**FR-10: Member Management**
- Invite team members
- Set role permissions (Admin / Member / Read-only)
- View team review statistics

---

## 4. Non-Functional Requirements

### 4.1 Performance

| Metric | Target |
|---|---|
| API Response Time (P95) | ≤ 30s (including LLM inference) |
| File Upload Speed | ≥ 2MB/s |
| Concurrent Review Capacity | ≥ 100 TPS |
| First Screen Load Time | ≤ 2s |

### 4.2 Security

| Requirement | Description |
|---|---|
| Data transmission encryption | TLS 1.3 |
| Contract file encryption at rest | AES-256 |
| User data isolation | Multi-tenant logical isolation + database row-level security |
| Audit log | Full operation records (non-deletable) |
| Sensitive info masking | Auto-masking of ID numbers / phone numbers in contracts |

### 4.3 Availability

| Metric | Target |
|---|---|
| System Availability | 99.9% (monthly downtime < 43 minutes) |
| Concurrent Users | 10,000+ |
| Multi-platform Support | Web (Chrome/Safari/Edge) + WeChat Mini Program |

---

## 5. MVP Scope

### Phase 1 MVP (M1-M3)

| Feature | Priority | Status |
|---|---|---|
| Contract PDF/Word upload | P0 | ✅ Included |
| Document parsing (body text + tables) | P0 | ✅ Included |
| Clause risk analysis (red/yellow/green tiers) | P0 | ✅ Included |
| Legal citation | P0 | ✅ Included |
| Modification suggestions | P0 | ✅ Included |
| Review report display | P0 | ✅ Included |
| Report export to PDF | P1 | ✅ Included |
| User registration/login | P0 | ✅ Included |
| OCR scanned document support | P1 | ⚠️ Downgraded to Simplified Chinese OCR |
| Case citation | P0 | ✅ Included (public rulings from Judgments Online) |
| Cross-validation | P0 | ✅ Included |
| Missing clause detection | P1 | ✅ Included |
| WeChat Mini Program | P2 | ❌ Deferred to M5 |

### Phase 2 Enhancement (M4-M6)

- Multi-contract comparison review
- Custom risk rules
- Contract template library
- OCR enhancement (handwriting / seals)
- Performance optimization (P95 < 20s)

### Phase 3 Enterprise Edition (M7-M12)

- On-premises deployment
- SSO / Enterprise WeChat integration
- API open platform
- Industry-specific editions (Manufacturing / Tech / Trading)
