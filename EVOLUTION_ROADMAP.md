# FutureHub Evolution Roadmap (Governed Build Path)

This file exists to prevent scope creep.

The system will evolve in strict, isolated phases.
No phase may modify prior working logic.

-------------------------------------

Phase 1 — Ticket Memory Logging (DONE)
- Persist ticket-level signals
- Store intent, confidence, draft outcome
- No aggregation
- No automation scaling

-------------------------------------

Phase 2 — Aggregation Engine (IN PROGRESS)
- On-demand weekly aggregation
- Intent frequency rollups
- Automation rate calculation
- No scheduler
- No auto-modification
- No model changes

-------------------------------------

Phase 3 — Audit & Automation Governance
- Track auto_send outcomes
- Track human edits
- Track reopen rate
- Introduce threshold gating logic
- Add audit_service.py
- Still no autonomous KB mutation

-------------------------------------

Phase 4 — Skills-Based SOP Injection
- Introduce /ai/skills/
- Intent-specific SOP rule injection
- No retraining
- No embeddings
- No autonomous modification

-------------------------------------

Phase 5 — Controlled Auto-Send Scaling
- Raise automation threshold
- Monitor via audit metrics
- Expand automation safely

-------------------------------------

Hard Rules:
- No embeddings system
- No vector search for analytics
- No background schedulers unless required
- No framework changes
- No architecture rewrites
- All evolution must be backward compatible
