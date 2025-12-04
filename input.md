Summary: Fix nanobrag_torch SQUARE lattice normalization so oversample grids no longer divide away the single subpixel that carries the (Na·Nb·Nc)^2 lattice weight.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: patch_ready
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/pytest_partiality.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Square-lattice sincg must deliver `(Na·Nb·Nc)^2`; update the finding once normalization lands.
  - SCALE-009 — Reconstruction parity requires simulator outputs to preserve Stage-A lattice scaling; cite when describing chi² gates.
  - PROBE-FREEZE-001 — No new plan-local probes; rely on owner instrumentation + existing probe binaries only.
Pointers:
  - docs/spec-db-core.md:60-140 — Normative simulator contracts for calibration/scaling and Stage-A acceptance gates.
  - docs/architecture/calibration_scaling.md:1-80 — Spot-scale threading and simulator normalization policy referenced by SCALE-009.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:420-470 — Phase C.33–C.35 history + new normalization plan.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.md — Coverage evidence (0/169 subpixels in sincg lobe).
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/summary.md — Current loop plan and validation checklist.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug (lattice weighting loses `(Na·Nb·Nc)^2`).
  - docs/architecture/calibration_scaling.md:10-40 — Owner: `dbex/refinement/reconstruction` + simulator factory; failure class: implementation bug (normalization violates SCALE-009).
Do Now (hard validity contract)
1. Implement: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` — compute `steps = sources * phi_steps * mosaic_domains` whenever `self.crystal.config.shape == CrystalShape.SQUARE`; keep the legacy `* oversample * oversample` factor for GAUSS/TOPHAT/ROUND. Emit the scalar through `_partiality_stats['steps_scalar']` when the debug hook is enabled so probes and architecture tests can assert it.
2. Implement: `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` — extend the test to read `_partiality_stats['steps_scalar']` from the probe outputs, assert `(Na·Nb·Nc)^2` scaling on cpu/cuda, and fail if the normalization still includes `oversample²` in SQUARE mode. Keep the existing ratio check but tighten tolerances once the fix lands.
3. Environment Freeze compliance — capture the simulator diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`, record rebuild/tag commands in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/environment_tag.md`, and append a note to `docs/findings.md::SIM-CONSTR-PARTIALITY-001` describing the normalization change and tag name.
4. Validation — rerun the mapped single-pixel probe, the partiality architecture test, and DB-AT-028/029 with artifacts/logs rooted at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z/`. Expect the probe + enforcement test to report `(Na·Nb·Nc)^2` within ≤1%, and the DB-AT chi²/ROI metrics to drop sharply toward spec.
Forbidden This Loop:
  - no new plan-local diagnostic scripts (probe inventory is frozen)
  - do not edit simulator kernels outside the SQUARE normalization path
  - no speculative instrumentation beyond `_partiality_stats['steps_scalar']`
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z && export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
  - After editing simulator.py and the architecture test, run the probe/pytest commands above, teeing stdout into the artifacts directory.
  - Save the simulator diff via `git -C /home/ollie/Documents/diffbragg_example_2/diffbragg_example diff src/nanobrag-torch/src/nanobrag_torch/simulator.py tests/architecture/test_nanobrag_partiality.py > plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch` and record rebuild/tag instructions in `patches/environment_tag.md`.
Pitfalls To Avoid:
  - Do not change normalization for GAUSS/TOPHAT/ROUND shapes; only SQUARE drops `oversample²`.
  - Keep `_partiality_stats` tensors detached/cpu to avoid torch.compile graph churn.
  - Remember PROBE-FREEZE-001: extend existing probe only; no new scripts under `plans/active/**/bin`.
  - Respect Environment Freeze — every simulator edit needs a patch file + environment tag + findings note.
  - Ensure DB-AT artifact dirs are unique; otherwise fixtures overwrite evidence.
If Blocked: Document the cause in this loop’s summary plus `docs/fix_plan.md` Attempts History, keep DecisionStatus=localized, and escalate to spec_change or new architecture initiative if `(Na·Nb·Nc)^2` parity still cannot be restored without reworking the kernel.
DMI Section:
  - Independent Reference: Single-pixel analytic `(Na·Nb·Nc)^2` scaling (spec-db-core §4.3) + Stage-A acceptance tests (DB-AT-028/029).
  - Transformation Ledger: `square_lattice_scaling.md` rows (coverage %, observed ratio, expected ratio) + `db_at_028/db_at_028_metrics.json` chi²/corr fields.
  - Source Trace Anchors: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py:1050-1200`, `tests/architecture/test_nanobrag_partiality.py`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`.
  - Consumption-State Measurements: min/max `Δh, Δk, Δl`, `_partiality_stats['steps_scalar']`, single-pixel observed ratio, DB-AT chi²/ROI stats (artifacts under this loop’s directory).
  - Boundary Bisection Step: Confirm `(Na·Nb·Nc)^2` parity after normalization change; if still low, escalate to spec_change or revisit lattice kernel math.
  - Probe Budget: 2 (Stage-A baseline helper + single-pixel probe); no new scripts permitted.
