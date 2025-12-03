# [ARCH-SIM-HKL-BOUNDS-001] Stage-A / Mapping HKL Alignment

## Metadata
- **ID**: ARCH-SIM-HKL-BOUNDS-001
- **Title**: Align Stage-A HKL queries with structure-factor grid bounds
- **Owner**: Galph ↔ Ralph
- **Status**: in_progress
- **Type**: architecture
- **Tier**: 0 (unblocks ARCH-SIM-CONSTRUCTION-001 and DB-AT-028/029)
- **Created**: 2025-12-03T150219Z
- **Depends on**: DIAG-NANOBRAGG-OVERSAMPLE-001 (HKL stats evidence)
- **Blocks**: ARCH-SIM-CONSTRUCTION-001, ARCH-REFACTOR-001 Phase D.3, DB-AT-027/028/029

## Problem Statement

DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F confirmed **0/9.4 million** HKL queries fall within
the loaded structure-factor grid bounds for both `simulate_forward_once` and the Stage-A
warm-cache simulators. Mapping fixtures load a grid spanning `h∈[-24,24], k∈[-28,28], l∈[-31,31]`
yet nanobrag_torch consistently queries `h∈[28,47], k∈[28,51], l∈[37,59]`, guaranteeing all
lookups return `default_F=0`. This explains the persistent 10⁴–10⁵× intensity mismatch and
chi²/pixel ≈1.08e5 reported by DB-AT-028/029. Diagnostics eliminated earlier hypotheses
(oversample mutation, beam flux defaults, SI-unit mismatch) and show the root cause is a
**reciprocal-space alignment bug** either in the dxtbx→nanobrag_torch crystal mapping or in the
structure-factor grid indexing conventions. Until HKL indices fall inside the grid envelope,
no reconstruction, Stage-A refinement, or parity selector can converge.

## Spec Alignment

- **docs/spec-db-core.md §§Geometry Mapping & Objective Function** — HKL lookup must be built
  from the same `A*(params)` used to simulate intensities; `default_F` fallbacks are non-conformant.
- **docs/spec-db-workflow.md §Stage A Canonical Initialization** — Zero-parameter Stage-A runs
  SHALL reuse the DB-AT-024 mapping pipeline (same HKL grid/calibration) and reproduce that forward
  stack before enabling parameter deltas.
- **docs/spec-db-conformance.md DB-AT-024/027/028/029** — Mapping parity, Stage-A zero-point, and
  Stage-A sanity tests all depend on correct HKL coverage. The current 0% hit-rate violates the
  conformance acceptance criteria.

## Goals
1. Quantify and eliminate the HKL offset between dxtbx-derived `A*` and nanobrag_torch's reciprocal
   lattice tensors at the Stage-A zero point.
2. Restore ≥99% in-bounds HKL coverage for both `simulate_forward_once` and Stage-A warm caches on
   the canonical refGeom smoke fixtures.
3. Re-run DB-AT-028/029 (small-detector) to confirm chi²/pixel ≤ 1e2 and median ROI correlation ≥ 0.2
   once HKL coverage is fixed.
4. Document the fix via findings + patch artifacts per Environment Freeze exception rules when
   touching `src/nanobrag-torch`.

## Non-Goals
- Stage-B/C HKL interpolation tuning (handled by REFINE-005).
- CUDA vs CPU HKL grid transfer issues (GRADIENT-003 is separate).
- Re-deriving mapping calibration policies (SCALE-00X initiatives cover that space).

## Exit Criteria
1. New analysis script records `max_abs_diff(A*_nanobrag, A*_dxtbx) ≤ 1e-6 Å⁻¹` at the Stage-A zero point
   (mapping assets, zero deltas).
2. HKL stats from both `simulate_forward_once` and `_build_stage_a_context` report `in_bounds_fraction ≥ 0.99`
   on the refGeom small-detector smoke fixture (captured under plan reports).
3. DB-AT-028 and DB-AT-029 pass on small-detector smoke fixture with canonical calibration (chi²/pixel ≤ 1e2,
   median ROI correlation_before ≥ 0.2, no `default_F` warnings in logs).
4. `docs/findings.md` updated with the repair summary and artifact links.
5. `ARCH-SIM-CONSTRUCTION-001` unblocked (chi² magnitude in reconstruction matches Stage A within tolerance).

## Phases

### Phase A — Baseline HKL / A* Gap Measurement
**Objective**: Reproduce the HKL offset numerically and capture the aberrant `A*` alignment.

Tasks:
- [x] A1: Author Tier-2 probe `plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/probe_crystal_hkl_alignment.py`
      that (a) loads the canonical refGeom smoke dataset via `DataLoad`, (b) builds a mapping context
      (`build_mapping_stage_a_context`), (c) instantiates `nanobrag_torch.models.Crystal` from the same
      `CrystalConfig`, and (d) compares the resulting reciprocal lattice columns against `crystal.get_A()`
      from dxtbx. Emit JSON metrics (max/mean absolute differences, per-axis offsets) plus a prose summary.
      **Result (2025-12-03T161200Z)**: `max|ΔA*|=4.44e-09 Å⁻¹` proving A* alignment is correct; HKL miss lies downstream.
- [ ] A2: Extend the probe to optionally reuse the HKL stats instrumentation from DIAG-NANOBRAGG-OVERSAMPLE-001
      so script output links the measured `A*` delta to the observed out-of-bounds ranges.
- [ ] A3: Record artifacts under `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/<timestamp>/` and update
      `docs/findings.md` (DIAG-OVERSAMPLE-001 cross-reference) with the quantified mismatch.

**Validation**: Probe completes on CPU (`NANOBRAGG_DISABLE_COMPILE=1`), writes metrics JSON + summary, and
confirms the HKL offset (expected failure state: >30 index offset with 0% coverage).

### Phase B — Root Cause Isolation & Fix Design
**Objective**: Identify the precise transformation error and define the minimal code changes.

Tasks:
- [ ] B1: Instrument nanobrag_torch’s scattering-vector→HKL projection for specific pixels (beam center and ±offsets)
      by implementing `plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py`. The script shall rebuild
      Detector/Beam/Crystal configs from the mapping fixture, compute diffracted/incident unit vectors, reproduce the
      `_compute_physics_for_position` math for chosen pixels, and emit JSON/summary files showing fractional HKL values,
      rounded indices, and whether each lies within `hkl_metadata` bounds. Priority: confirm the direct-beam pixel
      should yield `(h,k,l)≈(0,0,0)` but currently produces the +30/+40 offset captured by HKL stats.
- [ ] B2: Draft a fix design (preferably localized inside nanobrag_torch) that brings the reciprocal lattice
      back into alignment without regressing existing finding guards (GEOMETRY-003, GEOMETRY-004).
- [ ] B3: Capture the proposed change, environment-freeze compliance steps, and affected modules/tests in
      `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/<timestamp>/design_notes.md`.

**Validation**: Design review notes identify the exact bug locus (e.g., missing 2π factor, incorrect basis order,
MOSFLM injection override) with supporting logs.

### Phase C — Implementation & Validation
**Objective**: Apply the alignment fix, re-enable canonical tests, and propagate telemetry/doc updates.

Tasks:
- [ ] C1: Implement the reciprocal lattice fix (likely inside `nanobrag_torch.models.Crystal` or the bridge
      config factory), saving the patch diff under `plans/active/ARCH-SIM-HKL-BOUNDS-001/patches/` per
      Environment Freeze exception requirements.
- [ ] C2: Update HKL stats probe and DIAG findings with post-fix evidence (≥99% in-bounds, matched ranges).
- [ ] C3: Re-run DB-AT-028/029 (small detector, metadata sigma) and collect artifacts + pytest logs under
      this plan.
- [ ] C4: Update `docs/spec-db-workflow.md` / `docs/TESTING_GUIDE.md` / `docs/findings.md` as needed to
      document the repaired geometry contract.

**Validation**: Exit criteria satisfied; `ARCH-SIM-CONSTRUCTION-001` unblocks and Stage-A chi² matches mapping.

## Abort / Escalation Triggers
- HKL offset traces back to upstream (non-vendored) nanobrag_torch commits that cannot be patched locally →
  escalate via problems.md and halt plan pending maintainer response.
- Fix would require spec changes (e.g., altering DB-AT tolerances) → open spec_change initiative per workflow.
- Probe cannot load canonical fixtures due to missing data → document in `docs/fix_plan.md` and pause until
  assets restored.
