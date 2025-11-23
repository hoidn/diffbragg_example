# Phase D1c Decision: All Stage C Helpers Wired + Regression Guards PASS

## Path A: Both Tests PASS → Phase D2 Ready

### Validation Results
- **Compilation:** PASS
- **Small detector test:** PASS (EXIT CODE: 0)
- **Full detector test:** PASS (EXIT CODE: 0)

### Implementation Summary
1. Extracted `_run_stage_c_lbfgs` helper (296 lines) at line 3194
2. Removed inline Stage C code (420 lines deleted via sed)
3. Wired all 3 helpers (_build_stage_c_params, _build_stage_c_lbfgs_closure, _run_stage_c_lbfgs)
4. Fixed dict key mismatches (target_t, loss_mask_t, sigma_readout_t, misset_deg_for_crystal)
5. Added missing lazy imports to helper2 (create_detector_config, create_crystal_config)
6. Defined _apply_baseline_detector_prior inline (18 lines)

### Net Code Reduction
- Extracted: 296 lines (helper3)
- Removed: 420 lines (inline code)
- **Net reduction: 124 lines**

### Conformance
- REFINE-007: Stage C gate preserved
- PHYSICS-LOSS-001/002: Variance-weighted loss + sigma_floor preserved
- PERF-WARM-013: Warm-cache branching preserved
- POLICY-001: Environment Freeze maintained (code-only extraction)

### Next Steps
Phase D2: Extract Stage B helpers (optional scope)
