# NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator

## Initiative
- ID: NANOBRAG-BACKEND-002
- Title: Replace CLI torch backend stub with nanobrag_torch simulator
- Owner: Galph/Ralph pairing
- Status: done

## Goals
- Promote `dbex.nanobrag_bridge` helpers to instantiate real `nanobrag_torch` config objects (Detector/Beam/Crystal) without relying on local stubs.
- Replace the Gaussian stub in `dbex.refine_one.run_nanobrag_backend` with an actual `nanobrag_torch` simulation that honors SCALE-001/002 and geometry guardrails.
- Validate the new backend against the canonical DB-AT-001 golden dataset and update parity harness documentation/tests accordingly.

## Phases Overview
- Phase A — Config promotion: Replace bridge stubs with converters that emit `nanobrag_torch.config` dataclasses and model objects, with unit tests covering geometry/polarization guards.
- Phase B — Simulator integration: Invoke `nanobrag_torch.Simulator` per panel, apply post-simulation scaling, and stream stitched tensors through existing ROI scoring/output plumbing.
- Phase C — Parity validation & docs: Wire the backend into parity selectors, refresh documentation/ledger entries, and capture pytest artifacts showing canonical parity success end-to-end.

## Exit Criteria
1. `dbex.nanobrag_bridge` exposes helpers that return `nanobrag_torch.config` objects plus ready-to-run `nanobrag_torch` Detector/Crystal models; stub dataclasses are removed or relegated to test-only paths.
2. `dbex.refine_one.run_nanobrag_backend` generates `Bragg` tensors via `nanobrag_torch` (no Gaussian stub), applies the sqrt(scale_override) guard (SCALE-002), and writes diagnostics identical in structure to the DiffBragg path.
3. A pytest selector (existing or new) verifies that the torch backend reproduces the canonical DB-AT-001 tensors (within tolerance) and remains in the Active state with artifact logs stored under this initiative.
4. Documentation updates (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`, `docs/index.md`) and `docs/fix_plan.md` Attempts History reference the new backend behavior; `pytest --collect-only` logs are archived per TESTING-003.

## Phase A — Config promotion
### Checklist
- [x] A1: Replace stub dataclasses in `dbex.nanobrag_bridge` with thin adapters that construct `nanobrag_torch.config.DetectorConfig`, `.BeamConfig`, and `.CrystalConfig`.
- [x] A2: Implement helpers to build `nanobrag_torch.models.detector.Detector` and `nanobrag_torch.models.crystal.Crystal` (including HKL grid hydration + SCALE-001 enforcement).
- [x] A3: Extend `tests/dbex/test_nanobrag_bridge_configs.py` (or new module) to assert geometry, polarization, and orientation invariants using the real config classes with deterministic fixtures.

### Notes & Risks
- Ensure the analytic Euler inversion (GEOMETRY-002) survives migration to real config types; numerical drift could reintroduce ROI offsets.
- Missing `nanobrag_torch` installs must be recorded as blockers (Environment Freeze); no local wheel building allowed.

## Phase B — Simulator integration
### Checklist
- [x] B1: Update `dbex.refine_one.run_nanobrag_backend` to instantiate nanobrag_torch simulators per panel, reusing post-sim scaling √(spot_scale_override).
- [x] B2: Stream simulator outputs through `_write_torch_outputs`, ensuring artifacts (ROI dumps, metrics) mirror DiffBragg expectations and remain deterministic.
- [x] B3: Add regression tests (e.g., `tests/dbex/test_nanobrag_backend.py`) comparing simulator output against canonical fixtures for at least one panel/ROI.

### Notes & Risks
- Simulator runs may be GPU-intensive; restrict tests to CPU/device-neutral execution (enforce device via env, guard with pytest markers if needed).
- Pay attention to dtype/device conversions; Tensors must land on CPU before NumPy serialization, or parity harness will read garbage.

## Phase C — Parity validation & docs
### Checklist
- [x] C1: Update DB-AT-001 parity selector to exercise the real torch backend (drop xfail once metrics hit thresholds) and capture new artifacts.
- [x] C2: Sync documentation and Fix Plan Attempts History with new backend behavior, including SCALE-002 guard rationale and runtime pitfalls.
- [x] C3: Close initiative once `docs/fix_plan.md` status is `done` and all mapped selectors collect >0 tests (artifact logs archived under this initiative).

### Notes & Risks
- Ensure parity metrics remain within thresholds; if they regress, capture `first_divergence.json` diffs and pause rollout rather than weakening assertions.
- Doc sync must reference new artifact timestamps; stale paths break reproducibility guarantees.
- `tests/dbex/test_db_at_001_parity.py` currently writes parity artifacts to `plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T030000Z/`; next loop needs to bump this to the new NANOBRAG-BACKEND-002 report directory after rerunning the selector.

## Artifacts Index
- Reports root: `plans/active/NANOBRAG-BACKEND-002/reports/`
- Latest run: `2025-11-04T021141Z/`

## Wrap-up Notes (2025-11-23)
- Simulator wiring is being centralized via the unified factory under TORCH-API-ALIGN-001 (Phase B). Backend call sites should migrate to the factory as that work lands; no functional change expected.
- ExperimentModel parity tests exist (param_init="frozen"). They validate that high-level usage matches legacy wiring on fixtures.
- Documentation now prefers submodule imports for Simulator (`from nanobrag_torch.simulator import Simulator`); update examples and helpers accordingly (no code change required here).
