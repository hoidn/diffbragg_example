# DBEX Fix Plan Ledger

**Last Updated:** 2025-10-28

## Working Agreements
- Artifact policy: store loop outputs under `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/` and record the path in each Attempts History entry.
- Every loop updates this ledger before and after execution. Append `Metrics:` and `Artifacts:` lines for each attempt; note `First Divergence:` when debugging parity issues.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.

---

## Active Initiatives

### [TORCH-BRIDGE-001] Bridge DataLoad to `nanobrag_torch`
- Depends on: plans/nanobrag_integration_plan.md §Phase 1
- Status: pending
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. Helper returns background-subtracted targets, trusted/background masks, and per-panel slices aligned to `[panel, slow, fast]` (`docs/spec-db-core.md:24`).
  2. Detector/beam/crystal configs hydrate the torch simulator per `docs/config_crosswalk.md:1` and `docs/dxtbx_api.md:1`.
  3. Bridge raises when pixel pitch is not square (`docs/spec-db-core.md:43`).
  4. Smoke harness exercises one DIALS experiment; artifacts recorded with ROI triptych.
- Artifact Hub: `plans/active/TORCH-BRIDGE-001/`
- Attempts History:
  * _(pending)_

### [TORCH-RUNTIME-002] Author torch runtime checklist + testing harness seed
- Depends on: TORCH-BRIDGE-001
- Status: pending
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `docs/TESTING_GUIDE.md` documents smoke/acceptance commands and environment flags (e.g., `KMP_DUPLICATE_LIB_OK=TRUE`).
  2. Minimal pytest selector (or placeholder) captured for DB-AT parity suites (`docs/spec-db-conformance.md:25`).
  3. Artifact example written to `plans/active/TORCH-RUNTIME-002/reports/<timestamp>/runtime_smoke.md`.
  4. Ledger entry includes Metrics/Artifacts lines referencing the recorded selector run or TODO.
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
- Attempts History:
  * _(pending)_

---

## Backlog
- Populate parity harness specs from `docs/spec-db-conformance.md` once torch backend stabilizes.
- Extend Findings ledger with lessons from `reports/` once torch experiments begin.

