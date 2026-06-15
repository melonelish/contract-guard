# Draft-Review Closed Loop & Annotation Bridge Design

> Version: v1.0 | Last Updated: 2026-06-15
> Classification: Core Design Decision

---

## 1. The Core Problem

**User challenge**: "If the contract is drafted by AI, the user changes only a tiny bit, then throws it back to AI for review—what can the review possibly find? If it finds nothing wrong, then the review is just an echo chamber for the draft. If it finds issues, then the draft itself was flawed. Isn't this circular reasoning?"

**This challenge is legitimate.** If drafting and reviewing share the same logic, the same model, and the same knowledge base, they will indeed form a dead loop of "reviewing one's own work."

---

## 2. Root Cause Analysis

```
AI Draft ────→ User Minor Edit ────→ AI Review ────→ "No issues!"
                                               │
                                    Isn't this circular reasoning?
```

| Step | Common System Approach | Problem |
|---|---|---|
| Draft | "Help the user write a contract" | Generates based on default assumptions without marking premises |
| Edit | User doesn't understand law, barely edits | Implicit assumptions from drafting remain unchanged |
| Review | Same model, same knowledge base reviews it | Same logic reviews the same output → zero incremental value |

**Root cause: Drafting and reviewing are not decoupled.** They use the same brain, query the same knowledge base, and operate on the same assumptions. This is no different from having the test-setter grade their own exam.

---

## 3. Solution: Four-Layer Isolation + Annotation Bridge

### 3.1 Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                                                            │
│   Drafting Agent (Drafter)          Review Agent (Reviewer) │
│   ══════════════════               ═══════════════════     │
│                                                            │
│   Layer 1: Model Isolation                                 │
│     MiMo 2.5                           DeepSeek V4-Flash  │
│     (Primary reasoning engine)         (Different reasoning blind spots) │
│                                                            │
│   Layer 2: Knowledge Base Isolation                       │
│     Contract template library           Law library + Case library │
│     "How are purchase contracts        "What lawsuits have been      │
│      usually written?"                  filed over this wording?"    │
│                                                            │
│   Layer 3: Posture Isolation                               │
│     System Prompt:                    System Prompt:      │
│     "You are a contract drafting      "You are the opposing counsel, │
│      expert. Help the user produce     find every attackable point"   │
│      a complete and valid contract."                         │
│                                                            │
│   Layer 4: Annotation Bridge                               │
│     Draft output annotated → Review attacks based on annotations │
│     "I wrote clause B based on        "Does assumption A hold in     │
│      assumption A"                     your specific scenario?"      │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### 3.2 Why All Four Layers Must Be Isolated

| Isolating Only | What Happens |
|---|---|
| Only change the model | Same knowledge base, same prompt — DeepSeek will still reach similar conclusions based on the same legal articles |
| Only change the knowledge base | Same model, same tone — MiMo 2.5 querying judgments will also automatically favor content it wrote itself |
| Only change System Prompt | Same model + same knowledge base, only changing prompt = left hand fighting right hand; LLM has confirmation bias |
| **All four layers isolated** | Different models × different knowledge bases × adversarial posture × annotation counterattack = truly independent review |

---

## 4. Annotation Bridge: The Most Critical Mechanism

### 4.1 What Are Annotations?

The Drafting Agent outputs not bare clauses, but **annotated clauses**:

```json
{
  "clause_text": "Liquidated damages at 30% of total contract value",
  "annotations": {
    "category": "Liability for Breach",
    
    // Assumptions made during drafting ← Core target of Review Agent's attacks
    "assumptions": [
      "Assumes buyer and seller have equal bargaining power",
      "Assumes total contract value within ¥500K",
      "Assumes no special industry regulatory requirements",
      "Assumes both parties have performance capability"
    ],
    
    // Clause alternatives (how this could be written) ← Basis for Review Agent's comparison
    "alternatives": {
      "strict_version": "Liquidated damages at 50% of total contract value, waiving the right to petition court for reduction",
      "standard_version": "Liquidated damages at 30% of total contract value",  
      "lenient_version": "Liquidated damages capped at 20% of actual losses"
    },
    
    // Risk notes from drafting ← Review Agent judges whether these risks have escalated
    "risk_notes": [
      "If counterparty is a large company, 30% may be deemed unconscionable by the court",
      "Special industries (e.g., construction) have specific liquidated damages rules requiring manual confirmation"
    ],
    
    // Matters the user must decide ← Review Agent will follow up
    "user_must_decide": [
      "What is the total contract value? (Current 30% is based on ≤¥500K assumption)",
      "What is the counterparty's company size? (Recommend lowering penalty ratio if unequal)",
      "Does your industry have special liquidated damages regulations?"
    ],
    
    // Drafting Agent's confidence score
    "confidence": 0.6  // Indicates many assumptions; suggests review should focus here
  }
}
```

### 4.2 How the Review Agent Uses Annotations

```
When the Review Agent receives annotated clauses, its workflow changes:

❌ Old approach:
   "Review this liquidated damages clause"
   → Query laws → Confirm 30% is reasonable → "No issues" → Done

✅ New approach (Annotation-based):
   Step 1: Read annotations
     "Drafted assuming equal parties, contract value ≤¥500K"
   
   Step 2: Reverse questioning
     "Do these 4 assumptions hold in your actual scenario?"
     → User answers: Contract ¥2M, counterparty is a listed company
   
   Step 3: Re-evaluate based on real information
     "¥2M contract ÷ 30% penalty = ¥600K
      Per (2023) Supreme People's Court Civil Final No.128,
      liquidated damages exceeding ¥400K for ¥2M-level contracts may be reduced
      → Risk escalated to 🔴 High"
   
   Step 4: Output review conclusion
     "The standard assumptions from drafting (¥500K/equal standing)
      do not hold in your actual scenario (¥2M/unequal standing).
      Recommend reducing liquidated damages from 30% to 20% (¥400K)"
```

### 4.3 Value Formula of the Annotation Bridge

```
Review Value = Normal Review Value + Draft Assumption Breach Value

         ┌─────────────────────────────────┐
         │ Without Annotation Bridge:       │
         │ Review Value = Legal compliance  │
         │                check (routine)   │
         │ Review Output = "No obvious legal│
         │                 issues"          │
         │ User Perception = "So reviewing  │
         │                    was pointless"│
         ├─────────────────────────────────┤
         │ With Annotation Bridge:          │
         │ Review Value = Legal compliance  │
         │              + Assumption check  │
         │              + Scenario fit      │
         │              + Variant comparison│
         │ Review Output = "3 drafting      │
         │                assumptions don't │
         │                hold in your      │
         │                scenario; adjust" │
         │ User Perception = "So many things│
         │                   I didn't think │
         │                   of; the review │
         │                   is truly useful│
         └─────────────────────────────────┘
```

---

## 5. Complete Product Flow

```
┌─────────────────────────────────────────────────┐
│                   User Entry                      │
│         ┌──────────┐    ┌──────────┐            │
│         │ Draft New │    │ Review    │            │
│         │ Contract  │    │ Existing  │            │
│         └────┬─────┘    │ Contract  │            │
│              │          └─────┬────┘            │
└──────────────┼─────────────────┼────────────────┘
               │                 │
               ▼                 │
┌──────────────────────────┐     │
│     Drafting Agent        │     │
│                           │     │
│ 1. User describes needs   │     │
│    "Purchase contract,    │     │
│     buyer, ¥2M"           │     │
│                           │     │
│ 2. AI generates complete  │     │
│    contract with          │     │
│    annotations            │     │
│                           │     │
│ 3. User views + edits     │     │
│    (even if only changing │     │
│     company name)         │     │
│                           │     │
│ 4. Submit for review      │     │
└───────────┬───────────────┘     │
            │                     │
            │     ┌───────────────┘
            │     │
            ▼     ▼
┌────────────────────────────────────┐
│     Pre-Review Guidance (key step) │
│                                    │
│ System auto-extracts all           │
│ "to-be-confirmed" items from       │
│ annotations, guiding user input:   │
│                                    │
│ □ Total contract value: [____]     │
│    (affects penalty ratio)         │
│ □ Counterparty size: ○Large ○Med ○Small │
│    (affects fairness assessment)   │
│ □ Industry: [____]                 │
│    (affects special rules)         │
│ ... (more dynamically generated    │
│      based on contract type)       │
│                                    │
└──────────────┬─────────────────────┘
               │
               ▼
┌────────────────────────────────────┐
│        Review Agent                 │
│                                    │
│ Independent review based on        │
│ four-layer isolation:              │
│ 1. Check legal compliance          │
│    (RAG → Law library)             │
│ 2. Check case law risks            │
│    (RAG → Case library)            │
│ 3. Attack assumptions in           │
│    annotations                     │
│    "Does assumption A hold in      │
│     your scenario?"                │
│ 4. Mark risks per clause +         │
│    generate revision suggestions   │
│                                    │
└──────────────┬─────────────────────┘
               │
               ▼
┌────────────────────────────────────┐
│        Review Report                │
│                                    │
│ 🔴 High Risk (3 items)             │
│    Penalty 30%→Recommend 20%       │
│    (based on your entered          │
│     contract value of ¥2M)         │
│                                    │
│ 🟡 Medium Risk (5 items)           │
│    Jurisdiction clause needs       │
│    adjustment (based on your       │
│    entered counterparty being      │
│    a listed company)               │
│                                    │
│ 📝 Draft Assumption Changes (4)    │
│    Of 4 standard assumptions,      │
│    2 do not hold in your scenario; │
│    re-evaluated                    │
│                                    │
│ 🔄 Recommend re-review after       │
│    revisions                       │
└────────────────────────────────────┘
               │
               ▼
      User revises contract based on report
               │
               ▼
         ┌──────────┐
         │ Re-review  │ ← Annotations now updated; review baseline changed
         └──────────┘
```

---

## 6. Interview Q&A Quick Reference

**Q1: If AI drafts a contract, can AI review its own work? Isn't that the left hand fighting the right?**

> "Our solution is four-layer isolation: different models, different knowledge bases, adversarial postures, and most critically, the Annotation Bridge. Every clause from the Drafting Agent is annotated with 'this clause was written based on what assumptions.' The Review Agent doesn't look at what the draft wrote—it checks whether those assumptions hold in the user's actual scenario. This is fundamentally two independent systems performing orthogonal verification on the same problem."

**Q2: What if the user doesn't understand law and can't fill out the pre-review guidance questions properly?**

> "The guidance questions are multiple-choice, not fill-in-the-blank. For example, 'counterparty company size' has options 'Large/Medium/Small,' each with helper text: 'Large: >1000 employees or listed company.' The user doesn't need to understand law—they only need to describe objective facts. This is also a core design principle: the AI does legal reasoning; the user only inputs facts."

**Q3: What if the user skips the guidance and goes straight to review?**

> "We retain the default assumptions from drafting but prominently label in the report: 'The following conclusions are based on default assumptions [assumption content] and have not been adjusted for your situation.' We also provide a 'Supplement information for re-review' button. This mechanism itself is also a layer of safety—when something is uncertain, clearly state it is uncertain."

**Q4: Isn't using two models too expensive?**

> "Drafting uses a cheap model (DeepSeek V4-Flash, ~¥0.3/use); review uses the primary model (MiMo 2.5, ~¥1.5/use). But compared to the economic losses users face from contract loopholes (average tens of thousands of yuan per disputed contract), this cost is negligible."

---

## 7. Design Decision Log

| Decision | Rationale |
|---|---|
| Why not share a model | Avoid the model's own confirmation bias |
| Why not share a knowledge base | Drafting queries templates (positive direction); reviewing queries case law (negative direction); responsibilities are naturally different |
| Why annotations must be structured JSON | Allows the Review Agent to programmatically consume annotations rather than relying on the LLM to "understand" the other party's intent |
| Why the guidance step is mandatory | If not enforced, 80% of users would skip it, significantly degrading review quality |
| Why review conclusions must indicate confidence | Legal review is never 100% correct; indicating confidence is a responsible posture |

---

*This document corresponds to the standard answer for the project FAQ question: "Doesn't AI drafting + AI reviewing create circular reasoning?"*
