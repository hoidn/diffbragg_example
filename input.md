Summary: Remove the `oversample²` dilution for CrystalShape.SQUARE so the simulator preserves the `(Na·Nb·Nc)^2` lattice gain that DB-AT-028/029 require.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Simulator must preserve `(Na·Nb·Nc)^2` lattice scaling; update the finding with the normalization/tag once the fix lands.
  - SCALE-009 — Reconstruction parity depends on simulator calibration threading; cite when reporting DB-AT chi²/ROI metrics.
  - PROBE-FREEZE-001 — No new plan-local probes; rely on Stage-A telemetry + existing probe binaries only.
Pointers:
  - docs/spec-db-core.md:60-140 — Canonical simulator calibration + lattice-weighting requirements for SCALE-009/DB-AT-028/029.
  - docs/architecture/calibration_scaling.md:1-80 — Architecture contract for when normalization/scaling happen inside the simulator.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:800-870 — Phase C.33–C.35 checklist and normalization rationale.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.md — Coverage table showing `steps_scalar=sources·phi·mosaic·oversample²` despite 0/169 central samples.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/summary.md — Current loop hand-off + validation expectations.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug (lattice normalization violates SCALE-009).
  - docs/architecture/calibration_scaling.md:10-60 — Owner: `dbex/refinement/reconstruction` + simulator factory; failure class: implementation bug (Stage-A acceptance tests depend on preserved `(Na·Nb·Nc)^2`).
Do Now (hard validity contract)
1. Implement: `/home/ollie/Documents/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — when `self.crystal.config.shape == CrystalShape.SQUARE`, compute `steps = sources * phi_steps * mosaic_domains` (drop the `oversample * oversample` factor), keep the legacy normalization for GAUSS/TOPHAT/ROUND, and emit the chosen scalar via `_partiality_stats['steps_scalar']` so probes/tests can assert it.
2. Implement: `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — read `_partiality_stats['steps_scalar']` from the probe outputs, assert `(Na·Nb·Nc)^2` scaling for both cpu/cuda paths with ≤1% tolerance, and fail if the scalar still includes `oversample²` in SQUARE mode.
3. Implement: Environment Freeze bookkeeping — save the simulator diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`, record editable-rebuild/tag commands (`nanobrag-partiality-2026-01-06`) in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/environment_tag.md`, and append the normalization rationale/tag to `docs/findings.md::SIM-CONSTR-PARTIALITY-001`.
4. Validation: rerun the single-pixel probe, the partiality architecture test, and DB-AT-028/029 with artifacts/logs rooted at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/`; expect `(Na·Nb·Nc)^2` parity within ≤1% and sharply improved DB-AT chi²/pixel + ROI corr metrics.
Forbidden This Loop:
  - no new plan-local diagnostic scripts or probe extensions
  - do not touch simulator kernels outside the SQUARE normalization path
  - no speculative instrumentation beyond `_partiality_stats['steps_scalar']`
DMI Section:
  - Independent Reference: analytic `(Na·Nb·Nc)^2` scaling from spec-db-core §4.3 plus DB-AT-028/029 acceptance gates (docs/TESTING_GUIDE.md §5.2).
  - Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.{json,md}` (steps scalar, coverage %, observed vs expected ratios) + `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_probe.log`.
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:950-1250`, `tests/architecture/test_nanobrag_partiality.py`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`.
  - Consumption-State Measurements: `_partiality_stats['steps_scalar']`, min/max `Δh, Δk, Δl`, single-pixel ratio, DB-AT `chi2_initial_per_pixel` and ROI corr from `db_at_{028,029}_metrics.json` under this loop’s artifacts.
  - Boundary Bisection Step: Apply the normalization fix; if `(Na·Nb·Nc)^2` parity still fails, escalate to spec_change or revisit the sincg accumulation math.
  - Probe Budget: 2 (Stage-A baseline helper + single-pixel probe) — both already exist; no additional probes allowed.
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z && export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md before running commands.
  - After editing simulator/test files, rerun the mapped probe/pytest commands above, teeing stdout/stderr into the artifacts directory.
  - Capture the simulator diff + rebuild steps into `patches/square_lattice_steps_fix.patch` and `patches/environment_tag.md`, then update `docs/findings.md` once validation succeeds.
Pitfalls To Avoid:
  - Do not alter GAUSS/TOPHAT/ROUND normalization; only drop `oversample²` for SQUARE lattices.
  - Keep `_partiality_stats` tensors detached/cpu-safe so torch.compile caching is unaffected.
  - Respect PROBE-FREEZE-001 — no new scripts under `plans/active/**/bin` even for quick checks.
  - Ensure DB-AT artifact directories are unique for this timestamp to avoid overwriting prior evidence.
  - Document the environment tag + findings update immediately after rebuilding nanobrag_torch.
If Blocked: Record the blocker in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/summary.md` + `docs/fix_plan.md` Attempts History, keep DecisionStatus=localized, and escalate to a spec_change or new architecture initiative if `(Na·Nb·Nc)^2` parity cannot be restored without redesigning sincg accumulation.
