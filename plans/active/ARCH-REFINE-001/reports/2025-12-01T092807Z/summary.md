### Turn Summary
Removed inline Stage A/B/C branch and made RefinementEngine the single execution path for all stage combinations (A, A→B, A→C, A→B→C).
Stage B smoke test passed with telemetry intact; Stage C test reveals ~2.6% chi-squared offset between stages (REFINE-FLOW-001-EXT) plus zero Stage A improvement on small detector, requiring follow-up investigation.
Next: commit refactoring (-1071 lines), document Stage C blocker in findings.md, and resume in next loop once Stage C parameter reconstruction is debugged.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/ (pytest_stage_bc_small.log, collect_stage_bc_small.log)
