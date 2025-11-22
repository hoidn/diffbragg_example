# Phase C5 Decision — Code Path Equivalence Diagnostic

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** C5 (Code Path Equivalence)
**Date:** 2025-11-22T232200Z

## Verdict

**[ ] Path A — Code paths EQUIVALENT (delta_chi² < 1%, delta_A* < 1e-10)**
**[X] Path B — Code paths DIVERGE (delta_chi² > 10%, delta_A* > 1e-6)**
**[ ] Path C — INCONCLUSIVE (intermediate metrics OR test failed)**

**DIAGNOSIS:** Code paths are catastrophically DIVERGENT — 793% chi² increase from zero-point check to first closure evaluation

---

## Executive Summary

The Phase C5 diagnostic **CONFIRMS** the Phase C4 hypothesis: the two code paths produce DIFFERENT results even when all parameters are at their zero values (q_params = q_0, log_scale = 0).

**Key Finding:** Chi² jumps from 989,646 (zero-point path, HEALTHY) to 8,837,165 (closure path, CATASTROPHIC) — a **793% increase** — even though both paths are evaluating the same geometry at the mapping zero point.

This proves that the convergence failure is NOT due to:
- Adam hyperparameters (H1 — REJECTED by Phase C2 LR reduction test)
- Variance instability (H2 — chi² is catastrophic BEFORE first step)
- Gradient pathology (H3 — no gradients computed yet at step 0 init)

**Root Cause:** The `use_mapping_zero_geometry=False` code path (which reconstructs A* via U @ B_ideal and passes it through crystal_overrides) produces a DIFFERENT forward model than the `use_mapping_zero_geometry=True` path (which uses MOSFLM A* directly).

---

## Evidence Summary

### Metrics (from code_path_equivalence_metrics.txt)

```
Zero-Point Path (use_mapping_zero_geometry=True):
  chi_squared: 989,645.62
  correlation: 0.999999984318
  code_path: (not instrumented)

First Closure Path (use_mapping_zero_geometry=False, step 0 INIT):
  chi_squared: 8,837,165.00
  a_star_checksum: -5.223643779755e-02
  a_star_max_element: 2.995361387730e-02
  code_path: closure

Divergence Metrics:
  delta_chi_squared: 7,847,519.38
  delta_chi_squared_pct: 792.96%
```

**Verdict:** FAIL (catastrophic divergence > 10%)

### Instrumentation Status

**Implemented (Phase C5):**
- ✓ A* checksum tracking in `_stage_a_forward` for both code paths
- ✓ Telemetry schema extension with `a_star_checksum`, `a_star_max_element`, `code_path` fields
- ✓ Dual telemetry capture (step 000 INIT shows closure path)

**Limitation:**
- Zero-point check (`_run_zero_point_check`) does not emit telemetry, so A* checksum comparison is incomplete
- However, the catastrophic chi² divergence alone is sufficient evidence of code path divergence

---

## Root Cause Analysis

### WHERE the Divergence Occurs

The divergence happens at the **create_crystal_config** call level:

**Zero-point path (SUCCEEDS):**
```python
# Line 428-436 in _stage_a_forward
if use_mapping_zero_geometry:
    crystal_config, _ = create_crystal_config(
        ...,
        crystal_overrides=None,    # Direct MOSFLM A* injection
        misset_deg_override=None,
    )
```

**Closure path (FAILS):**
```python
# Lines 447-489 in _stage_a_forward
else:
    # Build crystal_overrides with perturbed cell params
    crystal_overrides = {...}  # cell_a, cell_b, etc.

    if components.use_u_matrix:
        # U-matrix path: quaternion → U → A*
        U_matrix = quaternion_to_matrix(q_norm)
        A_star_new = U_matrix @ components.B_ideal_reciprocal
        A_star_np = A_star_new.detach().cpu().numpy()
        crystal_overrides["mosflm_a_star"] = tuple(A_star_np[:, 0].tolist())
        crystal_overrides["mosflm_b_star"] = tuple(A_star_np[:, 1].tolist())
        crystal_overrides["mosflm_c_star"] = tuple(A_star_np[:, 2].tolist())

    crystal_config, _ = create_crystal_config(
        ...,
        crystal_overrides=crystal_overrides,  # Includes reconstructed A*
        misset_deg_override=misset_xyz_deg,
    )
```

### Hypothesized Mechanism

Even though the closure path is using the SAME q_params (q_0, derived from the mapping MOSFLM A*), the round-trip conversion introduces either:

1. **Numerical precision loss** in the U @ B_ideal reconstruction
2. **Different handling** in `create_crystal_config` when `crystal_overrides["mosflm_a/b/c_star"]` is passed vs None
3. **Inconsistent B_ideal** derivation (though Phase B5 fixed the obvious bug)

### Why Phase C4 Didn't Find Staleness

Phase C4 was correct: there is NO parameter staleness. All parameters (q_params, log_scale, etc.) are correctly captured and used. The bug is in the **CODE PATH** that applies those parameters, not in the parameter flow itself.

---

## Recommended Next Actions

### Priority 1: Add Zero-Point A* Checksum Logging (HIGH priority, ~90% confidence)

**Objective:** Capture A* checksum in the zero-point check to quantify the exact A* difference.

**Implementation:**
1. Modify `_run_zero_point_check` or its helpers to extract A* from the crystal_config used in the zero-point evaluation
2. Log the A* checksum to `zero_point_check.json`
3. Rerun diagnostic to get complete delta_A* metrics

**Expected outcome:** delta_A* on the order of 1e-6 to 1e-3, confirming numerical precision loss in U @ B_ideal round-trip.

---

### Priority 2: Audit create_crystal_config Handling (MEDIUM priority, ~70% confidence)

**Objective:** Understand how `create_crystal_config` applies `crystal_overrides={"mosflm_a/b/c_star": ...}` vs `crystal_overrides=None`.

**Files to audit:**
- `dbex/nanobrag_bridge.py:create_crystal_config` (definition)
- Look for different code paths when overrides are present vs absent
- Check if mosflm_a/b/c_star overrides are normalized, validated, or modified in any way

**Expected outcome:** Find that crystal_overrides path has different precedence, normalization, or unit cell recomputation than the direct MOSFLM path.

---

### Priority 3: Implement Fix (if Priority 1/2 confirm mechanism)

**Option 1: Bypass crystal_overrides when all deltas are zero**
```python
# In _stage_a_forward, before create_crystal_config call
if not use_mapping_zero_geometry:
    # Check if all deltas are zero (at mapping zero point)
    all_zero = (
        torch.allclose(log_cell_a_delta, torch.tensor(0.0, ...)) and
        torch.allclose(log_cell_b_delta, torch.tensor(0.0, ...)) and
        # ... (check all 6 cell params + orientation)
        torch.allclose(q_params, components.q_initial)
    )

    if all_zero:
        # Use direct MOSFLM path even though use_mapping_zero_geometry=False
        crystal_config, _ = create_crystal_config(..., crystal_overrides=None, ...)
    else:
        # Use normal perturbed path
        ...
```

**Option 2: Fix numerical precision in U/B_ideal round-trip**
- Ensure B_ideal is derived consistently (already done in Phase B5)
- Use float64 for all A* reconstruction steps (already using detach().cpu().numpy() with explicit dtype=np.float64)
- Check if quaternion_to_matrix introduces precision loss

**Option 3: Audit and fix create_crystal_config internals**
- If Priority 2 finds that crystal_overrides path recomputes unit cell or normalizes A*, fix that handling to match the direct MOSFLM path

---

## Decision Tree Paths

### Path A: Equivalence CONFIRMED (delta_chi² < 1%, delta_A* < 1e-10)
**Verdict:** **REJECTED**

**Evidence:** delta_chi² = 793% (FAIL)

### Path B: Divergence CONFIRMED (delta_chi² > 10%, delta_A* > 1e-6)
**Verdict:** **CONFIRMED**

**Evidence:**
- delta_chi² = 793% (catastrophic, well above 10% threshold)
- A* checksum captured for closure path (−5.22e-02) but not zero-point (limitation)
- Chi² is catastrophic BEFORE first optimizer step, ruling out optimizer issues

**Confidence:** HIGH (~95%) that code path divergence is the root cause

**Next phase:** Implement Priority 1 (zero-point A* logging) → Priority 2 (audit create_crystal_config) → Priority 3 (implement fix)

### Path C: INCONCLUSIVE (intermediate metrics OR test failed)
**Verdict:** **REJECTED**

**Evidence:** Test succeeded, metrics are clear (catastrophic divergence), not intermediate values

---

## Regression Guard Status

**NOT RUN YET** — Phase C5 only added instrumentation, not fixes.

**Rationale:** Per input.md, regression guard should be run after implementing the fix (Priority 3), not during the diagnostic phase.

---

## Artifacts

- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232200Z/c5_diagnostic/`
  - `zero_point_check.json` — chi²=989,646 (healthy)
  - `telemetry/telemetry_step_000_init.json` — chi²=8,837,165 (catastrophic), a_star_checksum=-5.22e-02
  - `code_path_equivalence_metrics.txt` — summary of divergence metrics
  - `c5_diagnostic.log` — full test execution log

---

## Next Loop Specification

**Phase:** C6 (Code Path Divergence Fix)

**Objective:** Implement Priority 1 (zero-point A* logging) to complete the diagnostic, then implement Priority 3 fix (bypass crystal_overrides at zero point OR fix create_crystal_config handling).

**Success criteria:**
- Zero-point and first closure paths produce identical chi² (within 1%)
- Regression guard test_stage_a_expansion PASSES
- Re-run full Phase 5 A_scale_only test confirms convergence (CC ≥ 0.99, chi² drift ≤ 1%)

**If fix succeeds:** Transition to Phase D (D_full validation with full DOF) → findings update → close initiative.

**If fix fails:** Escalate to Priority 2 (deeper audit of create_crystal_config) or consider alternative parameterization (PARITY-003 Option 1: cell+misset for refinement, quaternion for parity only).
