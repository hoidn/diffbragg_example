# Implementation Plan — TORCH-API-ALIGN-001

ID: TORCH-API-ALIGN-001
Title: Adopt ExperimentModel, Unify Simulator Wiring, and DIALS Mapping (no engine changes)
Owner: Unassigned
Spec Owner: docs/nanobrag_api.md
Status: pending

Goals
- Replace duplicate Simulator wiring with a single adapter path; adopt `ExperimentModel` for parity-first forward.
- Standardize on DIALS mapping (beam-center swap + panel-axis rotations) without changing `nanobrag_torch`; optionally support a CUSTOM-override path behind a flag for teams that require explicit −s0.
- Add missing targeted tests (mapping parity, adapter parity, simulator factory) with warm-cache disabled in new tests.

Phases Overview
- Phase A — Tests First (xfail/skip‑guarded): Targeted automation for DIALS mapping parity, unified simulator factory, and ExperimentModel parity, with explicit xfail/skip markers until wiring lands. Use a fixture to set `NANOBRAGG_DISABLE_COMPILE=1` for determinism in new tests.
- Phase B — Wiring: Fix simulator helper, standardize imports, unify duplicate wiring (including refine_one and nanobrag_refinement loops), and add an ExperimentModel adapter behind an explicit flag (default OFF).
- Phase C — Optional CUSTOM Override (dbex only): Add a feature-flagged path to build CUSTOM detectors with `custom_fdet/sdet/odet` from panel axes and `custom_beam_vector=normalize(−s0)`. Validate parity on fixtures; leave default OFF.
- Phase D — Rollout & Parity: Flip adapter default ON, validate broader parity matrix, keep warm‑cache deferred, and decide mid‑term seam (factory via adapter vs adapter via factory).

Exit Criteria
1. Unified simulator factory validates shape/dtype/device and is used by forward helpers (zero‑iter and torch‑grad paths), refine_one, and panel loops in nanobrag_refinement.
2. DIALS mapping parity tests pass on fixtures (panel + stitched), including ROI cropping parity and calibration gates; document that DIALS ignores `custom_beam_vector` in the current engine.
3. ExperimentModel parity tests pass (param_init="frozen") comparing against legacy Simulator wiring on fixtures.
4. Optional CUSTOM-override path is behind a flag (default OFF) with parity evidence recorded; acceptance criteria documented (e.g., tolerances or use-cases where it is allowed).
5. Refactor leaves existing smoke/perf selectors green; new tests force warm‑cache OFF and use `NANOBRAGG_DISABLE_COMPILE=1` in fixtures.
6. Documentation/testing registry reflects new selectors; `pytest --collect-only` logs saved to plan reports.

Compliance Matrix (Mandatory)
- [ ] Spec Constraint: docs/spec-db-workflow.md §7 — Engine Contract remains intact (ordered stages; no hardcoding).
- [ ] Spec Constraint: docs/spec-db-core.md — Variance-weighted loss remains detached and unchanged.
- [ ] Spec Constraint: docs/nanobrag_api.md — DetectorConfig mapping (DIALS), beam center swap, and ExperimentModel parity path adhered to.
- [ ] Fix-Plan Link: docs/fix_plan.md — Add TORCH-API-ALIGN-001 row; reference artifacts per loop.
- [ ] Policy: Environment Freeze — No engine/vendor patches; dbex-only changes documented.
- [ ] Policy: Warm/Cold Cache — Deferred; force OFF only in new parity/adapter tests.

Spec Alignment
- Normative: docs/nanobrag_api.md — Simulator constructor, Detector/Crystal/Beam configs, ExperimentModel interface.
- Key Clauses: DIALS convention mapping, beam center swap (fast, slow)→(s, f), ExperimentModel param_init modes, ROI-only compute behavior.

Phase A — Tests First (xfail/skip‑guarded)
Checklist
- [x] A1: DIALS mapping behavior test — ✓ COMPLETE 2025-11-24T000100Z
  - Construct a minimal dxtbx beam/panel; build DetectorConfig via `create_detector_config` (DIALS). Assert beam-center swap (fast, slow)→(s, f), Euler extraction from panel axes, and end-to-end forward parity on tiny fixtures.
  - Add a documentation/assertion that `custom_beam_vector` is ignored under DIALS in the current engine (expected behavior).
  - Selector: `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity`
- [ ] A2: Unified simulator factory test
  - Implement tests for one‑panel and stitched multi‑panel runs using the new factory; assert identical outputs vs. current paths on tiny fixtures. Mark xfail/skip until B1/B2 land.
  - Cover matrix: with/without `spot_scale_override`; with calibration metadata (`beam_config` + `N_cells`); CPU and CUDA (skip when CUDA unavailable).
  - Selector: `tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes`
- [ ] A3: ExperimentModel parity tests
  - Compare `ExperimentModel(..., param_init="frozen")` outputs to legacy Simulator wiring (per panel and stitched), including ROI cropping parity (cropped DetectorConfig and beam center shift). Use `experiment.set_structure_factors(F_grid, metadata)` to mirror legacy wire‑up.
  - Force `config.enable_stage_a_warm_cache=False` in these tests and set `NANOBRAGG_DISABLE_COMPILE=1` via test fixture.
  - Mark xfail/skip until B3 lands.
  - Selector: `tests/dbex/test_experiment_parity.py::test_parity_small_fixture`
- [ ] A4 (Optional, flagged): CUSTOM override exploratory test
  - Under a dbex feature flag, construct CUSTOM Detector with custom basis from panel axes and `custom_beam_vector=normalize(−s0)`; measure parity deltas on fixtures and record acceptance thresholds/use-cases.
  - Selector: `tests/dbex/test_bridge_custom_override.py::test_custom_override_exploratory`

Phase B — Wiring (unify duplicate wiring)
Checklist
- [x] B1: Fix simulator helper (dbex/refinement/helpers.py) — COMPLETE 2025-11-23T210000Z
  - Standardize on `from nanobrag_torch.simulator import Simulator`
  - Build `nanobrag_torch.models.Detector/Crystal`, attach HKL tensors, then construct `Simulator(detector=..., crystal=..., beam_config=..., device=..., dtype=...)`.
  - Factory responsibilities: accept `beam_config`, `dtype`, `device`; apply `sqrt_spot_scale` post‑run when provided; normalize/validate `mask_array` on device/dtype; preserve calibration gates (e.g., `N_cells`/sample clipping) identical to current code; support ROI-cropped DetectorConfig with beam-center mm shifts.
- [x] B2: Replace duplicate wiring — COMPLETE 2025-11-24T000000Z (B2a forward helpers COMPLETE 2025-11-23T220000Z -56 lines, B2b(i) refine_one CLI COMPLETE 2025-11-23T240000Z -23 lines; B2b(ii) scope clarification: no forward-only panel loops exist in nanobrag_refinement, refinement closures require direct Simulator for autograd)
  - Route `simulate_forward_once`, `simulate_forward_torch`, the refine_one CLI path (dbex/refine_one.py:380+), and panel loops in `dbex/nanobrag_refinement.py` through the factory; prepare incremental diffs with no behavior change.
  - Remove local mask conversions and `sqrt(spot_scale_override)` math from callers after the factory owns them.
- [ ] B3: ExperimentModel adapter
  - Add an adapter path: for each panel (or cropped ROI), construct configs via existing bridge helpers; instantiate `ExperimentModel(..., param_init="frozen")`, attach HKL tensors, call `experiment()`, stitch panels.
  - Behind an explicit adapter flag (default OFF). Adapter is parity‑first; no changes to loss or warm cache semantics. Document the flag name in module docstring and tests use fixtures to inject it (no global module state).
  - Long‑term layering: clarify that the simulator factory is the internal unifier and the adapter is the higher‑level parity path; mid‑term, converge to one public seam (factory via adapter or vice versa).

Phase C — Optional CUSTOM Override (dbex only)
Checklist
- [ ] C1: Add a dbex feature flag (default OFF) to build CUSTOM detectors when requested
  - In bridge/config hydration, when the flag is enabled: set `detector_convention=CUSTOM`; compute `custom_fdet/custom_sdet/custom_odet` from panel axes; set `custom_beam_vector=normalize(−s0)`.
  - Document pivot mode implications (CUSTOM forces SAMPLE pivot); gate usage to teams that accept potential drift relative to DIALS+BEAM mapping.
- [ ] C2: Exploratory parity run on fixtures
  - Run the A4 test selector; record deltas and acceptance thresholds in plan reports.

Phase D — Rollout & Parity (flip adapter ON, decide seam)
Checklist
- [ ] D1: Flip adapter default ON (rollback flag remains for emergency), leave warm‑cache logic unchanged in production.
- [ ] D2: Re-run parity and smoke tests (including existing selectors) and save `--collect-only` logs.
- [ ] D3: Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` with new selectors.
- [ ] D4: Decide mid‑term seam: route the factory through ExperimentModel or vice versa to avoid two public paths; document the decision.
- [ ] D5: Documentation updates
  - Update `docs/nanobrag_api.md` import example to use `from nanobrag_torch.simulator import Simulator` and `from nanobrag_torch.config import ...`.
  - Update `docs/spec-db-workflow.md` Per‑Panel Simulation step to reflect DIALS convention mapping (beam-center swap + panel axes → Euler angles). Note current engine behavior: DIALS ignores `custom_beam_vector`; for explicit −s0, instruct to use CUSTOM with full basis (dbex flag).
  - Record CUSTOM exploratory findings in plan reports and docs/findings.md (no engine patch tag required).

Validation & Artifacts
- Tests/selectors: listed per Phase A.
- Artifacts path: `plans/active/TORCH-API-ALIGN-001/reports/<timestamp>/`

Risks & Mitigations
- API drift risk in ExperimentModel: Mitigate via parity tests and rollback flag.
- Beam direction fidelity: DIALS path does not forward −s0 explicitly; mitigate via mapping parity tests and doc note. CUSTOM override path exists behind a flag for specialized needs.
- Performance: Adapter keeps warm‑cache untouched; tests force cache OFF for determinism. Quantify any overhead in rollout report; defer warm‑cache improvements per “Deferred Work”.

Existing Plan Adjustments (Conflicts/Updates)
- TORCH-BRIDGE-001 (Bridge DataLoad to nanobrag_torch)
  - Update wording in Phase B “Map Detector” to DIALS convention mapping (beam-center swap + Euler extraction). Remove engine patch assumptions; add note about CUSTOM override flag.
- PERF-WARM-SIM-001 (Warm Simulator)
  - Mark as explicitly deferred until after this initiative; note that new parity tests force warm-cache OFF.
- ARCH-REFACTOR-001 (Refinement Engine Modularization & Physics Separation)
  - Incorporate “ExperimentModel adapter” into Phase C incremental migration as a near‑term step (before larger facade clean‑up); add dependency on this initiative.
  - Add dependency on TORCH-API-ALIGN-001 completion for simulator wiring unification.
- NANOBRAG-BACKEND-002 (Torch backend integration)
  - No functional change required; note in Attempts History that simulator wiring is now centralized and that ExperimentModel parity tests are added (documentation-only update).

