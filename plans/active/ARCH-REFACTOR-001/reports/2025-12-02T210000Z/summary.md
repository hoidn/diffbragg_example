### Turn Summary
Created dbex/refinement/config.py (135 lines) extracting RefinementConfig from facade with backward-compat re-export; updated 13 import sites across 5 files (production + tests).
All 3/3 mapped tests PASSED; both new path (dbex.refinement.config) and old path (facade re-export) verified working; no behavioral regression.
Next: Phase D.2 — migrate CLI (dbex/refine_one.py) to RefinementEngine direct usage.
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T210000Z/ (pytest_phase_d1.log, import_verification.txt, metrics.txt)
