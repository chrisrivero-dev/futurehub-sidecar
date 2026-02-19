# FutureHub Evolution Roadmap (Governed Build Path)

This file exists to prevent scope creep.

The system will evolve in strict, isolated phases.  
No phase may modify prior working logic.

---

## Phase 1 — Ticket Memory Logging (DONE)

- Persist ticket-level signals
- Store intent, confidence, draft outcome
- No aggregation
- No automation scaling

---

## Phase 2 — Aggregation Engine (IN PROGRESS)

- On-demand weekly aggregation
- Intent frequency rollups
- Automation rate calculation
- No scheduler
- No auto-modification
- No model changes

---

## Phase 3 — Audit & Automation Governance

- Track auto_send outcomes
- Track human edits
- Track reopen rate
- Introduce threshold gating logic
- Add `governance_service.py`
- Still no autonomous KB mutation

---

## Phase 4 — Skills-Based SOP Injection

- Introduce `/ai/skills/`
- Intent-specific SOP rule injection
- No retraining
- No embeddings
- No autonomous modification

---

## Phase 5 — Controlled Auto-Send Scaling

- Raise automation threshold
- Monitor via audit metrics
- Expand automation safely

---

## Hard Rules

- No embeddings system
- No vector search for analytics
- No background schedulers unless required
- No framework changes
- No architecture rewrites
- All evolution must be backward compatible

---

# 🧠 FutureHub System Interaction Architecture

## 🎯 Design Principle

Sidecar and FutureHause must remain functionally separate systems.

They may exchange intelligence signals — but they must never duplicate responsibilities.

---

## 🟦 Sidecar — Operational Intelligence Layer

### Scope

- Real-time draft generation
- Intent classification
- Confidence scoring
- Risk categorization
- Automation gating
- Ticket memory logging
- Weekly support analytics

### Data Source

- Internal support tickets only

### Outputs

- Draft responses
- Automation decisions
- Weekly operational summaries

### Sidecar answers:

“What happened inside support?”

### Sidecar does NOT:

- Scrape Reddit
- Monitor X
- Create KB articles automatically
- Modify knowledge autonomously
- Perform strategic forecasting

Sidecar is execution-layer intelligence.

---

## 🟩 FutureHause — Strategic Intelligence Layer

### Scope

- External signal ingestion (Reddit, X, forums)
- Trend detection
- Sentiment monitoring
- Risk clustering
- Knowledge gap detection
- KB article proposal
- Strategic recommendations

### Data Sources

- Reddit
- X
- Public chatter
- Competitor mentions
- Optional Sidecar weekly summary feed

### Outputs

- KB suggestions
- Product risk alerts
- Automation tuning recommendations
- Prompt adjustment suggestions

### FutureHause answers:

“What is happening outside support — and what should we prepare for?”

### FutureHause does NOT:

- Draft live tickets
- Auto-send messages
- Mutate Sidecar memory
- Override automation thresholds

FutureHause proposes.  
Humans decide.  
Sidecar executes.

---

## 🔁 Approved Interaction Flow

Tickets → Sidecar → JSONL Memory Log → Weekly Summary  
                               ↓  
                        (Optional Feed)  
                               ↓  
                       FutureHause Analysis  
                               ↓  
                  KB Proposal / Strategy Suggestion  
                               ↓  
                        Human Approval  
                               ↓  
                     KB Update / Prompt Update  
                               ↓  
                          Sidecar Uses  

---

## 🚫 Explicit Non-Overlap Rules

- Sidecar never scrapes external sources.
- FutureHause never injects drafts into live tickets.
- No autonomous KB mutation.
- No cross-system silent state mutation.
- All changes must be human-reviewed.

---

## 🧩 Long-Term Role Clarity

Sidecar = Operational Brain  
FutureHause = Strategic Brain  

Execution and strategy remain decoupled.

---

This document exists to prevent architectural drift.
