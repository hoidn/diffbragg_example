# ARCH-SIM-CONSTRUCTION-001 Phase C.4 Planning Summary

Ralph's diagnostic probe identified the smoking gun: oversampling mismatch (3-fold vs 1-fold auto-selection) causing 5,586× raw output discrepancy.
Planned explicit `oversample=3` fix for both simulate_forward_once and reconstruction cold path (3 files: config_factories.py signature, nanobrag_bridge.py, reconstruction.py).
Next: Ralph implements Phase C.4, validates with DB-AT-028/029 expecting bragg_after≈0.24 and tests PASS.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/ (galph_root_cause_final_oversampling.md, updated implementation.md, input.md)
