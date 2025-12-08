### Turn Summary
Triaged Phase 8 blocker (KeyError 'shell_indices' at stage_b.py:343): Stage B wrapper unconditionally extracts shell-mode keys from param_values dict, but per-reflection mode creates different keys (asu_indices/log_modifiers/n_asu_unique).
Root cause identified with 95% confidence: mode isolation bug (wrapper doesn't branch on stage_b_mode before param extraction per dbex/nanobrag_refinement.py:2662-2673 pattern).
Next: Ralph implements mode-aware conditional extraction (~20 lines) + 4-step validation (compilation, Phase 6 regression, shell smoke, per-reflection E2E), estimated 1-1.5 hours single-loop delivery.
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-24T115000Z/ (blocker_analysis.md, input.md)
