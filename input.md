Summary: Audit the HKL projection inside `_compute_physics_for_position` by logging the traced pixel’s scattering vector and a dual-basis solve so we can prove whether k/l stay ~0.05 away from integers because of a projection bug rather than detector-plane offsets.
Mode: Parity
ActionType: parity_localization
DecisionStatus: exploring
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — SQUARE lattice sincg must emit `(N_a·N_b·N_c)^2`; new telemetry stays inside `_partiality_stats`.
  - SCALE-009 — DB-AT-028/029 remain the acceptance selectors; simulator magnitude parity is still due.
  - PROBE-FREEZE-001 — all visibility flows through owner instrumentation (no new plan-local scripts).
Pointers:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/square_lattice_scaling.md — detector-plane offsets now span [-6/13,+6/13] yet k/l remain ≥0.0538 from integers.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/summary.md — Phase C.36 conclusions + rationale for auditing HKL projection next.
  - docs/spec-db-core.md:60-140 — SCALE-009 lattice contract (owner API + acceptance gates).
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug (HKL projection/weighting still violates SCALE-009).
  - docs/architecture/calibration_scaling.md:10-60 — Owner: simulator/reconstruction scaling path; failure class: implementation bug (Stage A/reconstruction depend on simulator parity).
Do Now (hard validity contract)
1. Implement: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` — when both `collect_partiality_stats` and `trace_pixel` are enabled, log (a) the traced pixel’s raw scattering vector (`trace_scattering_vector`, Å⁻¹), (b) the dot products with the rotated reciprocal basis currently used for `h/k/l`, and (c) an alternate HKL solve via the dual-basis matrix (stack `rot_*_star` columns, run `torch.linalg.solve`, and stash `trace_h_dual`, `trace_k_dual`, `trace_l_dual`). Keep everything behind the debug flag so production runs are untouched.
2. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — ingest the new telemetry, compute per-axis deltas between the production HKL and the dual-basis solve (min/median/max, signed offsets), and include them in both JSON + Markdown reports plus a console block so we can immediately see whether the alternate projection lands near integers.
3. Validation: Re-run the single-pixel probe (command above) and the partiality architecture test (`pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1`). No DB-AT reruns until the HKL audit lands.
DMI Section:
  - Independent Reference: `(N_a·N_b·N_c)^2` lattice scaling per docs/spec-db-core.md plus DB-AT-028/029 telemetry (Stage A magnitude gates).
  - Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_scaling.md`, `.../2026-01-05T150000Z/square_lattice_scaling.md`, `.../2026-01-07T150000Z/square_lattice_scaling.md`, `.../2026-01-08T010000Z/pytest_partiality.log`, `.../2026-01-08T150000Z/square_lattice_scaling.md`.
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run/_compute_physics_for_position` (HKL projection + sincg), `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` (owner probe).
  - Consumption-State Measurements: `_partiality_stats['steps_scalar']`, `min_abs_delta_{h,k,l}`, new `trace_scattering_vector` + dual-basis HKL deltas, probe ratio, architecture-test ratio.
  - Boundary Bisection Step: Compare production HKL to the dual-basis solve; if the alternate projection hits integers, patch `_compute_physics_for_position`; if not, escalate (oversample/spec-change).
  - Probe Budget: reusing existing probe + architecture test only (0 additional probes consumed).
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/pytest_partiality.log
Pitfalls To Avoid:
  - Keep all new tensors behind `collect_partiality_stats`/`trace_pixel`; production Stage A/B/C paths must not pay for this instrumentation.
  - No new plan-local diagnostic scripts (PROBE-FREEZE-001 still in force).
  - Do not run DB-AT selectors until HKL evidence is collected; this loop is evidence-only.
  - Move tensors to CPU / `.tolist()` before serializing so artifacts remain JSON-friendly.
  - Document matrix shapes/units so the dual-basis math is auditable; avoid silent dtype/device mismatches.
If Blocked: Capture the issue in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/summary.md`, update docs/fix_plan.md + galph_memory.md, and be ready to escalate to spec_change or harness initiatives if the HKL projection already matches the dual-basis solve yet selectors still fail.
Doc Sync Plan (Conditional): none — no new tests are being added or renamed.
