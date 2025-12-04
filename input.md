Summary: Instrument the nanobrag_torch SQUARE lattice path so we can explain why a single-pixel simulator run scales by only 8.46e4 instead of (Na·Nb·Nc)^2, and capture the evidence in Phase C.31 before scheduling the production patch.
Mode: Parity
ActionType: debug
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — lattice partiality has a decision-carrying finding; instrumentation and tests must cite this guard while we continue diagnosing the Na·Nb·Nc scaling failure.
Pointers:
  - docs/spec-db-core.md:60-140 — lattice factor contract for SQUARE crystals.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:360-430 — Phase C tasks plus instrumentation history we are extending.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/summary.md — single-pixel probe results showing the 0.000058× scaling deficit.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: nanobrag_torch.simulator.compute_physics_for_position; failure type: implementation bug (SQUARE lattice must emit (Na·Nb·Nc)^2 scaling).
  - tests/architecture/test_nanobrag_partiality.py:1-200 — Owner: architecture enforcement test; failure type: implementation bug (enforcement stays red until the scaling contract passes).
Do Now (hard validity contract)
1. Implement: /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position — when `debug_config['trace_pixel']` or `collect_partiality_stats` are enabled, record `F_cell`, `F_latt`, `(F_cell*F_latt)^2`, and the pre-polar intensity so we can compare the measured ratio against the theoretical `(Na·Nb·Nc)^2` term inside the real kernel (keep the hook opt-in to honor probe-freeze).
2. Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py::main — thread the new debug payload into the probe output (JSON + Markdown) so base vs scaled runs report `F_cell`, `F_latt`, `pre_polar_intensity`, and the derived ratio `(pre_polar)/(F_cell·F_latt)^2` for both cases.
3. Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md — add Phase C.31 notes that describe the instrumentation scope, cite the new report directory, and list the hypotheses this evidence will confirm/refute before we edit production code (mirror the attempt in docs/fix_plan.md so the ledger tracks this evidence loop).
4. Run: collect artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/` by executing the updated probe (`python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir ... --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1`) and rerunning `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`; archive the JSON/MD/logs next to the enforcement failure and summarize the measured ratios in summary.md.
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/pytest_partiality.log
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
      --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z \
      --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 \
      | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/square_lattice_probe.log
Pitfalls To Avoid:
  - Do not create new plan-local probes; reuse the existing square-lattice script and kernel hooks (PROBE-FREEZE-001).
  - Keep instrumentation opt-in so production runs stay unaffected and torch.compile caching remains valid.
  - Avoid editing unrelated phases in docs/fix_plan.md; only add the new Attempts History entry tied to this evidence.
  - Preserve Environment Freeze compliance by limiting edits to the checked-out nanobrag_torch source tree and documenting any future patch files.
  - Keep commits/tests in ASCII and cite spec sections when documenting findings.
  - Capture both stdout and JSON artifacts; missing logs invalidate the ledger.
If Blocked: Record the blocker in summary.md and galph_memory, attach partial logs under the artifact directory, and update docs/fix_plan.md Attempts History explaining why the evidence could not be gathered; do not attempt new probes until the instrumentation path is unblocked.
DMI Section:
  - Independent Reference: Spec contract docs/spec-db-core.md:60-140 (SQUARE lattice) + C-code snippet in simulator.py comments; Stage A baseline and DB-AT-028/029 selectors remain the acceptance references.
  - Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/spot_profile_summary.md` already lists ≥5 ROI rows comparing Stage A telemetry vs |F|²·F_latt²·LP; continue referencing this ledger when adding the new single-pixel stats.
  - Source Trace Anchors: nanobrag_torch/simulator.py:288-382 (SQUARE lattice computation + intensity path), plus probe_square_lattice_scaling.py:1-190 (owner CLI hitting the same code path).
  - Consumption-State Measurements: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/square_lattice_scaling.{json,md}` show base=6.52, scaled=5.52e5, observed ratio=8.46e4 vs expected 1.45e9 (deviation factor 5.8e-5).
  - Boundary Bisection Step: Compare `(pre_polar_intensity)/(F_cell·F_latt)^2` for base vs scaled runs; if the ratio deviates from 1 within compute_physics_for_position, inspect the normalization branch right after `F_total = F_cell * F_latt` to find the missing multiplier before touching Lorentz/polarization code.
  - Probe Budget: 2 active probes for this signature (Stage A baseline script + square_lattice_scaling.py); no new scripts allowed until we attempt the production fix.
