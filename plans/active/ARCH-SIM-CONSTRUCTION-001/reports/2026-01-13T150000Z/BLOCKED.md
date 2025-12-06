# ARCH-SIM-CONSTRUCTION-001 — BLOCKED (2026-01-13T150000Z)

## Status: blocked_pending_environment

## Summary of C.39 Omega Hypothesis Rejection

Phase C.39 attempted to implement omega compensation for SQUARE lattices with oversample>1, based on instrumentation from `reports/2026-01-11T010000Z/` suggesting the oversample accumulation path multiplied each subpixel by `last_omega≈1e-6`, reducing the final intensity by that factor.

**Hypothesis**: Apply omega once after the Riemann sum (instead of per-subpixel) to preserve the `(Na·Nb·Nc)²` amplitude boost.

**Result**: Hypothesis definitively rejected. Ralph correctly blocked the implementation after discovering omega is a **red herring**.

## Evidence That Deficit Exists Before Omega Application

### Key Finding from C.39 Re-analysis

Examining the telemetry from `reports/2026-01-13T010000Z/square_lattice_probe_os13.log`:

1. **Raw sum before omega**: `trace_subpixel_F_total_sq_sum` shows the deficit of 90.60% appears in the raw accumulated subpixel intensity **before** any omega multiplication

2. **Omega cancels in ratio**: Both base run (N_cells=1×1×1) and scaled run (N_cells=41×29×32) have omega≈1e-6. When computing the ratio to test `(Na·Nb·Nc)²` scaling, omega **cancels out**, so it cannot be the source of the 90.60% deficit

3. **F_latt amplitude deficit**: Per-subpixel sincg accumulation produces F_latt at only **11% of expected amplitude**:
   - Observed: F_latt ≈ 4206.5
   - Expected: F_latt = Na×Nb×Nc = 41×29×32 = 38,048
   - Ratio: 4206.5 / 38,048 ≈ 0.1106 (11.06%)

4. **Intensity discrepancy exceeds F_latt²**:
   - F_latt deficit squared: (0.1106)² ≈ 0.0122 → predicts 1.2% of expected intensity
   - Observed intensity: 9.4% of expected
   - This suggests **multiple compounding factors** in the sincg lattice weight computation

## Root Cause: sincg Lattice Factor Computation Bug in nanobrag_torch

The evidence points to a bug in how `nanobrag_torch` computes the lattice factor F_latt from the per-axis sincg functions. The observed 11% amplitude (vs 100% expected) suggests:

**Possible mechanisms:**
- Incorrect normalization or missing multiplier in the sincg product
- Geometric/grid issues causing most samples to miss the sincg peak
- Domain/boundary effects not properly accounted for
- Missing factor related to lattice shape (SQUARE vs other shapes)

## PROBE-FREEZE-001 Constraint

Phases C.34 through C.38 exhausted the diagnostic capacity available under PROBE-FREEZE-001:
- **C.34**: Per-subpixel payload instrumentation
- **C.35**: Oversample normalization fix (removed 169× dilution)
- **C.36**: Subpixel offset telemetry
- **C.37**: (planned) HKL projection audit
- **C.38**: Oversample accumulation sanity check
- **C.39**: Omega compensation attempt (rejected)

Further instrumentation would require either:
- Creating new plan-local diagnostic scripts (violates PROBE-FREEZE-001)
- Modifying `nanobrag_torch` internals beyond the opt-in telemetry hooks
- Expanding probe script scope into shadow-pipeline territory

All of these are **forbidden** under current policy.

## Three Unblock Options

### Option A: nanobrag_torch Maintainer Investigation

**Scope**: Engage the `nanobrag_torch` maintainer to investigate sincg lattice factor computation for SQUARE lattices

**Deliverables**:
- Review `src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` sincg logic
- Validate against reference implementation or analytical formula
- Identify source of 11% amplitude (vs 100% expected)
- Provide bugfix or clarify expected behavior

**Blockers**: Requires maintainer availability and engagement

### Option B: spec_change Initiative

**Scope**: Relax DB-AT-028/029 acceptance criteria to account for current nanobrag_torch behavior

**Rationale**:
- If the 11% F_latt amplitude is **intentional** (e.g., physics approximation, performance trade-off), then DB-AT-028/029 gates encode unrealistic expectations
- Exit criteria currently require: chi²/pixel initial ≤ 1e2, median ROI correlation before ≥ 0.2
- Current results: chi²≈2.1e5, ROI corr≈-0.05 (both fail by wide margins)

**Deliverables**:
- Revise DB-AT-028/029 acceptance thresholds
- Document physics justification for relaxed criteria
- Update spec-db-core.md §§20-40 if calibration contracts change

**Risk**: May mask real bugs or hide physics inaccuracies

### Option C: Harness-Grade Diagnostic Initiative

**Scope**: Create a **new** architecture/harness initiative outside plan-local constraints

**Approach**:
- Promote sincg diagnostic instrumentation to a first-class harness tool (under `dbex/tools/` or `tests/architecture/`)
- Build reference sincg implementation for validation
- Create comprehensive lattice-factor test suite
- May require temporary Environment Freeze exception to patch `nanobrag_torch`

**Deliverables**:
- Architecture enforcement test: `tests/architecture/test_nanobrag_sincg_reference_parity.py`
- Diagnostic tool: `dbex/tools/sincg_validator.py` (not plan-local)
- Patch: `patches/sincg_instrumentation.patch` + environment tag

**Benefit**: Preserves PROBE-FREEZE-001 policy while enabling deeper investigation

## Cross-References to C.34-C.39 Evidence

- **C.34**: `reports/2026-01-05T150000Z/square_lattice_scaling.{json,md}` — per-subpixel payload showing 0/169 samples in sincg lobe
- **C.35**: `reports/2026-01-08T010000Z/` — oversample normalization fix (169× dilution removed, but 58.5% deficit remained)
- **C.36**: `reports/2026-01-08T150000Z/` — subpixel offset telemetry (detector-plane centering confirmed)
- **C.37**: Planned HKL projection audit (not executed; blocked by C.39 rejection)
- **C.38**: `reports/2026-01-10T150000Z/` — oversample=1 achieves 0.0005% error, proving sincg/HKL/beam are correct when oversample is disabled
- **C.39**: `reports/2026-01-13T010000Z/` — omega hypothesis rejected; deficit appears before omega application

## Recommended Next Steps

1. **Immediate**: Supervisor review of this BLOCKED.md to select Option A, B, or C
2. **If Option A**: Draft maintainer request with evidence summary + minimal reproducer
3. **If Option B**: Open spec_change initiative to revise DB-AT-028/029 gates
4. **If Option C**: Draft harness-grade diagnostic initiative plan (ARCH-SINCG-VALIDATION-001 or similar)

## Artifacts

- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T010000Z/summary.md` — omega diagnosis correction (Ralph's loop)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-11T010000Z/` — C.38 telemetry showing normalized/raw = 1e-6
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T150000Z/` — oversample=1 validation (0.0005% error)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/` — C.35 oversample normalization fix
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/` — C.34 per-subpixel payload

## Physics Context

### Expected Behavior

For a SQUARE lattice with N_cells = (Na, Nb, Nc) = (41, 29, 32):
- Each axis contributes a sincg factor: `F_latt_a = sincg(Δh, Na)`, similarly for b, c
- Total lattice factor: `F_latt = F_latt_a × F_latt_b × F_latt_c`
- When Δh/Δk/Δl are all near zero (Bragg condition): `F_latt ≈ Na × Nb × Nc = 38,048`
- Intensity scales as: `I ∝ |F_cell × F_latt|² ∝ (Na·Nb·Nc)²` for Bragg peaks

### Observed Behavior

- F_latt median ≈ 4206.5 (from oversample>1 runs)
- F_latt max ≈ 38,048 (from oversample=1 runs where Δ≈0 for all samples)
- Ratio: 4206.5 / 38,048 ≈ 0.1106

This suggests the **oversample grid rarely samples near Δ≈0 simultaneously for all three axes**, or there is a systematic undercount in the sincg product.

## Specification Alignment

This blocking condition relates to:
- **docs/spec-db-core.md §§20-40**: Simulator construction and calibration contracts
- **SCALE-009**: Stage A vs reconstruction scaling (owner path lives in nanobrag_torch.simulator)
- **DB-AT-028**: chi²/pixel initial ≤ 1e2 (currently ~2.1e5, FAIL)
- **DB-AT-029**: median ROI correlation before ≥ 0.2 (currently -0.05, FAIL)

The sincg bug prevents ARCH-SIM-CONSTRUCTION-001 from meeting exit criteria #2 and #3, which in turn blocks ARCH-REFACTOR-001 Phase D.3.
