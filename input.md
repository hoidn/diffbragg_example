# Input for Ralph — TORCH-REFINE-004 Phase 7 Implementation

## Summary
Integrate ASU-based per-reflection modifiers into Stage B optimization loop (parallel to existing shell mode path).

## Mode
None (production code implementation)

## Focus
TORCH-REFINE-004 Phase 7 — Stage B Per-Reflection Mode Migration (Optimization Loop Integration)

## Branch
`integration`

## Mapped Tests
- `tests/dbex/test_stage_b_asu_mapping.py` — Phase 6 regression (5 tests, ALL must PASS)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` — Shell mode regression (must PASS)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` — NEW Phase 7 smoke (must PASS)

## Artifacts
`plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/`
- `pytest_phase6_regression.log` — Phase 6 unit tests output
- `pytest_shell_regression.log` — Shell mode smoke output
- `pytest_per_reflection_smoke.log` — Per-reflection smoke output (NEW)
- `compilation_check.log` — Import validation
- `collect_only.log` — Selector discovery verification
- `decision.md` — Path outcome (A/B/C/D)
- `summary.md` — Turn summary

---

## Do Now

**Objective:** Implement Phase 7 per-reflection mode integration into Stage B loop.

**Context:**
- **Phase 6 ✓ COMPLETE** (commit 19dd43e + aebdddd): ASU mapping helpers implemented and tested (5/5 tests PASSED, runtime 1.06s), engine telemetry schema fix applied (`telemetry_version` field added, regression guard PASSED).
- **Phase 7 Scope:** Integrate ASU modifiers into existing Stage B loop via mode branching (`stage_b_mode="per_reflection"` vs `"shell"`).

**Tasks:**
1. **Implement:** 7.1-7.4 integration code in `dbex/nanobrag_refinement.py` (~75-95 lines total)
2. **Test:** Create `test_stage_b_per_reflection_smoke` in `tests/dbex/test_torch_refine_smoke.py` (~60-80 lines)
3. **Validate:** Run 4-step validation protocol (compilation, Phase 6 regression, shell regression, per-reflection smoke)
4. **Synthesize:** Write decision.md (Path A/B/C/D outcome) + summary.md
5. **Commit:** All code + artifacts with message `"TORCH-REFINE-004 Phase 7: Per-reflection mode integration — tests: <selector>"`

---

## How-To Map

### Step 1: Read Planning Analysis
```bash
cat plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/phase_7_planning_analysis.md
```
**Action:** Understand integration points (7.1-7.4 task breakdown), dataflow diagram, risk mitigation.

---

### Step 2: Implement 7.1 — ASU Mode Initialization

**File:** `dbex/nanobrag_refinement.py::_build_stage_b_params` (lines 2383-2546)

**Location:** Insert mode branch at line ~2432 (before existing shell lookup)

**Code Template:**
```python
# Phase 7: Branch on Stage B mode (per-reflection vs shell)
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
    param_values = {
        "asu_indices": asu_indices_t,
        "n_asu_unique": n_asu_unique,
        "log_modifiers": log_modifiers,
        "params": stage_b_params,
    }
else:  # "shell" mode
    # Existing shell mode path (lines 2433-2443)
    shell_indices, shell_edges = compute_hkl_shell_lookup(
        crystal, hkl_metadata, n_shells=config.stage_b_n_shells, device=device, dtype=dtype
    )
    shell_modifier_raw = torch.zeros(config.stage_b_n_shells, device=stage_b_param_device, dtype=dtype, requires_grad=True)
    identity_raw = math.log(math.expm1(0.5))  # softplus(identity_raw)*2 == 1.0
    shell_modifier_raw.data.fill_(identity_raw)
    stage_b_params = [shell_modifier_raw]

    param_values = {
        "shell_indices": shell_indices,
        "shell_edges": shell_edges,
        "shell_modifier_raw": shell_modifier_raw,
        "params": stage_b_params,
    }
```

**Lines Added:** ~35-40

---

### Step 3: Implement 7.2 — Dynamic Optimizer Selection

**File:** `dbex/nanobrag_refinement.py::_build_stage_b_params` (lines 2447-2455)

**Location:** Replace existing LBFGS-only setup with mode-aware branch

**Code Template:**
```python
# Phase 7: Dynamic optimizer selection based on mode and parameter count
if config.stage_b_mode == "per_reflection":
    n_asu = param_values["n_asu_unique"]
    if n_asu >= config.stage_b_optimizer_gate:  # Default 10000
        # Adam for large parameter counts (spec-db-workflow.md:107 permits Adam)
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
    stage_b_optimizer = torch.optim.LBFGS(
        stage_b_params,
        history_size=config.history_size,
        max_iter=config.max_iter,
        tolerance_grad=config.tolerance_grad,
        tolerance_change=config.tolerance_change,
        line_search_fn='strong_wolfe'
    )
    param_values["optimizer_type"] = "lbfgs"

# Continue with common telemetry accumulators (lines 2457-2546)
```

**Lines Added:** ~15-20

---

### Step 4: Implement 7.3 — ASU Modifier Application in Closure

**File:** `dbex/nanobrag_refinement.py::_build_stage_b_lbfgs_closure` (lines 2637-2906, specifically 2710-2722)

**Location:** Inside `compute_loss_stage_b` function, replace shell modifier loop with mode branch

**Code Template:**
```python
def compute_loss_stage_b(work_item_ids: List[int], is_full: bool = False, force_panel_eval: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
    # ... (lines 2637-2710: device setup, eval branch, hkl_grid_local)

    # Phase 7: Mode-aware modifier application
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
            hkl_grid_modified = torch.where(
                mask,
                hkl_grid_local * modifier_value,
                hkl_grid_modified
            )

    # ... (rest of closure unchanged: warm cache setup, simulator run, loss computation)
```

**Lines Changed:** ~10-15

**Important:** Extract `asu_indices` and `log_modifiers` from `param_values` at closure scope (lines ~2600-2610, in closure preamble).

---

### Step 5: Implement 7.4 — ASU Telemetry Fields

**File:** `dbex/nanobrag_refinement.py::_run_stage_b_lbfgs` (lines 2909-3107)

**Location:** Add ASU fields to telemetry dict construction (after line ~3080, before `return telemetry_b`)

**Code Template:**
```python
# Phase 7: Mode-specific telemetry
if config.stage_b_mode == "per_reflection":
    log_modifiers_final = param_values["log_modifiers"]
    clamp_range = config.stage_b_modifier_clamp
    modifiers_exp = torch.exp(torch.clamp(log_modifiers_final, *clamp_range))
    telemetry_b.update({
        "n_asu_unique": int(param_values["n_asu_unique"]),
        "optimizer_type": param_values["optimizer_type"],  # "adam" or "lbfgs"
        "asu_modifier_stats": {
            "min": float(modifiers_exp.min().item()),
            "max": float(modifiers_exp.max().item()),
            "mean": float(modifiers_exp.mean().item()),
            "std": float(modifiers_exp.std().item()),
        },
    })
else:  # "shell" mode
    # Existing shell telemetry (lines 3072-3082)
    final_shell_modifiers = F.softplus(param_values["shell_modifier_raw"]).detach() * 2.0
    telemetry_b.update({
        "shell_edges": [float(x) for x in param_values["shell_edges"]],
        "shell_modifiers": [float(x) for x in final_shell_modifiers],
    })
```

**Lines Added:** ~15-20

---

### Step 6: Create Integration Smoke Test

**File:** `tests/dbex/test_torch_refine_smoke.py`

**Location:** Append after `test_stage_b_shell_modifiers` (line ~1300)

**Code Template:**
```python
def test_stage_b_per_reflection_smoke():
    """
    Validate Stage B per-reflection mode with ASU-based modifiers (Phase 7).

    Exit Criteria:
    - Telemetry includes ASU mode-specific fields (n_asu_unique, optimizer_type, asu_modifier_stats)
    - Optimizer selection validates correctly (P1 fixture ~35K ASU → Adam expected)
    - Gradient flow verified (modifier stats change from initial ~1.0)
    - Stage B improves upon Stage A (chi² reduction ≥0.01%)
    - Stage A/B both converge (status="converged")

    Mode: TDD (test-first), per-reflection default not yet enforced (Phase 8)
    Fixture: refGeom_small (29 ROIs, P1 space group ~35K unique ASU)
    Runtime: ~25-35s (Stage A + Stage B with small detector)
    """
    if os.getenv("AUTHORITATIVE_CMDS_DOC") != "./docs/TESTING_GUIDE.md":
        pytest.skip("Requires AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md")

    # Load canonical small-detector fixture
    inputs, baseline_detector, canonical_baseline = load_refgeom_refinement_inputs(detector_size="small")

    config = RefinementConfig(
        enable_stage_b=True,
        stage_b_mode="per_reflection",  # Phase 7 new mode
        device="cuda" if torch.cuda.is_available() else "cpu",
        enable_stage_a_warm_cache=False,  # Cold mode for determinism (PERF-WARM-001)
        sigma_source="cli_override",
        sigma_readout_adu=os.getenv("DBEX_SMOKE_SIGMA_SOURCE", "cli_override"),
    )

    telemetry_dict = run_nanobrag_refinement(
        refinement_inputs=inputs,
        baseline_detector=baseline_detector,
        config=config,
    )

    # Telemetry structure validation
    assert "A" in telemetry_dict, "Stage A telemetry missing"
    assert "B" in telemetry_dict, "Stage B telemetry missing (enable_stage_b=True)"
    telem_a = telemetry_dict["A"]
    telem_b = telemetry_dict["B"]

    # ASU mode-specific fields (Phase 7.4)
    assert "n_asu_unique" in telem_b, "ASU mode should report n_asu_unique"
    assert "optimizer_type" in telem_b, "ASU mode should report optimizer_type"
    assert "asu_modifier_stats" in telem_b, "ASU mode should report modifier stats"

    # Optimizer selection validation (P1 fixture ~35K ASU → Adam expected per Phase 6 planning)
    assert telem_b["optimizer_type"] in ["adam", "lbfgs"], f"Invalid optimizer: {telem_b['optimizer_type']}"
    n_asu = telem_b["n_asu_unique"]
    assert n_asu > 0, "ASU mapping failed (0 unique reflections)"
    # P1 fixture expected ~35K unique ASU (from Phase 6 planning analysis)
    assert 20000 < n_asu < 60000, f"Unexpected n_asu={n_asu} (expected ~35K for P1 fixture)"

    # Gradient flow validation (modifier stats should change from initial ~1.0)
    stats = telem_b["asu_modifier_stats"]
    assert stats["mean"] > 0.0, "ASU modifiers collapsed to zero"
    assert abs(stats["mean"] - 1.0) > 0.001, f"ASU modifiers unchanged (mean={stats['mean']:.6f}, gradient flow broken)"

    # Convergence validation (Stage B should improve upon Stage A)
    chi_sq_a_final = telem_a["chi_squared"]
    chi_sq_b_final = telem_b["chi_squared"]
    improvement_pct = 100 * (chi_sq_a_final - chi_sq_b_final) / chi_sq_a_final

    # Relaxed improvement gate for smoke (canonical test would use stricter 3% gate)
    assert improvement_pct >= 0.01, f"Stage B degraded chi² (improvement={improvement_pct:.4f}%)"

    # Regression guards (Stage A should still pass)
    assert telem_a["status"] == "converged", f"Stage A failed: status={telem_a['status']}"
    assert telem_b["status"] == "converged", f"Stage B failed: status={telem_b['status']}"
```

**Lines Added:** ~60-80

**Selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke`

---

### Step 7: Validation Protocol

**7.1 Compilation Check:**
```bash
python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement; print('Compilation OK')" > plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/compilation_check.log 2>&1 || echo "FAILED"
```

**7.2 Phase 6 Unit Test Regression:**
```bash
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_asu_mapping.py > plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/pytest_phase6_regression.log 2>&1
```
**Expected:** `5 passed` (Phase 6 tests unchanged)

**7.3 Shell Mode Regression:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers > plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/pytest_shell_regression.log 2>&1
```
**Expected:** `1 passed` (existing shell mode unaffected)

**7.4 Per-Reflection Smoke:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke > plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/pytest_per_reflection_smoke.log 2>&1
```
**Expected:** `1 passed` (ASU mode converges, telemetry valid, runtime <60s)

**7.5 Collect-Only Verification:**
```bash
pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke > plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/collect_only.log 2>&1
```
**Expected:** `1 test collected`

---

### Step 8: Decision Synthesis

Create `plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/decision.md` with Path outcome:

**Path A (All Tests PASS):**
- Mark Phase 7 ✓ COMPLETE
- Commit message: `"TORCH-REFINE-004 Phase 7: Per-reflection mode integration — tests: test_stage_b_per_reflection_smoke"`
- Return to Galph for Phase 8 planning

**Path B (Per-Reflection Smoke FAILS — Gradient Flow):**
- Debug `log_modifiers.grad` in closure (check for None or zeros)
- Verify `apply_asu_modifiers` preserves gradient graph
- Fix gradient flow bug (likely 1-5 line change)
- Rerun per-reflection smoke

**Path C (Per-Reflection Smoke FAILS — ASU Timeout):**
- Log ASU computation time
- If >30s → escalate to Galph with blocker report
- Mark Phase 7 blocked

**Path D (Shell Mode Regression FAILS):**
- Rollback Phase 7 changes
- Debug shell mode path isolation
- Fix branch logic
- Rerun all validation steps

---

### Step 9: Turn Summary

Create `plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/summary.md`:

```markdown
### Turn Summary
Implemented Phase 7 per-reflection mode integration: ASU modifiers + dynamic optimizer selection (Adam/LBFGS) now functional in Stage B loop.
Per-reflection smoke test PASSED (n_asu ~35K, optimizer=adam, chi² improved X.XX%, mean modifier=X.XX), shell mode regression clean.
Next: Phase 8 telemetry HDF5 output + fallback tests, then Phase 9 docs + TORCH-REFINE-004 closure.
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/ (pytest_per_reflection_smoke.log, decision.md)
```

---

### Step 10: Commit

```bash
git add -A
git commit -m "TORCH-REFINE-004 Phase 7: Per-reflection mode integration — tests: test_stage_b_per_reflection_smoke"
git push
```

---

## Pitfalls To Avoid

1. **Mode Branch Isolation:** Ensure `if config.stage_b_mode == "per_reflection"` checks are complete with `else` clauses; shell mode path must remain untouched.

2. **Device Consistency:** Respect `stage_b_param_device` (line 2440) for CPU fallback compatibility (GRADIENT-001); do NOT hardcode `device` for parameter init.

3. **Closure Scope Variables:** Extract `asu_indices` and `log_modifiers` from `param_values` in closure preamble (lines ~2600-2610), NOT inside `compute_loss_stage_b` function body.

4. **Optimizer API Mismatch:** If Adam path fails, replace `optimizer.step(closure)` with manual `loss.backward()` + `optimizer.step()` (LBFGS requires closure, Adam does not).

5. **Telemetry Mode Guard:** Add `if config.stage_b_mode == "per_reflection"` checks before accessing ASU-specific fields in telemetry dict (lines ~3080).

6. **Gradient Preservation:** Do NOT call `.cpu().numpy()`, `.detach()`, or `.item()` on `log_modifiers` or `asu_indices` inside `compute_loss_stage_b` closure (breaks gradient graph).

7. **Halo Handling:** Phase 6 `initialize_asu_modifiers` already fixes halo at index 0; do NOT add duplicate halo guards in Phase 7.

8. **Spec Compliance:** Per-reflection mode is NOT yet default (Phase 8 will enforce); tests must explicitly set `stage_b_mode="per_reflection"`.

9. **Test Isolation:** Run Phase 6 unit tests and shell regression BEFORE per-reflection smoke to catch branch isolation bugs early.

10. **Import Statements:** Ensure `from torch.nn import functional as F` exists for `F.softplus` in shell mode branch (lines ~2710).

---

## If Blocked

1. **Compilation Fails:** Fix import errors (likely missing `F` or `torch.optim.Adam`), retry compilation check.

2. **Phase 6 Regression Fails:** Rollback Phase 7 changes (Phase 6 helpers should be unchanged); debug import or test environment.

3. **Shell Regression Fails:** Isolate shell mode branch with explicit `else` clause; verify no ASU code executes when `mode == "shell"`.

4. **Per-Reflection Smoke Fails (Gradient Flow):** Inspect `log_modifiers.grad` in closure; verify `apply_asu_modifiers` uses `torch.gather` (not `.numpy()`); debug optimizer step API.

5. **Per-Reflection Smoke Fails (Timeout):** Log ASU computation time; if >30s, escalate to Galph with blocker report (spec:60 permits shell mode fallback).

6. **Collect-Only Fails:** Check test name typo; ensure `test_stage_b_per_reflection_smoke` is in `test_torch_refine_smoke.py`.

---

## Findings Applied

- **REFINE-001** (LBFGS scale warm-start) ✓ — Stage B inherits global scale from Stage A
- **REFINE-002** (acceptance gate) ✓ — Stage B improvement validated in smoke test
- **REFINE-005** (HKL halo mandatory) ✓ — Halo voxels fixed at ASU index 0 (Phase 6)
- **SCALE-001** (unscaled structure factors) ✓ — ASU modifiers applied post-interpolation
- **SCALE-002** (global post-simulation factor) ✓ — ASU modifiers are per-reflection
- **PHYSICS-LOSS-001** (variance-weighted loss) ✓ — Stage B uses same V = I_model + sigma² denominator
- **POLICY-001** (Environment Freeze) ✓ — No package installs, reuse Phase 6 helpers
- **ARCH-ENGINE-002** (lazy imports) ✓ — cctbx imported in `compute_hkl_asu_map` only when needed
- **spec-db-workflow.md:59** (per-reflection SHALL be default) ✓ — Phase 8 will enforce default
- **spec-db-workflow.md:60** (shell mode fallback permitted) ✓ — Shell mode remains via `stage_b_mode="shell"`
- **spec-db-workflow.md:61** (tricubic + halo mandatory) ✓ — Halo requirement enforced (REFINE-005)
- **spec-db-workflow.md:107** (LBFGS/Adam permitted) ✓ — Dynamic selection per n_asu threshold

---

## Pointers

- **Planning Analysis:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/phase_7_planning_analysis.md` (comprehensive task breakdown, dataflow diagram, risk mitigation)
- **Phase 6 Helpers:** `dbex/nanobrag_refinement.py:239-447` (`compute_hkl_asu_map`, `initialize_asu_modifiers`, `apply_asu_modifiers`)
- **Integration Points:** `dbex/nanobrag_refinement.py:2383-2546` (`_build_stage_b_params`), lines 2637-2906 (`compute_loss_stage_b` closure)
- **Shell Mode Reference:** `dbex/nanobrag_refinement.py:2710-2722` (existing shell modifier application loop)
- **Test Reference:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (shell mode smoke template)
- **Spec:** `docs/spec-db-workflow.md:59-61` (per-reflection normative requirement), lines 107 (optimizer flexibility)
- **Test Registry:** `docs/TESTING_GUIDE.md:§2.2` (Stage B selectors), `docs/development/TEST_SUITE_INDEX.md` (selector index)

---

## Next Up (After Phase 7 Complete)

**Phase 8:** Telemetry HDF5 output, fallback tests (`test_stage_b_shell_fallback`, `test_stage_b_mode_config_validation`), test registry sync.

**Phase 9:** Documentation updates (`docs/findings.md` REFINE-006, implementation plan Phase 7-9 checklist), TORCH-REFINE-004 closure.

---

**Estimated Effort:** 2.5 hours (7.1-7.4 implementation ~1.5h, 7.5 test ~40min, validation ~30min)

**Confidence:** HIGH (~85%) — Integration points clear, helpers proven, no new physics/algorithms.
