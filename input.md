# Ralph Input — Phase 6 Implementation (Per-Reflection ASU Mapping)

## Summary
Implement per-reflection Fhkl modifier parameterization with ASU (asymmetric unit) index mapping for Stage B using cctbx.miller symmetry operations.

## Mode
TDD

## Focus
TORCH-REFINE-004 — Stage B Per-Reflection Mode Migration (Phase 6: ASU Mapping Implementation)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_stage_b_asu_mapping.py::test_asu_mapping_p1` — Validate P1 space group (no symmetry, all indices unique)
- `tests/dbex/test_stage_b_asu_mapping.py::test_asu_mapping_p432` — Validate P432 high-symmetry (48-fold reduction)
- `tests/dbex/test_stage_b_asu_mapping.py::test_asu_halo_handling` — Validate halo voxels map to ASU index 0 with fixed modifier=1.0
- `tests/dbex/test_stage_b_asu_mapping.py::test_asu_friedel_pairs` — Validate (h,k,l) and (-h,-k,-l) map to same ASU index

## Artifacts
plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/{pytest_stage_b_asu.log, summary.md}

## Do Now

**Objective:** Implement Phase 6 ASU mapping infrastructure (3 helper functions + dynamic optimizer selection + unit tests) per `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/phase_6_planning_analysis.md §6 Implementation Checklist`.

**Core Tasks:**

**Implement:** `dbex/nanobrag_refinement.py::compute_hkl_asu_map` helper function
- Inputs: `hkl_grid: np.ndarray` (h,k,l,3), `crystal_symmetry` (from MTZ F.crystal_symmetry()), `halo_mask: np.ndarray` (optional boolean mask)
- Algorithm: Flatten HKL grid → convert to flex.miller_index → miller.set(anomalous_flag=False) → map_to_asu() → np.unique(return_inverse=True) → reshape to (h,k,l)
- Edge cases: Reserve ASU index 0 for halo voxels (if halo_mask provided), wrap cctbx calls in try/except and return None on failure (triggers shell mode fallback)
- Outputs: `(hkl_asu_map: torch.Tensor[int64], n_asu_unique: int)` or `(None, 0)` on failure
- Reference: `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py`

**Implement:** `dbex/nanobrag_refinement.py::initialize_asu_modifiers` helper function
- Inputs: `n_asu_unique: int`, `device: torch.device`, `dtype: torch.dtype`
- Initialize log-space modifiers near 0 (linear-space modifiers ≈ 1.0): `torch.zeros((n_asu_unique,), dtype=dtype, device=device, requires_grad=True)`
- Fix index 0 (halo) at log(1.0) = 0.0 with `requires_grad=False` if n_asu_unique > 1
- Return: `nn.Parameter` wrapping the tensor

**Implement:** `dbex/nanobrag_refinement.py::apply_asu_modifiers` helper function
- Inputs: `hkl_grid_base: torch.Tensor`, `log_modifiers: nn.Parameter`, `hkl_asu_map: torch.Tensor`
- Clamp log_modifiers to [-3.0, 3.0] range (modifier ∈ [0.05, 20.0])
- Convert to linear space: `modifiers = torch.exp(log_modifiers_clamped)`
- Broadcast via index lookup: `modifier_grid = modifiers[hkl_asu_map]`
- Apply element-wise: `hkl_grid_modified = hkl_grid_base * modifier_grid.unsqueeze(-1)`
- Return: `hkl_grid_modified: torch.Tensor`

**Implement:** Dynamic optimizer selection in Stage B setup (currently uses LBFGS)
- After ASU mapping computation, check `n_asu_unique` against gate threshold (10,000)
- If `n_asu_unique < 10000`: use LBFGS (spec default) with `max_iter=20, history_size=10, line_search_fn="strong_wolfe"`
- Else: use Adam (spec-permitted per spec-db-workflow.md:107) with `lr=1e-3, betas=(0.9, 0.999)`
- Store optimizer choice in telemetry: `stage_b_optimizer` field

**Test:** Create `tests/dbex/test_stage_b_asu_mapping.py` with 4 unit tests
- `test_asu_mapping_p1`: Synthetic P1 space group (no symmetry), assert all indices unique, n_asu == n_voxels
- `test_asu_mapping_p432`: Synthetic P432 space group (48-fold), assert n_asu ≈ n_voxels / 48, validate symmetry folding
- `test_asu_halo_handling`: Provide halo_mask with some voxels marked True, assert halo voxels map to ASU index 0, assert modifiers[0].requires_grad == False
- `test_asu_friedel_pairs`: Synthetic space group with Friedel pairs (h,k,l) and (-h,-k,-l), assert both map to same ASU index

**Validate:** Run test suite with pytest
- Execute: `NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_asu_mapping.py`
- Expected: All 4 tests PASS with runtime < 10s (unit tests with synthetic space groups)
- Archive: `plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/pytest_stage_b_asu.log`

**Regression:** Confirm existing Stage B shell mode tests still pass
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

## How-To Map

**Step 1: Implement compute_hkl_asu_map helper**
```bash
# Reference: plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py
# Location: dbex/nanobrag_refinement.py (add after compute_hkl_shell_lookup, ~line 350)
# Inputs: hkl_grid (h,k,l,3), crystal_symmetry (from MTZ), halo_mask (optional)
# Algorithm: Flatten → flex.miller_index → miller.set → map_to_asu() → np.unique → reshape
# Edge case: Reserve ASU index 0 for halo voxels (shift all indices +1 if halo_mask provided)
# Failure handling: Wrap cctbx calls in try/except, return (None, 0) on failure
```

**Step 2: Implement initialize_asu_modifiers helper**
```bash
# Location: dbex/nanobrag_refinement.py (add after compute_hkl_asu_map)
# Initialize: torch.zeros((n_asu_unique,), dtype=dtype, device=device, requires_grad=True)
# Fix halo: If index 0 is halo, set modifiers[0].requires_grad = False
# Return: nn.Parameter(modifiers)
```

**Step 3: Implement apply_asu_modifiers helper**
```bash
# Location: dbex/nanobrag_refinement.py (add after initialize_asu_modifiers)
# Clamp: log_modifiers_clamped = torch.clamp(log_modifiers, -3.0, 3.0)
# Exp: modifiers = torch.exp(log_modifiers_clamped)
# Broadcast: modifier_grid = modifiers[hkl_asu_map]
# Apply: hkl_grid_modified = hkl_grid_base * modifier_grid.unsqueeze(-1)
```

**Step 4: Add dynamic optimizer selection**
```bash
# Location: dbex/nanobrag_refinement.py Stage B setup (after ASU mapping computation)
# Check: if n_asu_unique < config.stage_b_optimizer_gate (default 10000):
#   optimizer = LBFGS(params, max_iter=20, history_size=10, line_search_fn="strong_wolfe")
# else:
#   optimizer = Adam(params, lr=config.stage_b_adam_lr)  # default 1e-3
# Telemetry: stage_b_optimizer = "LBFGS" or "Adam"
```

**Step 5: Extend RefinementConfig**
```bash
# Location: dbex/nanobrag_refinement.py RefinementConfig dataclass (~line 50)
# Add fields:
#   stage_b_optimizer_gate: int = 10000  # n_asu threshold for LBFGS vs Adam
#   stage_b_adam_lr: float = 1e-3        # Adam learning rate
#   stage_b_modifier_clamp: tuple[float, float] = (-3.0, 3.0)  # log-space clamp
```

**Step 6: Create test file**
```bash
# Create: tests/dbex/test_stage_b_asu_mapping.py (~200-250 lines)
# Import: cctbx.miller, cctbx.sgtbx, cctbx.crystal.symmetry, cctbx.array_family.flex
# Test 1: P1 space group (all indices unique, n_asu == n_voxels)
# Test 2: P432 space group (48-fold reduction, n_asu ≈ n_voxels / 48)
# Test 3: Halo handling (halo_mask provided, index 0 fixed at modifier=1.0)
# Test 4: Friedel pairs (h,k,l and -h,-k,-l map to same ASU index)
```

**Step 7: Run test suite**
```bash
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_asu_mapping.py 2>&1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/pytest_stage_b_asu.log
```

**Step 8: Regression guard**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
```

## Pitfalls To Avoid

**Environment Freeze (POLICY-001):**
- ✅ Use existing cctbx.miller (confirmed available 2025-11-24T125000Z)
- ❌ Do NOT install additional packages or upgrade cctbx
- If cctbx call fails at runtime, return None and fallback to shell mode (spec-permitted per spec:60)

**Device/Dtype Neutrality:**
- All torch tensors must preserve input device and dtype
- `hkl_asu_map` should be torch.int64 on same device as hkl_grid
- `modifiers` parameter should match hkl_grid dtype (float32 or float64)

**Lazy Imports (ARCH-ENGINE-002):**
- Import cctbx.miller inside compute_hkl_asu_map function, not at module top level
- Allows module to load without cctbx dependency for DiffBragg backend

**HKL Halo Handling (REFINE-005, spec:61):**
- Halo voxels (±1 beyond MTZ range) have no structure factor
- MUST map halo voxels to ASU index 0 with fixed modifier=1.0 (requires_grad=False)
- Failure to fix halo modifier will cause gradient explosions

**Symmetry Failure Handling:**
- Wrap cctbx.miller.set construction in try/except
- On exception, log warning with error details and return (None, 0)
- Fallback to shell mode is spec-permitted (spec-db-workflow.md:60)
- Add telemetry field: `stage_b_mode_fallback_reason` (e.g., "asu_mapping_failed")

**Test Isolation:**
- All unit tests must use synthetic space groups (P1, P432) with small HKL grids (<10K voxels)
- Do NOT use golden_data fixture in Phase 6 unit tests (integration tests are Phase 7)
- Runtime must be < 10s for all 4 tests combined

**Spec Compliance:**
- Per-reflection mode is NOT YET the default (Phase 6 only adds infrastructure)
- Shell mode remains default until Phase 7 optimization loop complete
- Phase 6 deliverable: helpers + unit tests only, no Stage B runtime integration

## If Blocked

**Blocker: cctbx.miller import fails**
- Symptom: `ModuleNotFoundError: No module named 'cctbx'`
- Action: Document blocker in `docs/fix_plan.md` Attempts History with exact error signature
- Fallback: Mark TORCH-REFINE-004 blocked, note that Environment Freeze prevents cctbx installation
- Escalation: Supervisor must decide whether to request environment update (violates POLICY-001)

**Blocker: Unit tests fail due to cctbx API mismatch**
- Symptom: cctbx.miller.set API different from planning analysis expectations
- Action: Archive error logs under `plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/`
- Fallback: Research cctbx.miller API documentation (grep simtbx_project for usage examples)
- If API fundamentally incompatible: Document and escalate to supervisor for fallback design

**Blocker: Regression tests fail**
- Symptom: `test_stage_b_shell_modifiers` fails after Phase 6 implementation
- Action: Verify no changes to Stage B shell mode code paths (Phase 6 should be new code only)
- Debug: Check if RefinementConfig field additions broke existing instantiation
- Mitigation: Add default values to new config fields, ensure backward compatibility

## Findings Applied

**Mandatory Adherence:**

**REFINE-001** (LBFGS scale warm-start) — Stage B inherits global scale from Stage A final state; per-reflection modifiers initialized near 1.0 (log-space 0.0)

**REFINE-002** (acceptance gate) — Stage B improvement gate separate from Stage A; per-reflection mode will use same acceptance logic as shell mode

**REFINE-005** (HKL halo mandatory) — Halo voxels MUST map to ASU index 0 with fixed modifier=1.0 (requires_grad=False) to prevent gradient explosions

**SCALE-001** (structure factors unscaled) — ASU modifiers applied post-interpolation to HKL grid, not pre-simulation to structure factors

**SCALE-002** (global post-simulation factor) — ASU modifiers are per-reflection scale factors, orthogonal to global post-simulation scale

**PHYSICS-LOSS-001** (variance-weighted loss consistency) — Stage B uses same V = I_model + sigma² denominator; per-reflection modifiers affect numerator via HKL grid modification

**POLICY-001** (Environment Freeze) — Use existing cctbx.miller (confirmed available); no installations; if cctbx fails, return None and fallback to shell mode

**ARCH-ENGINE-002** (lazy imports) — Import cctbx.miller inside compute_hkl_asu_map function body, not at module top level

**GEOMETRY-003** (B_ideal convention) — Not directly relevant to Stage B (Stage A geometry fixed); per-reflection modifiers do not affect crystal geometry

**spec-db-workflow.md:59** (per-reflection SHALL be default) — Core normative requirement; Phase 6 adds infrastructure, Phase 7 makes it default

**spec-db-workflow.md:60** (shell mode fallback permitted) — Fallback to shell mode on ASU mapping failure is spec-compliant; add `stage_b_mode_fallback_reason` telemetry

**spec-db-workflow.md:61** (tricubic + halo mandatory) — Halo handling designed: ASU index 0 reserved for halo voxels with fixed modifier=1.0

**spec-db-workflow.md:107** (optimizer flexibility) — Dynamic LBFGS/Adam selection based on n_asu_unique threshold (10K gate); LBFGS spec default, Adam permitted

## Pointers

**Specs:**
- `docs/spec-db-workflow.md:58-61` — Stage B normative requirements (per-reflection SHALL be default, halo mandatory)
- `docs/spec-db-workflow.md:102-115` — Optimization strategy (LBFGS default, Adam permitted for large parameter counts)
- `docs/spec-db-core.md:57-80` — Variance definition (V = I_model + sigma²)

**Architecture:**
- `docs/architecture/pytorch_design.md §1.1.1` — HKL halo requirements (±1 voxels beyond MTZ range)

**Planning Analysis:**
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/phase_6_planning_analysis.md` — Comprehensive planning (algorithm design, risk mitigation, implementation checklist)
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py` — Algorithm pseudocode with edge case handling
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/parameter_count_analysis.md` — Space group analysis, n_asu estimates
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/optimizer_decision.md` — LBFGS vs Adam trade-off analysis

**Implementation Plan:**
- `plans/active/TORCH-REFINE-004/implementation.md:1-38` — Phases 1-5 complete (shell mode implemented)

**Fix Plan:**
- `docs/fix_plan.md:227-239` — TORCH-REFINE-004 entry (current status: in_progress Phase 6 planning)

**Findings:**
- `docs/findings.md` — REFINE-001/002/005, SCALE-001/002, PHYSICS-LOSS-001, POLICY-001, ARCH-ENGINE-002

**Testing:**
- `docs/TESTING_GUIDE.md §2` — Test selector conventions and environment variables
- `docs/development/TEST_SUITE_INDEX.md` — Test registry (will be updated in Phase 9 after tests added)

**Existing Code References:**
- `dbex/nanobrag_refinement.py:~350` — compute_hkl_shell_lookup (pattern to follow for compute_hkl_asu_map)
- `dbex/nanobrag_refinement.py:~50` — RefinementConfig dataclass (add new fields)
- `simtbx_project/simtbx/diffBragg/utils.py:1000-1027` — open_mtz function (cctbx.miller usage example)

## Next Up

**Phase 7 (Optimization Loop Integration):** After Phase 6 unit tests pass, integrate per-reflection modifiers into Stage B optimization loop:
- Replace shell mode modifier application with apply_asu_modifiers call
- Update LBFGS/Adam closure to use dynamic optimizer selection
- Add integration smoke test with golden_data fixture (P1 space group, ~35K parameters, Adam optimizer)
- Validate convergence: Stage B improvement ≥ Stage A final loss (acceptance gate)

**Phase 8 (Telemetry & Documentation):** Extend Stage B telemetry with per-reflection mode fields:
- `stage_b_mode`: "shell" | "per_reflection"
- `stage_b_optimizer`: "LBFGS" | "Adam"
- `n_asu_unique`: int (number of unique ASU reflections)
- `halo_voxel_count`: int (if halo handling active)
- `modifier_stats`: dict (min, max, mean, std of linear-space modifiers)

## Doc Sync Plan

Not required for Phase 6 (unit tests added, not user-facing). Doc sync required in Phase 9 after integration tests added and per-reflection mode becomes default.
