Summary: Instrument `_compute_physics_for_position` so the per-subpixel HKL tensors used by the lattice kernel are exposed via `_partiality_stats`, then rerun the square-lattice probe + architecture partiality test to reconcile the TRACE_PY vs `_partiality_stats` mismatch.
Mode: Parity
ActionType: parity_localization
DecisionStatus: exploring
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Probe output still shows `(Na·Nb·Nc)^2` collapse; instrumentation must stay inside the owner simulator instead of plan scripts.
  - SCALE-009 — DB-AT-028/029 chi² and ROI corr failures are driven by the same simulator magnitude deficit; cite when summarizing results.
  - PROBE-FREEZE-001 — No new plan-local probes; extend telemetry via production hooks only.
Pointers:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T200000Z/BLOCKED.md — normalization fix validated yet parity still fails; documents the sampling hypothesis.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T010000Z/square_lattice_scaling.md — oversample=41 sweep proving coarse sampling is not the culprit (TRACE_PY vs `_partiality_stats` mismatch).
  - docs/spec-db-core.md:60-140 — Canonical simulator calibration + lattice weighting requirements for SCALE-009.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:400-520 — Phase C.32–C.35 notes that the remaining deficit must be inside `_compute_physics_for_position`.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator._compute_physics_for_position`; failure class: implementation bug (SQUARE lattice weighting not matching SCALE-009 contract).
  - docs/architecture/calibration_scaling.md:10-60 — Owner: simulator factory/reconstruction path; failure class: implementation bug (reconstruction relies on simulator parity).
Do Now (hard validity contract)
1. Implement: `/home/ollie/Documents/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` — when `self.trace_pixel` is set, capture the traced pixel’s per-subpixel `h`, `k`, `l` values, the rounded indices, `delta_{h,k,l}`, and the per-axis lattice responses into `_partiality_stats` (e.g., `trace_h`, `trace_delta_h`, `trace_F_latt_a`). Detach tensors, move them to CPU, and keep them slice-sized so probe scripts/tests can serialize them without exceeding PROBE-FREEZE guardrails.
2. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` — plumb the new `_partiality_stats` entries into the JSON/Markdown report (summaries plus optional `.npy` dumps) so we can compare `_compute_physics_for_position` HKL tensors against the existing TRACE_PY output. Include concise stats (min/median/max) to keep artifacts readable.
3. Validation: rerun the single-pixel probe (oversample=13) and `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, teeing logs into `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/`. Highlight the captured HKL tensors in `summary.md` so the next loop can decide whether to patch the simulator or revisit SCALE-009 specs.
Forbidden This Loop:
  - no new plan-local diagnostic scripts
  - do not modify simulator kernels beyond debug instrumentation (no new physics tweaks yet)
  - no DB-AT reruns until the HKL telemetry lands
DMI Section:
  - Independent Reference: `(Na·Nb·Nc)^2` scaling per docs/spec-db-core.md §4.3 and DB-AT-028/029 acceptance telemetry.
  - Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.md`, `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T010000Z/square_lattice_scaling.md` (oversample sweep), plus the upcoming instrumentation artifacts.
  - Source Trace Anchors: `/home/ollie/Documents/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position`, `_apply_debug_output`; `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`.
  - Consumption-State Measurements: `_partiality_stats['f_latt']`, new `trace_h/trace_delta_h` tensors, `square_lattice_scaling.{json,md}`, `pytest_partiality.log` (failing ratios).
  - Boundary Bisection Step: Instrument `_compute_physics_for_position` to reconcile the HKL tensors used by the physics kernel with TRACE_PY output before attempting another simulator fix.
  - Probe Budget: Existing Stage-A baseline helper + single-pixel probe + architecture test — no new probes.
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z
  - Apply the simulator + probe edits, then:
    * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py ... | tee .../square_lattice_probe.log`
    * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee .../pytest_partiality.log`
  - Summarize the captured HKL tensors + deltas in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/summary.md` for the next decision loop.
Pitfalls To Avoid:
  - Do not reintroduce plan-local math; instrumentation stays inside `nanobrag_torch`.
  - Keep tensors small (single traced pixel) to avoid 400-LOC PROBE-FREEZE violations.
  - Preserve existing debug payload keys (`F_cell`, `f_latt`, etc.) so downstream consumers remain stable.
  - No simulator physics tweaks until the HKL tensors are reconciled.
  - Record any warnings or unexpected NaNs in the summary.
If Blocked: Capture the instrumentation gap in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-07T150000Z/summary.md`, update docs/fix_plan.md with the blocker, and reassess whether SCALE-009 needs a spec_change vs. simulator patch.
