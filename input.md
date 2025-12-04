Summary: Drop the SQUARE-lattice oversample² normalization inside `nanobrag_torch.Simulator.run`, capture the Environment Freeze patch/tag, and rerun the single-pixel probe + partiality architecture test + DB-AT-028/029 so `(N_a·N_b·N_c)^2` parity is restored.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_A_BASELINE_METRICS_PATH=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/db_at_metrics DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k 'DB_AT_028 or DB_AT_029' | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — instrumentation proves SQUARE lattices must not average over oversample²; enforce the new normalization and document the change.
  - SCALE-009 — DB-AT-028/029 chi²/ROI failures are the acceptance selectors we are closing; rerun both selectors with Stage-A baseline metrics captured.
  - PROBE-FREEZE-001 — keep all telemetry inside `nanobrag_torch` + existing probes; no new plan-local scripts.
Pointers:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/summary.md — Do Now + evidence recap.
  - docs/spec-db-core.md:60-140 — Simulator scaling + lattice contracts for SCALE-009.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/square_lattice_scaling.md — HKL tensor telemetry proving the sampling deficit.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator::Simulator.run`; failure class: implementation bug (SQUARE lattice normalization violates SCALE-009 parity contract).
  - docs/architecture/calibration_scaling.md:10-60 — Owner: simulator + reconstruction path; failure class: implementation bug (Stage A/reconstruction rely on the simulator to preserve calibrated scale).
Do Now (hard validity contract)
1. Implement: `/home/ollie/Documents/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — when `crystal.shape == CrystalShape.SQUARE`, drop the `oversample * oversample` factor from `steps`, keep the existing normalization for other shapes, and continue writing `_partiality_stats['steps_scalar']` so probes/tests can assert the scalar. Save the diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`, rebuild/install nanobrag_torch (`python -m pip install -e src/nanobrag-torch --no-deps`), and log the rebuild/tag (`nanobrag-partiality-2026-01-08`) under `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/environment_tag.md` per CLAUDE.md.
2. Implement: `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — ensure the test inspects `_partiality_stats['steps_scalar']` (cpu + cuda legs) and asserts it equals `sources * phi_steps * mosaic_domains` for SQUARE lattices. This guards the new normalization while still checking the `(N_a·N_b·N_c)^2` ratio. Update `docs/findings.md::SIM-CONSTR-PARTIALITY-001` with the normalization rationale.
3. Validation: rerun the single-pixel probe, the architecture partiality test, and DB-AT-028/029 with Stage-A baseline metrics enabled, teeing logs into `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/`. Expect `(41·29·32)^2` parity within ≤1% and DB-AT chi²/ROI metrics to improve dramatically.
Forbidden This Loop:
  - no new plan-local diagnostic scripts
  - do not modify simulator physics beyond the SQUARE normalization change
  - no DB-AT selector skips (rerun both 028/029 as mapped)
DMI Section:
  - Independent Reference: `(N_a·N_b·N_c)^2` lattice scaling from docs/spec-db-core.md §4 and DB-AT-028/029 telemetry.
  - Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_scaling.md`, `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.md`, `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/square_lattice_scaling.md`, `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/stage_a_baseline_probe_baseline.json`, `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/spot_profile_summary.md` (≥5 entries showing Stage A vs reference ratios).
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run`, `_compute_physics_for_position`; `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`.
  - Consumption-State Measurements: `_partiality_stats['steps_scalar']`, `square_lattice_scaling.{json,md}`, `pytest_partiality.log`, DB-AT-028/029 metrics, Stage-A baseline metrics JSON.
  - Boundary Bisection Step: switch from instrumentation to normalization patch; success is measured at the single-pixel probe boundary plus DB-AT selectors.
  - Probe Budget: reuse existing probe + architecture test only (no new probes or scripts).
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z
  - Apply the simulator + test edits; save `patches/square_lattice_steps_fix.patch`
  - python -m pip install -e src/nanobrag-torch --no-deps | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/pip_rebuild.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_A_BASELINE_METRICS_PATH=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/db_at_metrics DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k 'DB_AT_028 or DB_AT_029' | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/pytest_db_at_028_029.log
Pitfalls To Avoid:
  - Do not touch non-SQUARE lattice paths; only drop oversample² for CrystalShape.SQUARE.
  - Keep all telemetry inside nanobrag_torch hooks; no new probe scripts (PROBE-FREEZE-001).
  - Capture the patch + rebuild commands; Environment Freeze compliance is mandatory.
  - Ensure `_partiality_stats['steps_scalar']` stays populated for trace_pixel runs (tests assert this).
  - DB-AT selectors must run with Stage-A baseline metrics enabled so SCALE-009 evidence is updated.
If Blocked: Document the blocker in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/summary.md`, update docs/fix_plan.md + galph_memory.md with the failure reason, and open a spec_change or harness initiative if normalization cannot restore `(N_a·N_b·N_c)^2` parity.
Doc Sync Plan (Conditional): none — reusing existing selectors/tests.
