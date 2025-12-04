Summary: Center the MOSFLM auto beam-center defaults so SQUARE lattice sampling actually hits the Bragg manifold and the `(Na·Nb·Nc)^2` ratio recovers.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/pytest_partiality.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — lattice normalization + telemetry lives in the owner API; keep evidence inside `nanobrag_torch`.
  - PROBE-FREEZE-001 — no new plan-local probes; reuse the sanctioned probe + architecture test only.
  - CONFIG-001 — detector/beam-center mapping must follow the documented conventions (docs/config_crosswalk.md).
Pointers:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-09T010000Z/square_lattice_scaling.md — k/l deltas stay at 0.053846 and coverage remains 0 %, proving the beam center is mis-specified.
  - nanobrag_torch/config.py#L300-L360 — MOSFLM/DENZO auto beam-center defaults currently compute `(detsize + pixel)/2`, which pushes the beam 1.5 px off center before the +0.5 mapping offset.
  - docs/architecture/detector.md — beam-center conventions and MOSFLM mapping (Fbeam = Ybeam + 0.5·pixel, etc.).
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug (SQUARE lattice still violates SCALE-009 parity gates).
  - docs/architecture/detector.md §Beam center mapping — Owner: `nanobrag_torch.config.DetectorConfig`; failure class: implementation bug (auto beam centers violate documented alignment, so downstream physics never sees Δ≈0).
Do Now (hard validity contract)
Implement:
  - `nanobrag_torch/config.py::DetectorConfig.__post_init__` — for MOSFLM and DENZO auto defaults (beam_center_source="auto"), replace `(detsize + pixel)/2` with `(detsize - pixel)/2` so that, after the mandatory +0.5 pixel mapping in `Detector.__init__`, the final `Sbeam/Fbeam` land at `n/2` pixels (mid-plane). Update the inline comments to spell out the before/after math and why this centers any detector, including 1×1 shims.
  - Ensure both slow and fast axes follow the new formula, leave ADXV/DIALS/XDS paths untouched, and keep explicit beam centers honoring user input.
Validation:
  - Rerun the square-lattice probe command above (captures `min_abs_delta_{h,k,l}` plus the `(Na·Nb·Nc)^2` ratio under the fresh timestamp).
  - Rerun `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1` so the enforcement test proves the ratio gate is back within the 1 % tolerance.
Forbidden This Loop:
  - no new probes
  - do not extend plan-local diagnostic scripts beyond the existing probe entry point
DMI Section:
  - Independent Reference: SCALE-009 lattice contract in docs/spec-db-core.md + DB-AT-028/029 telemetry (Stage A magnitudes already obey the spec once simulator parity holds).
  - Transformation Ledger: probe summaries from `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/`, `.../2026-01-05T150000Z/`, `.../2026-01-08T150000Z/`, and `.../2026-01-09T010000Z/` (ratio + min_abs_delta evidence).
  - Source Trace Anchors: `nanobrag_torch/config.py::DetectorConfig.__post_init__` (auto beam-center math) and `nanobrag_torch/models/detector.py::_calculate_pix0_vector` (F/S-beam usage).
  - Consumption-State Measurements: `min_abs_delta_{h,k,l}`, `_partiality_stats['steps_scalar']`, probe ratio, pytest logs.
  - Boundary Bisection Step: After centering the beam, re-examine `min_abs_delta_{k,l}`; if they still exceed 1/N, escalate to simulator physics, otherwise mark parity restored.
  - Probe Budget: unchanged (reuse sanctioned probe + architecture test only).
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/pytest_partiality.log
Pitfalls To Avoid:
  - Keep the beam-center change strictly scoped to MOSFLM/DENZO auto defaults; explicit values and other conventions must remain untouched.
  - Do not tweak simulator physics or add new debug knobs in this loop (probe budget already spent).
  - Ensure both axes use identical logic so the detector stays square.
  - Update comments so future loops understand how the +0.5 mapping composes with the new defaults.
  - Capture artifacts under the new timestamp; no stray files under repo root.
If Blocked: document the failure in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/summary.md`, update docs/fix_plan.md + galph_memory.md, and be ready to escalate toward simulator math if min_abs_delta still exceeds 1/N after the centering patch.
Doc Sync Plan (Conditional): none — no new selectors.
