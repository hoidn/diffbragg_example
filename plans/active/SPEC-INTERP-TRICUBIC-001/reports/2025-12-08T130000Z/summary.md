### Turn Summary
Broke out of 20-loop maintenance mode by discovering that SPEC-INTERP-TRICUBIC-001 Phase B is actionable — specs were already updated (Phase A done) to mandate tricubic interpolation globally.
The key insight: cell gradient failures (ARCH-GRADIENT-FLOW-001) can be resolved via spec-side fix (tricubic) rather than waiting for upstream nanobrag_torch response.
Next: Ralph executes Phase B — change `config.py` default from `enable_hkl_interpolation=False` to `True`, update legacy test comments, run validation tests.
Artifacts: plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/
