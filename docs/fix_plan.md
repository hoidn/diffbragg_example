# DBEX Fix Plan Ledger

**Last Updated:** 2025-10-28

## Working Agreements
- Artifact policy: store loop outputs under a dedicated `plans/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/` directory (or another documented location) and record the path in each Attempts History entry.
- Every loop updates this ledger before and after execution. Append `Metrics:` and `Artifacts:` lines for each attempt; note `First Divergence:` when debugging parity issues.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.

---

## Active Initiatives

### [TORCH-BRIDGE-001] Bridge DataLoad to `nanobrag_torch`
- Depends on: plans/nanobrag_integration_plan.md §Phase 1
- Status: in_progress
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. Helper returns background-subtracted targets, trusted/background masks, and per-panel slices aligned to `[panel, slow, fast]` (`docs/spec-db-core.md:24`).
  2. Detector/beam/crystal configs hydrate the torch simulator per `docs/config_crosswalk.md:1` and `docs/dxtbx_api.md:1`.
  3. Bridge raises when pixel pitch is not square (`docs/spec-db-core.md:43`).
  4. Smoke harness exercises one DIALS experiment; artifacts recorded with ROI triptych.
- Working Plan: plans/active/TORCH-BRIDGE-001/implementation.md
- Attempts History:
  * 2025-10-28T205500Z — Loop planning kickoff for Phase A scaffolding. Metrics: pending. Artifacts: pending.
  * 2025-10-28T222910Z — Supervisor planning pass to scope Phase A tests + helper implementation; validated outstanding bridge gaps. Metrics: pending. Artifacts: {lys_nitr_10_6_0001.cbf, lys_nitr_10_6_0002.cbf, lys_nitr_10_6_0003.cbf, refGeom.expt, scaled.mtz, stills_proc.phil}
  * 2025-10-28T222910Z — Implemented Phase A (A1+A2) bridge helper with RefinementInputs dataclass and prepare_refinement_inputs function; authored 4 tests (tensor contract, mask polarity, pixel pitch guard, tuple mask input); all tests pass. Metrics: 4/4 tests passed, 0.12s runtime, CPU. Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T222910Z/{do-now-notes.md,pytest.log}. First Divergence: n/a. Next Actions: Phase B config hydration (DetectorConfig, BeamConfig, CrystalConfig mapping from dxtbx); Phase C smoke harness (single-experiment flow with stitched Bragg tensor and ROI triptych).
  * 2025-10-28T224846Z — Supervisor planning for Phase B hydration (Detector/Beam/Crystal configs); confirmed no config helpers/tests exist yet and spec references remain current. Metrics: pending. Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/.
  * 2025-10-28T224846Z — Implemented Phase B (B1+B2) config hydration with DetectorConfig, BeamConfig, CrystalConfig stubs and 3 helper functions (create_detector_config, create_beam_config, create_crystal_config); authored 14 tests covering beam center swap, sample→source vector, CUSTOM convention, mask float conversion, polarization fallback, MOSFLM A* injection, stills defaults; all tests pass. Metrics: 18/18 tests passed (4 Phase A + 14 Phase B), 0.18s runtime, CPU. Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/{do-now-notes.md,pytest.log,pytest_full.log,config_snapshots.json}. First Divergence: n/a. Next Actions: Phase C smoke harness (single-experiment flow with nanobrag_torch simulator, stitched Bragg tensor, ROI triptych artifact); update docs/findings.md if new durable lessons discovered.
  * 2025-10-28T230500Z — Supervisor planning for Phase C smoke harness; verified no existing ROI triptych artifacts under plans/active/TORCH-BRIDGE-001/reports/ and noted nanobrag_torch import remains stubbed pending install. Metrics: pending. Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/.

### [TORCH-RUNTIME-002] Author torch runtime checklist + testing harness seed
- Depends on: TORCH-BRIDGE-001
- Status: pending
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `docs/TESTING_GUIDE.md` documents smoke/acceptance commands and environment flags (e.g., `KMP_DUPLICATE_LIB_OK=TRUE`).
  2. Minimal pytest selector (or placeholder) captured for DB-AT parity suites (`docs/spec-db-conformance.md:25`).
  3. Artifact example captured under the initiative’s documented reports directory.
  4. Ledger entry includes Metrics/Artifacts lines referencing the recorded selector run or TODO.
- Working Plan: plans/active/TORCH-RUNTIME-002/implementation.md
- Attempts History:
  * _(pending)_

### [TORCH-CLI-003] Wire torch backend flag into CLI
- Depends on: TORCH-BRIDGE-001
- Status: pending
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `dbex.refine_one` accepts `--backend {diffbragg,nanobrag}` with default `diffbragg`.
  2. Torch branch emits `Bragg` tensor and diagnostics matching legacy layout (`plans/nanobrag_integration_plan.md` §Phase 4).
  3. Update `docs/index.md` entry for CLI to reflect backend flag.
  4. Entry validated by running torch CLI smoke (documented in `docs/TESTING_GUIDE.md`).
- Working Plan: plans/active/TORCH-CLI-003/implementation.md
- Attempts History:
  * _(pending)_

### [DOC-HARDEN-001] Harden key docs with prescriptive guardrails
- Depends on: none
- Status: done
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. Review `docs/architecture.md` and `docs/development/testing_strategy.md`.
  2. Add new sections titled "Common Pitfalls" or "Architectural Anti-Patterns" to each.
  3. Populate these sections with at least two concrete examples of failure modes observed during `nanobrag_torch` integration (e.g., ADU↔photons unit mismatch, device/dtype neutrality violations, `[panel, slow, fast]` vs dxtbx `(fast, slow)` ordering).
- Attempts History:
  * 2025-10-28: Added "Common Pitfalls" to `docs/architecture.md` (§13) and `docs/development/testing_strategy.md` (§1.6). Metrics: n/a; Artifacts: n/a.

---

## Backlog
- Populate parity harness specs from `docs/spec-db-conformance.md` once torch backend stabilizes.
- Extend Findings ledger with lessons from `reports/` once torch experiments begin.
### [DOC-RUNTIME-004] Restore `docs/pytorch_runtime_checklist.md`
- Depends on: none
- Status: pending
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `docs/pytorch_runtime_checklist.md` resolves to a valid file (symlink or local copy) and can be opened without build errors.
  2. Runtime guardrails referenced by the checklist remain aligned with `docs/spec-db-conformance.md` and `docs/architecture.md` guidance.
  3. `docs/index.md` and `docs/prompt_sources_map.json` reference the restored checklist path.
- Attempts History:
  * _(pending)_
