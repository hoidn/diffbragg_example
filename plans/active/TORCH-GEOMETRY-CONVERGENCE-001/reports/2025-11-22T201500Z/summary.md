### Turn Summary
Authored Phase B4 extended diagnostic protocol to capture U_matrix/A*/gradient lifecycle tracing and definitively identify root cause among staleness/aliasing/gradient explosion hypotheses.
Instrumentation targets dbex/nanobrag_refinement.py (closure lifecycle logging) and stage_a_mapping_adam_debug.py (dual telemetry emission before/after optimizer.step).
Next: Ralph implements telemetry extensions, executes 1-step diagnostic, applies 4-test decision tree (U_checksum staleness, A*_checksum aliasing, gradient PRIMARY vs SYMPTOM, escalation), and synthesizes HIGH confidence verdict for Phase B5 fix implementation.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T201500Z/ (input.md Phase B4 protocol)
