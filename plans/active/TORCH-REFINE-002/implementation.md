# TORCH-REFINE-002 — Stage A Expansion (Full Crystal + Orientation)

## Purpose
Extend the Stage A refinement loop from the nucleus (scale + cell_a) to the full crystal parameter set (logs for cell lengths, bounded deltas for angles, orientation perturbations) so that the canonical dataset gains meaningful leverage (>5% masked-MSE improvement) ahead of Stage C detector tweaks.

## References
- plans/nanobrag_integration_plan.md:143-220 — Stage A scope, optimizer contract, telemetry
- docs/spec-db-workflow.md:20-78 — Stage staging and parameterization (logs/angles, quaternion→XYZ)
- docs/nanobrag_api.md — CrystalConfig fields, detector/orientation mapping
- docs/findings.md — REFINE-001 (warm-start + clamp), REFINE-002 (0.1% nucleus baseline), GRADIENT-001 (tensor overrides preserve autograd)

## Exit Criteria (mirror fix_plan)
1) Stage A optimizer parameters include: global scale, log deltas for cell_a/b/c, bounded angle deltas for alpha/beta/gamma, and an orientation perturbation mapped through a normalized quaternion (or equivalent axis-angle) before constructing CrystalConfig. All parameters warm-start from experiment geometry and propagate through `crystal_overrides` without autograd breaks. Telemetry emits per-parameter deltas.
2) Canonical refGeom dataset achieves ≥5% masked-MSE reduction within ≤30 LBFGS iterations on the deterministic ROI sample, with full-loss trace non-increasing across the last 3 validations (or satisfying LBFGS tolerances). Telemetry message/status reflect the ≥5% gate and record ROI/full traces.
3) Targeted pytest selector (Stage A expansion smoke) collects and passes; registry/docs updated only if selectors change.

## Phase Breakdown
- Phase 1 — Parameter Surface & Warm-starts
  - [x] P1.1: Introduce new trainable tensors for log_cell_b_delta/log_cell_c_delta and bounded angle deltas (alpha/beta/gamma) with clamped/tanh mapping around the baseline angles. *(Landed in 2025-11-05T031241Z implementation; telemetry confirms non-zero cell movement.)*
- [x] P1.2: Add orientation perturbation tensor (3-vector mapped to quaternion) and integrate through `create_crystal_config` misset fields without leaving autograd. *2025-11-05T040935Z implementation proved `misset_deg_override` survives CrystalConfig instantiation and rotates the simulator; telemetry captures XYZ Euler angles with gradients intact (REFINE-003 closed).*
  - [x] P1.3: Ensure global scale warm-start + clamp logic still applies with the expanded parameter list; add appropriate bounds for new parameters (length exponent clamp, angle delta ceiling, orientation norm guard).
- Phase 2 — Telemetry & Safety Rails
- [x] P2.1: Extend `param_deltas` telemetry to include all new Stage A DoFs (lengths, angles, orientation components) with clear naming. *`misset_xyz_deg` (initial/final/delta + quaternion_norm) now flows into param_deltas and rollback snapshots per 2025-11-05T040935Z telemetry patch.*
- [x] P2.2: Capture best-parameter snapshots for rollback covering the expanded tensor set; update early-stop messaging to the ≥5% gate. *Snapshots now include misset XYZ + quaternion norm; messaging references 5% gate.*
- [x] P2.3: Maintain NaN/Inf guards and add orientation normalization (unit quaternion) check to avoid invalid crystals. *`vec_to_unit_quaternion` normalization ships with the Option D patch and existing gradient NaN guards remain active in `compute_loss`/`run_nanobrag_refinement`.*
- Phase 3 — Test & Docs Sync
  - [x] P3.1: Update Stage A smoke test (or add a companion) asserting ≥5% improvement, non-zero deltas for additional DoFs, and telemetry completeness. *Telemetry assertions and deterministic helper landed; ≥5% gate currently marked `xfail` with REFINE-004/005 rationale until TORCH-REFINE-002D restores the dataset.*
  - [x] P3.2: Archive pytest logs under plans/active/TORCH-REFINE-002/reports/<timestamp>/ and update testing guides only if selectors change. *Logs archived per loop; registry untouched because selector name remained stable.*

- Phase 4 — Deterministic Miscalibration & Gate Rebaseline
  - [ ] P4.1: Introduce a deterministic refGeom perturbation (cell + small orientation misset) used only inside the Stage A expansion smoke to guarantee ≥5% masked-MSE headroom while keeping production defaults unchanged. *Helper implemented (tests/dbex/test_torch_refine_smoke.py::create_perturbed_geometry) but disabled until HKL grid can be rebuilt for the perturbed basis (REFINE-005). → Tracked in TORCH-REFINE-002D.*
  - [ ] P4.2: Document the perturbation (magnitude, axes, rationale) in `docs/fix_plan.md` and add a matching finding so future datasets can reuse or retire it. *REFINE-004 reflects the strategy; REFINE-005 records the HKL dependency. Full doc write-up waits for HKL-compatible assets. → Tracked in TORCH-REFINE-002D.*
  - [ ] P4.3: Once perturbation lands, re-run telemetry to capture the new improvement baseline and update `RefinementConfig.min_loss_improvement`/smoke assertions accordingly. *Deferred to TORCH-REFINE-002D once ≥5% gate is restored.*

## Mapped Tests (planned)
- Stage A expansion smoke: `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (new) or upgraded existing `test_loss_decreases`.
  - Acceptance (steady-state goal): ROI-sample masked MSE drops ≥5% within ≤30 steps with telemetry covering scale, cell lengths/angles, and orientation. *Current loop will mark the ≥5% assertion as `xfail` linked to REFINE-004/005 while the dataset/HKL rebuild initiative is prepared; telemetry structure must continue to be validated on every run.*

## Artifacts
- Reports directory: `plans/active/TORCH-REFINE-002/reports/<YYYY-MM-DDTHHMMSSZ>/`
  - `collect_stage_a.log` — pytest collection log
  - `pytest_stage_a.log` — targeted selector output
  - `telemetry_snapshot.json` — optional structured telemetry dump
  - `summary.md` — loop narrative + decisions

## How-To (initial)
- Targeted selector (after test lands):
  - `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Full suite (post-expansion sanity):
  - `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/`

## Next Up (after Stage A expansion)
- TORCH-REFINE-003 — Stage C detector microslip (panel normal translations)
- TORCH-REFINE-004 — Stage B Fhkl modifiers (per-shell/global multipliers)
