# AI Module

This folder contains AI-related logic for the Sidecar widget.

## Files

- `draft_generator.py`

  - Generates agent-facing response drafts
  - Safe, deterministic interface
  - LLM calls can be added later

- `intent_classifier.py`
  - Lightweight intent detection
  - Replaceable with ML/LLM later

Design goal: **stable interfaces, swappable intelligence**
