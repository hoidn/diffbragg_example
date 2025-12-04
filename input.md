Summary: Recenter the oversample grid inside nanobrag_torch's sincg branch so slow/fast/l axes actually sample Δ≈0; prove it by rerunning the single-pixel probe and the partiality enforcement test.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/
Findings Applied (Mandatory):
  - SIM-CONSTR-PARTIALITY-001 — Partiality guard remains red until (Na·Nb·Nc)^2 scaling is restored; cite this when adjusting subpixel offsets.
  - PROBE-FREEZE-001 — Keep evidence in owner probes/tests only; no new plan-local physics scripts.
Pointers:
  - docs/spec-db-core.md:60-140 — square lattice contract and `(Na·Nb·Nc)^2` expectation.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:430-455 — Phase C.32 closure + new C.33 checklist.
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/summary.md — today’s delta_k/delta_l evidence.
ARCH Contracts (mandatory):
  - docs/spec-db-core.md:60-140 — Owner: `nanobrag_torch.simulator.compute_physics_for_position`; failure class: implementation bug (square lattice must scale with `(Na·Nb·Nc)^2`).
  - docs/architecture/calibration_scaling.md:1-80 — Owner: `dbex/refinement/reconstruction`/`nanobrag_bridge` coordinate contract; failure class: implementation bug (pixel/HKL projection misaligned).
Do Now (hard validity contract)
1. Implement: src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position — replace the current `subpixel_offsets` computation (lines ~1100-1135) with the centered formula `offsets = (torch.arange(oversample, device, dtype) - (oversample - 1) / 2.0) / oversample` for both axes so the oversample grid contains a Δ=0 sample on slow and fast dimensions. Preserve device/dtype neutrality.
2. Implement: same function — when `partiality_stats` is enabled, record `min_abs_delta_h`, `min_abs_delta_k`, and `min_abs_delta_l` (float scalars) so owner probes/tests can assert the grid still straddles zero. Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` to display these stats alongside the ratio ledger.
3. Run: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/square_lattice_probe.log (expect `(Na·Nb·Nc)^2` ratio ≥0.99× spec and `min_abs_delta_{h,k,l} < 1e-3`).
4. Run: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/pytest_partiality.log (document pass/fail plus the new min-delta stats).
Forbidden This Loop:
  - no new plan-local probes
  - do not bypass Stage A/mapping telemetry (reuse existing hooks only)
How-To Map:
  - mkdir -p plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z
  - Apply simulator.py edits + instrumentation
  - KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/square_lattice_probe.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/pytest_partiality.log
Pitfalls To Avoid:
  - Don’t skew the oversample grid with +0.5 biases; offsets must be symmetric around zero for both axes.
  - Keep `subpixel_offsets` math device/dtype neutral (torch.arange on simulator.device, dtype=simulator.dtype).
  - Preserve existing behavior for ROUND/GAUSS/TOPHAT shapes.
  - No new plan-level instrumentation outside owner APIs (PROBE-FREEZE-001).
  - Cite SIM-CONSTR-PARTIALITY-001 when summarizing results so the ledger stays coherent.
If Blocked: Document the blocker in summary.md + docs/fix_plan.md, keep `input.md` in parity_localization mode, and capture raw `delta_{h,k,l}` tensors under the artifacts directory so the next loop can continue from the same evidence base.
DMI Section:
  - Independent Reference: Analytic `(Na·Nb·Nc)^2` scaling for square lattice (docs/spec-db-core.md) + single-pixel probe baseline (plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/).
  - Transformation Ledger: Update `square_lattice_scaling.md` with ≥5 rows comparing delta/min_abs stats, production vs reference ratios, and resulting chi²/ROI deltas after the grid fix.
  - Source Trace Anchors: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:1100-1180`, `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`, `tests/architecture/test_nanobrag_partiality.py`.
  - Consumption-State Measurements: Record `min_abs_delta_{h,k,l}`, observed `(Na·Nb·Nc)^2` ratio, enforcement test output, and DB-AT chi²/corr metrics in the new artifact directory.
  - Boundary Bisection Step: Verify oversample centering fixes the earliest shared boundary (single-pixel probe). If ratio is still <0.99×, bisect Detector basis vs HKL projection next.
  - Probe Budget: 2 active probes (Stage A baseline telemetry + single-pixel scaling). Do not author new scripts.
