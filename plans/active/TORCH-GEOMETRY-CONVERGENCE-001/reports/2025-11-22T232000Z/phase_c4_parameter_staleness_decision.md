# Phase C4 Decision — Parameter Staleness Audit

**Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
**Phase:** C4 (First Closure Parameter Staleness Audit)
**Date:** 2025-11-22T232000Z

---

## Verdict

**[ ] Path A — Audit found clear staleness bug, fix implemented and validated**
**[ ] Path B — Audit found multiple bugs OR fix didn't resolve issue**
**[X] Path C — Audit inconclusive, no clear staleness found**

**DIAGNOSIS:** **Path C — No parameter staleness found, but code path divergence suspected**

---

## Executive Summary

After systematic audit of all parameter initialization and closure usage in the diagnostic script (`stage_a_mapping_adam_debug.py`), **no parameter staleness bug was found**. All parameters (log_scale, q_params, cell deltas) are correctly captured in closure scope and used without stale copies.

**NEW FINDING:** The catastrophic chi²=8.8M in first closure is likely caused by a **code path divergence** between:
1. **Zero-point validation** (SUCCEEDS): Uses `create_crystal_config(..., crystal_overrides=None)` → direct MOSFLM A* injection
2. **First closure** (FAILS): Uses `create_crystal_config(..., crystal_overrides={"mosflm_a_star": ...})` → U/B_ideal round-trip

Even though all parameters are at zero values, the two code paths produce DIFFERENT results, suggesting numerical precision loss or handling differences in `create_crystal_config`.

---

## Evidence Summary

### Parameters Audited (All PASS)

| Parameter | Initialization | Closure Usage | Verdict |
|-----------|---------------|---------------|---------|
| log_scale | Line 732 `torch.tensor(...)` | Captured in closure scope, used at line 470 | ✓ SAME TENSOR |
| q_params | Line 767 `q_initial.clone().requires_grad_(...)` | Passed to `_stage_a_forward` at line 829 | ✓ SAME TENSOR |
| U_matrix | N/A (derived) | Computed fresh at line 434 from current q_params | ✓ CORRECT |
| A_star_new | N/A (derived) | Computed fresh at line 436 from current U @ B_ideal | ✓ CORRECT |
| crystal_overrides | N/A (derived) | Built fresh at lines 418-442 from current params | ✓ CORRECT |

### Code Path Divergence (SUSPECT)

**Zero-point path (chi²=990k, corr=1.0):**
```python
# Line 836 in stage_a_mapping_adam_debug.py
bragg_before_t, chi_sq_before_t = _forward_once(use_mapping_zero_geometry=True)
  → _stage_a_forward(..., use_mapping_zero_geometry=True)
  → create_crystal_config(crystal, Expt, crystal_overrides=None, misset_deg_override=None)
  → Uses MOSFLM A* directly from crystal.get_A()
```

**First closure path (chi²=8.8M BEFORE step):**
```python
# Line 924 in stage_a_mapping_adam_debug.py
bragg_t, chi_sq_t = _forward_once(use_mapping_zero_geometry=False)
  → _stage_a_forward(..., use_mapping_zero_geometry=False)
  → Derives U from q_params (line 434)
  → Reconstructs A* = U @ B_ideal (line 436)
  → Converts to numpy tuples (line 440-442)
  → create_crystal_config(crystal, Expt, crystal_overrides={"mosflm_a_star": ..., ...})
  → Uses reconstructed A* via crystal_overrides
```

**Hypothesis:** Even with zero-valued parameters (log_cell_X_delta=0, q_params=q_0), the round-trip conversion (MOSFLM A* → U, B_ideal → A* = U @ B_ideal → numpy tuples → crystal_overrides) introduces numerical error or triggers different handling in `create_crystal_config`.

---

## Why Phase C3 Misdiagnosed the Failure

Phase C3 correctly observed that chi² is catastrophic BEFORE optimizer.step(), but interpreted this as "forward model uses stale parameters."

**Actual cause:** The forward model uses **correct (non-stale) parameters**, but applies them via a DIFFERENT code path than zero-point validation. This code path difference produces wrong results even at zero parameters.

**Analogy:** Like Phase B5's bug where `crystal_overrides["A_star"]` was ignored (unsupported key), there may be a similar issue where the `crystal_overrides` path produces different results than the direct MOSFLM injection path.

---

## Recommended Next Actions

### Priority 1: Instrument Code Path Divergence (HIGH confidence ~85%)

**Objective:** Prove/disprove that `use_mapping_zero_geometry=False` with zero parameters produces different A* than `use_mapping_zero_geometry=True`.

**Implementation:**
1. Add logging to `_stage_a_forward` at lines 397-464:
   ```python
   if use_mapping_zero_geometry:
       crystal_config, _ = create_crystal_config(...)
       # NEW: Log A_star checksum from crystal_config
       A_star_direct = np.array(crystal_config.A_star_init, dtype=np.float64)
       print(f"[ZERO PATH] A* checksum: {A_star_direct.sum():.12f}")
   else:
       # After line 442:
       A_star_roundtrip = A_star_new.detach().cpu().numpy()
       print(f"[CLOSURE PATH] A* checksum: {A_star_roundtrip.sum():.12f}")
       print(f"[DIFF] A* abs diff: {np.abs(A_star_roundtrip - A_star_direct).max():.12e}")
   ```

2. Run 2-step Adam diagnostic with telemetry

3. Compare checksums — if they differ by > 1e-10, the round-trip is lossy

**Expected outcome:** Find that A* differs between the two paths, confirming code path divergence hypothesis.

**If checksums match:** Reject this hypothesis and escalate to deeper investigation (possibly in `create_crystal_config` or simulator internals).

---

### Priority 2: Audit create_crystal_config Handling (MEDIUM confidence ~60%)

**Objective:** Understand how `create_crystal_config` applies `crystal_overrides={"mosflm_a_star": ...}` vs `crystal_overrides=None`.

**Files to audit:**
- `dbex/nanobrag_bridge.py:create_crystal_config` (definition)
- Look for Phase B5-style bugs where certain override keys are ignored or applied incorrectly

**Expected outcome:** Find that `crystal_overrides` path has different precedence rules or normalization than direct MOSFLM path.

---

### Priority 3: Test LBFGS vs Adam (LOW confidence ~15%)

**Objective:** Rule out Adam-specific issues.

**Test:** Run Phase C3 diagnostic with `--use-lbfgs` flag.

**Rationale:** Production `run_nanobrag_refinement` uses LBFGS, so if LBFGS shows healthy chi², the bug is Adam-specific. If LBFGS also fails, the bug is in forward model code path (confirming Priority 1 hypothesis).

---

## Decision Tree Paths

### Path A: Audit found clear bug, fix implemented and validated
**Verdict:** REJECTED

**Evidence:** All parameter flow paths audited — no staleness bugs found.

### Path B: Audit found multiple bugs OR fix didn't resolve issue
**Verdict:** REJECTED

**Evidence:** Audit found zero bugs (not multiple bugs).

### Path C: Audit inconclusive, no clear staleness found
**Verdict:** **CONFIRMED**

**Evidence:**
- No parameter staleness in log_scale, q_params, or any derived values
- All parameters correctly captured and used in closure
- New hypothesis: Code path divergence between zero-point and first closure

**Confidence:** HIGH (~95%) that no staleness bug exists in parameter flow.

---

## Next Loop Specification

**Phase:** C5 (Code Path Divergence Diagnostic)

**Objective:** Instrument `_stage_a_forward` to log A* checksums for both `use_mapping_zero_geometry=True` and `use_mapping_zero_geometry=False` paths, then run 2-step Adam diagnostic to prove/disprove code path divergence hypothesis.

**Success criteria:**
- Identify exact magnitude of A* difference between the two paths
- Correlate A* difference to chi² difference (expect ~1e-6 A* error → ~8M chi² amplification)
- Determine whether bug is in U/B_ideal derivation OR in `create_crystal_config` handling

**If divergence confirmed:** Implement fix to make the two paths produce identical results at zero parameters (likely: bypass crystal_overrides when all deltas are zero, OR fix numerical precision in U/B_ideal round-trip).

**If divergence NOT confirmed:** Escalate to Priority 2 (audit `create_crystal_config` internals) or Priority 3 (test LBFGS).

---

## Artifacts

- `phase_c4_first_closure_audit.md` — Detailed parameter-by-parameter audit
- `phase_c4_parameter_staleness_decision.md` (this file) — Path C verdict and next actions

---

## Regression Guard Status

**NOT RUN** — Audit phase did not implement code changes.

**Rationale:** Per input.md §Pitfalls #1, only implement fixes after audit identifies clear bug. Since audit found NO staleness bug, no fix was implemented, so no regression guard is needed.

**Next loop:** If Priority 1 diagnostic confirms code path divergence, then implement fix and run regression guard `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`.
