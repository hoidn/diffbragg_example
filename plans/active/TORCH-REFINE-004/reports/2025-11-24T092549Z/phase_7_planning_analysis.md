# Phase 7 Planning Analysis — Per-Reflection Mode Integration into Stage B Loop

**Initiative:** TORCH-REFINE-004 (Stage B Per-Reflection Mode Migration)

**Date:** 2025-11-24T092549Z

**Mode:** Planning (supervisor loop, no code changes)

**Objective:** Integrate ASU-based per-reflection modifiers into Stage B optimization loop, replacing shell-based aggregation when enabled via `stage_b_mode="per_reflection"`.

## Executive Summary

**Phase 6 Status:** ✓ COMPLETE (commit 19dd43e + aebdddd)
- 3 helper functions implemented and tested: `compute_hkl_asu_map`, `initialize_asu_modifiers`, `apply_asu_modifiers`
- 5 unit tests PASSED (runtime 1.06s): P1/P432 ASU mapping, halo handling, Friedel pairs, modifier application
- RefinementConfig extended with 3 ASU mode fields: `stage_b_optimizer_gate`, `stage_b_adam_lr`, `stage_b_modifier_clamp`
- Engine telemetry schema fix COMPLETE (commit aebdddd): `telemetry_version` field added, regression guard PASSED

**Phase 7 Scope:** Integrate ASU modifiers into existing Stage B loop (`_build_stage_b_params`, `compute_loss_stage_b` closure). Tasks:
1. **7.1** — Compute ASU map and initialize ASU modifiers in `_build_stage_b_params` (parallel to shell mode path)
2. **7.2** — Dynamic optimizer selection (n_asu < 10K → LBFGS, ≥10K → Adam per spec:107)
3. **7.3** — Replace shell modifier application with `apply_asu_modifiers` call in `compute_loss_stage_b` closure
4. **7.4** — Add ASU telemetry fields (`n_asu_unique`, `optimizer_type`, `asu_modifier_stats`)
5. **7.5** — Integration smoke test: `test_stage_b_per_reflection_smoke` (validates ASU path, gradient flow, convergence)

**Estimated Effort:** 1 loop (~2-3 hours)

**Confidence:** HIGH (~85%) — Integration points clear, helpers already tested, no new physics/algorithms.

---

## 1. Integration Point Analysis

### Current Shell Mode Flow (dbex/nanobrag_refinement.py)

**Setup (`_build_stage_b_params`, lines 2383-2546):**
1. Compute shell lookup (line 2433-2435): `compute_hkl_shell_lookup`
2. Initialize shell modifiers (lines 2437-2443): `torch.zeros(n_shells)` with softplus init
3. Setup optimizer (lines 2447-2455): LBFGS only
4. Build closure (lines 2570-2906): applies shell modifiers via `torch.where` loop (lines 2712-2722)

**Per-Reflection Mode Integration (Phase 7):**
1. Branch on `config.stage_b_mode` early in `_build_stage_b_params`
2. If `mode == "per_reflection"`:
   - Call `compute_hkl_asu_map` (Phase 6 helper) → `asu_indices` tensor + `n_asu_unique`
   - Call `initialize_asu_modifiers` (Phase 6 helper) → `log_modifiers` parameter tensor
   - Dynamic optimizer selection based on `n_asu_unique` vs `config.stage_b_optimizer_gate`
   - Replace shell modifier application in closure with `apply_asu_modifiers` (Phase 6 helper)
3. Otherwise (mode == "shell"): existing shell mode path unchanged

### Modified Dataflow

**Phase 7 Changes (new per-reflection branch):**
```
_build_stage_b_params:
  IF config.stage_b_mode == "per_reflection":
    asu_indices, n_asu = compute_hkl_asu_map(hkl_grid, crystal_symmetry, halo_mask)  # Phase 6
    log_modifiers = initialize_asu_modifiers(n_asu, device, dtype, clamp_range)      # Phase 6
    params = [log_modifiers]
    IF n_asu >= config.stage_b_optimizer_gate (default 10000):
      optimizer = torch.optim.Adam(params, lr=config.stage_b_adam_lr)  # Phase 7.2
    ELSE:
      optimizer = torch.optim.LBFGS(params, ...)  # Existing LBFGS path
  ELSE:  # "shell" mode
    shell_indices, shell_edges = compute_hkl_shell_lookup(...)  # Existing
    shell_modifier_raw = torch.zeros(n_shells, ...)
    params = [shell_modifier_raw]
    optimizer = torch.optim.LBFGS(params, ...)  # Existing

compute_loss_stage_b closure:
  IF config.stage_b_mode == "per_reflection":
    hkl_grid_modified = apply_asu_modifiers(hkl_grid, asu_indices, log_modifiers, clamp_range)  # Phase 6
  ELSE:
    hkl_grid_modified = hkl_grid.clone()
    FOR shell_idx IN range(n_shells):
      mask = (shell_indices == shell_idx)
      hkl_grid_modified = torch.where(mask, hkl_grid * shell_modifiers[shell_idx], hkl_grid_modified)  # Existing
  # Rest of closure unchanged (forward simulation, loss computation)
```

---

## 2. Task Breakdown

### 7.1 — ASU Mode Initialization in `_build_stage_b_params`

**Location:** `dbex/nanobrag_refinement.py::_build_stage_b_params` (lines 2383-2546)

**Implementation:**
1. Add mode branch at line ~2432 (before shell lookup):
   ```python
   if config.stage_b_mode == "per_reflection":
       # Compute ASU map using Phase 6 helper
       halo_mask = hkl_metadata.get("halo_mask")  # 3D boolean array
       asu_indices, n_asu_unique = compute_hkl_asu_map(
           hkl_grid.cpu().numpy(),
           crystal.crystal_symmetry,  # From MTZ
           halo_mask=halo_mask
       )
       asu_indices_t = torch.from_numpy(asu_indices).to(device=device, dtype=torch.long)

       # Initialize ASU modifiers using Phase 6 helper
       log_modifiers = initialize_asu_modifiers(
           n_asu=n_asu_unique,
           device=stage_b_param_device,  # Respect CPU fallback logic (line 2440)
           dtype=dtype,
           clamp_range=config.stage_b_modifier_clamp  # (-3.0, 3.0) default
       )
       stage_b_params = [log_modifiers]

       # Store ASU metadata in param_values for closure
       param_values.update({
           "asu_indices": asu_indices_t,
           "n_asu_unique": n_asu_unique,
           "log_modifiers": log_modifiers,
       })
   else:  # "shell" mode
       # Existing shell mode path (lines 2433-2443)
       shell_indices, shell_edges = compute_hkl_shell_lookup(...)
       shell_modifier_raw = torch.zeros(...)
       stage_b_params = [shell_modifier_raw]
       param_values.update({
           "shell_indices": shell_indices,
           "shell_edges": shell_edges,
           "shell_modifier_raw": shell_modifier_raw,
       })
   ```

**Outputs:**
- `param_values["asu_indices"]`: Tensor mapping HKL voxels to ASU indices
- `param_values["n_asu_unique"]`: Integer count of unique ASU reflections
- `param_values["log_modifiers"]`: Trainable nn.Parameter for ASU modifiers

**Lines Added:** ~35-40

---

### 7.2 — Dynamic Optimizer Selection

**Location:** `dbex/nanobrag_refinement.py::_build_stage_b_params` (lines 2447-2455)

**Implementation:**
```python
if config.stage_b_mode == "per_reflection":
    n_asu = param_values["n_asu_unique"]
    if n_asu >= config.stage_b_optimizer_gate:  # Default 10000
        # Adam for large parameter counts
        stage_b_optimizer = torch.optim.Adam(
            stage_b_params,
            lr=config.stage_b_adam_lr  # Default 1e-3
        )
        optimizer_type = "adam"
    else:
        # LBFGS for small parameter counts (spec default per spec-db-workflow.md:107)
        stage_b_optimizer = torch.optim.LBFGS(
            stage_b_params,
            history_size=config.history_size,
            max_iter=config.max_iter,
            tolerance_grad=config.tolerance_grad,
            tolerance_change=config.tolerance_change,
            line_search_fn='strong_wolfe'
        )
        optimizer_type = "lbfgs"
    param_values["optimizer_type"] = optimizer_type
else:  # "shell" mode
    # Existing LBFGS-only path (lines 2447-2455)
    stage_b_optimizer = torch.optim.LBFGS(stage_b_params, ...)
    param_values["optimizer_type"] = "lbfgs"
```

**Rationale:**
- Spec-db-workflow.md:107 permits LBFGS or Adam for Stage B
- n_asu for P1 fixture ~35K → Adam required (LBFGS memory scales with parameter count)
- 10K gate based on typical LBFGS history size (10-20) × HKL grid size

**Lines Added:** ~15-20

---

### 7.3 — ASU Modifier Application in Closure

**Location:** `dbex/nanobrag_refinement.py::_build_stage_b_lbfgs_closure` (lines 2712-2722, inside `compute_loss_stage_b`)

**Implementation:**
```python
def compute_loss_stage_b(work_item_ids, is_full=False, force_panel_eval=False):
    # ... (lines 2637-2710: device setup, eval branch, hkl_grid_local)

    if config.stage_b_mode == "per_reflection":
        # ASU mode: apply per-reflection modifiers using Phase 6 helper
        asu_indices_local = asu_indices if eval_device == device else asu_indices.to(device=eval_device)
        log_modifiers_local = log_modifiers if eval_device == device else log_modifiers.to(device=eval_device)
        hkl_grid_modified = apply_asu_modifiers(
            hkl_grid=hkl_grid_local,
            asu_indices=asu_indices_local,
            log_modifiers=log_modifiers_local,
            clamp_range=config.stage_b_modifier_clamp  # (-3.0, 3.0) default
        )
    else:  # "shell" mode
        # Existing shell modifier path (lines 2710-2722)
        shell_modifiers = F.softplus(shell_modifier_raw) * 2.0
        shell_indices_local = shell_indices if eval_device == device else shell_indices.to(device=eval_device)
        hkl_grid_modified = hkl_grid_local.clone()
        for shell_idx in range(config.stage_b_n_shells):
            mask = (shell_indices_local == shell_idx)
            modifier_value = shell_modifiers[shell_idx]
            if modifier_value.device != eval_device:
                modifier_value = modifier_value.to(device=eval_device)
            hkl_grid_modified = torch.where(mask, hkl_grid_local * modifier_value, hkl_grid_modified)

    # ... (rest of closure unchanged: warm cache setup, simulator run, loss computation)
```

**Lines Changed:** ~10-15 (replace shell loop with single `apply_asu_modifiers` call)

---

### 7.4 — ASU Telemetry Fields

**Location:** `dbex/nanobrag_refinement.py::_run_stage_b_lbfgs` (lines 2909-3107, telemetry dict construction)

**Implementation:**
Add ASU-specific fields to telemetry dict (after line ~3080):
```python
if config.stage_b_mode == "per_reflection":
    telemetry_b.update({
        "n_asu_unique": int(param_values["n_asu_unique"]),
        "optimizer_type": param_values["optimizer_type"],  # "adam" or "lbfgs"
        "asu_modifier_stats": {
            "min": float(torch.exp(torch.clamp(param_values["log_modifiers"].min(), *config.stage_b_modifier_clamp)).item()),
            "max": float(torch.exp(torch.clamp(param_values["log_modifiers"].max(), *config.stage_b_modifier_clamp)).item()),
            "mean": float(torch.exp(torch.clamp(param_values["log_modifiers"].mean(), *config.stage_b_modifier_clamp)).item()),
            "std": float(torch.exp(torch.clamp(param_values["log_modifiers"], *config.stage_b_modifier_clamp)).std().item()),
        },
    })
else:  # "shell" mode
    # Existing shell telemetry (lines 3072-3082)
    telemetry_b.update({
        "shell_edges": [float(x) for x in param_values["shell_edges"]],
        "shell_modifiers": [float(x) for x in final_shell_modifiers],
    })
```

**Lines Added:** ~15-20

---

### 7.5 — Integration Smoke Test

**Location:** New test in `tests/dbex/test_torch_refine_smoke.py`

**Objective:** Validate per-reflection mode end-to-end (ASU mapping, optimization, gradient flow, convergence).

**Test Structure:**
```python
def test_stage_b_per_reflection_smoke():
    """Validate Stage B per-reflection mode with ASU-based modifiers (Phase 7)."""
    config = RefinementConfig(
        enable_stage_b=True,
        stage_b_mode="per_reflection",  # Phase 7 new mode
        device="cuda" if torch.cuda.is_available() else "cpu",
        # ... (other config similar to test_stage_b_shell_modifiers)
    )

    telemetry_dict = run_nanobrag_refinement(
        refinement_inputs=inputs,
        baseline_detector=baseline_detector,
        config=config,
    )

    # Telemetry structure validation
    assert "B" in telemetry_dict, "Stage B telemetry missing"
    telem_b = telemetry_dict["B"]

    # ASU mode-specific fields
    assert "n_asu_unique" in telem_b, "ASU mode should report n_asu_unique"
    assert "optimizer_type" in telem_b, "ASU mode should report optimizer_type"
    assert "asu_modifier_stats" in telem_b, "ASU mode should report modifier stats"

    # Optimizer selection validation (P1 fixture ~35K ASU → Adam expected)
    assert telem_b["optimizer_type"] in ["adam", "lbfgs"], f"Invalid optimizer: {telem_b['optimizer_type']}"
    n_asu = telem_b["n_asu_unique"]
    assert n_asu > 0, "ASU mapping failed (0 unique reflections)"

    # Gradient flow validation (modifier stats should change from initial ~1.0)
    stats = telem_b["asu_modifier_stats"]
    assert stats["mean"] > 0.0, "ASU modifiers collapsed to zero"
    assert stats["mean"] != 1.0, "ASU modifiers unchanged (gradient flow broken)"

    # Convergence validation (Stage B should improve upon Stage A)
    telem_a = telemetry_dict["A"]
    chi_sq_a_final = telem_a["chi_squared"]
    chi_sq_b_final = telem_b["chi_squared"]

    # Relaxed improvement gate for smoke (canonical test uses stricter 3% gate)
    improvement_pct = 100 * (chi_sq_a_final - chi_sq_b_final) / chi_sq_a_final
    assert improvement_pct >= 0.01, f"Stage B degraded chi² (improvement={improvement_pct:.4f}%)"

    # Regression guards (Stage A should still pass)
    assert telem_a["status"] == "converged", "Stage A failed"
    assert telem_b["status"] == "converged", "Stage B failed"
```

**Lines Added:** ~60-80

**Runtime Estimate:** ~25-35s (Stage A + Stage B with small detector fixture)

**Selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke`

---

## 3. Risk Analysis

### R1: ASU Modifier Application Performance

**Risk:** `apply_asu_modifiers` slower than shell loop due to `torch.gather` overhead.

**Impact:** LOW (one-time cost per closure evaluation, ~1-5ms for 512³ grid)

**Mitigation:**
- Phase 6 unit test validated `apply_asu_modifiers` correctness
- Performance measured in Phase 7 smoke test (runtime < 60s acceptable)
- Fallback: shell mode remains available via `stage_b_mode="shell"` config

**Status:** LOW risk (helper already tested, no blockers expected)

---

### R2: Optimizer Selection Heuristic Needs Tuning

**Risk:** 10K parameter gate may not be optimal for all space groups.

**Impact:** LOW (affects optimization speed, not correctness)

**Mitigation:**
- 10K gate is conservative (based on LBFGS history size * typical HKL dimensions)
- P1 fixture ~35K → Adam (known to work from Phase 6 planning)
- P432 ~2K → LBFGS (known to work from shell mode tests)
- Document gate in findings.md as tunable threshold (REFINE-006 placeholder)

**Status:** LOW risk (conservative gate, both optimizers spec-permitted)

---

### R3: Gradient Compatibility with Adam

**Risk:** Stage B closure may have Adam-specific gradient issues (e.g., step vs closure API mismatch).

**Impact:** MEDIUM (would block Adam path, requiring LBFGS fallback)

**Mitigation:**
- LBFGS path already proven stable (shell mode tests PASSED)
- Adam-specific closure refactor if needed: replace `optimizer.step(closure)` with manual `loss.backward()` + `optimizer.step()`
- Phase 7 smoke test validates Adam path explicitly for n_asu ≥ 10K case

**Status:** MEDIUM risk (manageable, fallback to LBFGS if needed)

---

### R4: ASU Map Computation Time

**Risk:** `compute_hkl_asu_map` takes >10s for large grids, blocking setup.

**Impact:** LOW-MEDIUM (one-time cost, acceptable if <30s)

**Mitigation:**
- Phase 6 planning estimated 3-7s for 512³ grid (P1 ~35K ASU)
- Phase 7 smoke test measures actual time, logs warning if >10s
- Fallback: shell mode if ASU computation exceeds timeout (spec-permitted per spec:60)

**Status:** LOW risk (Phase 6 estimates within acceptable range)

---

## 4. Exit Criteria (Phase 7)

### Code Deliverables

1. **7.1 ✓** — ASU mode initialization branch in `_build_stage_b_params` (~35-40 lines)
2. **7.2 ✓** — Dynamic optimizer selection (LBFGS vs Adam) (~15-20 lines)
3. **7.3 ✓** — ASU modifier application in `compute_loss_stage_b` closure (~10-15 lines)
4. **7.4 ✓** — ASU telemetry fields (`n_asu_unique`, `optimizer_type`, `asu_modifier_stats`) (~15-20 lines)
5. **7.5 ✓** — Integration smoke test `test_stage_b_per_reflection_smoke` (~60-80 lines)

**Total Lines Added:** ~135-175 (including test)

---

### Validation Protocol

1. **Compilation Check:**
   ```bash
   python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('OK')"
   ```
   Expected: No import errors

2. **Unit Test Regression:**
   ```bash
   NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_asu_mapping.py
   ```
   Expected: 5 passed (Phase 6 tests unchanged)

3. **Shell Mode Regression:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
   ```
   Expected: 1 passed (existing shell mode unaffected)

4. **Per-Reflection Mode Smoke:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke
   ```
   Expected: 1 passed (ASU mode converges, telemetry valid)

5. **Collect-Only Verification:**
   ```bash
   pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke
   ```
   Expected: 1 test collected

---

### Decision Paths

**Path A: All Tests PASS**
- Conditions:
  - Compilation succeeds
  - Phase 6 unit tests PASS (5/5)
  - Shell mode regression PASS
  - Per-reflection smoke PASS (telemetry valid, convergence achieved, runtime <60s)
- Actions:
  1. Mark Phase 7 ✓ COMPLETE
  2. Commit with message: "TORCH-REFINE-004 Phase 7: Per-reflection mode integration (test PASSED)"
  3. Update fix_plan.md Attempts History (Phase 7 completion, artifacts path)
  4. Return to Galph for Phase 8 planning (telemetry + docs)

**Path B: Per-Reflection Smoke FAILS (Gradient Flow Issue)**
- Conditions:
  - Shell mode regression PASSES
  - Per-reflection smoke FAILS with assertion on modifier stats (mean == 1.0 → gradients not flowing)
- Actions:
  1. Inspect `log_modifiers.grad` in closure (check for None or zeros)
  2. Verify `apply_asu_modifiers` preserves gradient graph (should use `torch.gather`, not `.cpu().numpy()`)
  3. Debug optimizer step (Adam may need manual `loss.backward()` + `optimizer.step()` instead of `step(closure)`)
  4. Fix gradient flow bug (likely 1-5 line change)
  5. Rerun per-reflection smoke

**Path C: Per-Reflection Smoke FAILS (ASU Map Computation Timeout)**
- Conditions:
  - Per-reflection smoke hangs or exceeds 5min timeout during `compute_hkl_asu_map`
- Actions:
  1. Log ASU computation time
  2. If >30s → escalate to Galph with blocker report (spec:60 permits shell mode fallback)
  3. Mark Phase 7 blocked, document timeout in decision.md
  4. Recommended fix: add timeout guard in `_build_stage_b_params` (fallback to shell mode if ASU computation >30s)

**Path D: Shell Mode Regression FAILS**
- Conditions:
  - Shell mode test FAILS after Phase 7 changes (unexpected side effect)
- Actions:
  1. Rollback Phase 7 changes (ASU branch should be isolated behind `if config.stage_b_mode == "per_reflection"`)
  2. Debug shell mode path isolation (likely missing `else` branch or incorrect mode check)
  3. Fix branch logic
  4. Rerun all validation steps

---

## 5. Estimated Effort

| Task | Code Lines | Test Lines | Estimated Time | Confidence |
|------|------------|------------|----------------|------------|
| 7.1 ASU initialization | 35-40 | - | 30min | HIGH (~90%) |
| 7.2 Optimizer selection | 15-20 | - | 15min | HIGH (~95%) |
| 7.3 Modifier application | 10-15 | - | 20min | HIGH (~85%) |
| 7.4 ASU telemetry | 15-20 | - | 15min | HIGH (~90%) |
| 7.5 Integration smoke test | - | 60-80 | 40min | MEDIUM-HIGH (~80%) |
| Validation + debug buffer | - | - | 30min | - |
| **Total** | **75-95** | **60-80** | **~2.5 hours** | **HIGH (~85%)** |

**Single-Loop Feasibility:** YES (estimated 2.5 hours < 4 hour typical loop budget)

---

## 6. Findings Applied

**Mandatory Adherence:**
- **REFINE-001** (LBFGS scale warm-start) ✓ — Stage B inherits global scale from Stage A
- **REFINE-002** (acceptance gate) ✓ — Stage B improvement validated in smoke test
- **REFINE-005** (HKL halo mandatory) ✓ — Halo voxels fixed at ASU index 0 (Phase 6)
- **SCALE-001** (unscaled structure factors) ✓ — ASU modifiers applied post-interpolation
- **SCALE-002** (global post-simulation factor) ✓ — ASU modifiers are per-reflection
- **PHYSICS-LOSS-001** (variance-weighted loss) ✓ — Stage B uses same V = I_model + sigma² denominator
- **POLICY-001** (Environment Freeze) ✓ — No package installs, reuse Phase 6 helpers
- **ARCH-ENGINE-002** (lazy imports) ✓ — cctbx imported in `compute_hkl_asu_map` only when needed
- **spec-db-workflow.md:59** (per-reflection SHALL be default) ✓ — Phase 8 will make per_reflection default
- **spec-db-workflow.md:60** (shell mode fallback permitted) ✓ — Shell mode remains via `stage_b_mode="shell"`
- **spec-db-workflow.md:61** (tricubic + halo mandatory) ✓ — Halo requirement enforced (REFINE-005)
- **spec-db-workflow.md:107** (LBFGS/Adam permitted) ✓ — Dynamic selection per n_asu threshold

---

## 7. Phase 7 Completion Checklist

- [ ] **7.1** — ASU mode initialization in `_build_stage_b_params` (lines ~2432-2470)
- [ ] **7.2** — Dynamic optimizer selection (lines ~2447-2470)
- [ ] **7.3** — ASU modifier application in `compute_loss_stage_b` (lines ~2712-2730)
- [ ] **7.4** — ASU telemetry fields (lines ~3080-3100)
- [ ] **7.5** — Integration smoke test `test_stage_b_per_reflection_smoke` (new file or append)
- [ ] Compilation check PASSED
- [ ] Phase 6 unit tests regression PASSED (5/5)
- [ ] Shell mode regression PASSED
- [ ] Per-reflection smoke PASSED (telemetry + convergence)
- [ ] Collect-only verification PASSED (1 test collected)
- [ ] Artifacts committed (pytest logs, decision.md, summary.md)

---

## 8. Next Actions (After Phase 7 Complete)

**Phase 8 Scope (Tests + Telemetry):**
1. Extend telemetry HDF5 output (`_write_torch_outputs`) with ASU mode fields
2. Add `test_stage_b_shell_fallback` test (validates shell mode remains available)
3. Add `test_stage_b_mode_config_validation` (refuses invalid modes, enforces halo requirement)
4. Update `docs/TESTING_GUIDE.md` with Phase 7 selector
5. Update `docs/development/TEST_SUITE_INDEX.md` with new tests

**Phase 9 Scope (Documentation):**
1. Update `docs/findings.md` with REFINE-006 (ASU parameter count guidance)
2. Update `plans/active/TORCH-REFINE-004/implementation.md` Phase 7-9 checklist
3. Mark TORCH-REFINE-004 status `done` in `docs/fix_plan.md`

**Estimated Total Remaining:** 2-2.5 loops (Phases 8-9 combined ~4-5 hours)

---

**Confidence:** HIGH (~85%) — All integration points identified, helpers proven stable, no new physics/algorithms required.

**Recommendation:** APPROVE ready_for_implementation (Phase 7 single-loop delivery feasible).
