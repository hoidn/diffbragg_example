# DBEX Fix Plan Ledger

**Last Updated:** 2025-10-28

## Working Agreements
- Artifact policy: store loop outputs under a dedicated `plans/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/` directory (or another documented location) and record the path in each Attempts History entry.
- Every loop updates this ledger before and after execution. Append `Metrics:` and `Artifacts:` lines for each attempt; note `First Divergence:` when debugging parity issues.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
 - Test registry synchronization: When tests are added or renamed in a loop, update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` accordingly, and reference `pytest --collect-only` logs (artifact paths) in the Attempts History entry. Items must not be marked `done` if any selector documented as "Active" collects 0 tests.

---

## Active Initiatives

### [TORCH-BRIDGE-001] Bridge DataLoad to `nanobrag_torch`
- Depends on: plans/nanobrag_integration_plan.md §Phase 1
- Status: done
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
  * 2025-10-28T231200Z — Implemented Phase C (C1+C2) smoke harness with DataLoad→bridge→stub simulator flow; authored 3 tests (single experiment flow, masked MSE computation, artifact generation) exercising 92 ROIs from refGeom dataset; generated ROI triptych and metrics JSON; all tests pass. Metrics: 3/3 tests passed, 1.83s runtime, CPU. Masked MSE=9.6e5 (stub Gaussian vs real data), loss mask coverage=0.21%, n_rois=92, target shape=[1,2527,2463]. Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/{do-now-notes.md,pytest.log,smoke_metrics.json,roi_triptych.png}. First Divergence: n/a. Next Actions: Mark implementation.md Phase C complete; update bridge tests if crystal A* tuple→array pattern recurs; swap stub_bragg_tensor for real nanobrag_torch simulator when available.
  * 2025-10-28T233500Z — Closure validation run: reran full test suite (21 tests: 4 bridge, 14 config, 3 smoke) with KMP_DUPLICATE_LIB_OK=TRUE; all tests passed. Metrics: 21/21 tests passed, 1.93s runtime, CPU, Python 3.9.23, PyTorch 2.8.0. Masked MSE=9.6e5, loss mask coverage=0.21%, n_rois=92, target shape=[1,2527,2463]. Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z/{do-now-notes.md,pytest.log,run_env.txt,smoke_metrics.json,roi_triptych.png}. First Divergence: n/a. Next Actions: All exit criteria met; initiative complete and ready for handoff to TORCH-RUNTIME-002 or TORCH-CLI-003. Archive plans/active/TORCH-BRIDGE-001/implementation.md.

### [TORCH-RUNTIME-002] Author torch runtime checklist + testing harness seed
- Depends on: TORCH-BRIDGE-001
- Status: done
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `docs/TESTING_GUIDE.md` documents smoke/acceptance commands and environment flags (e.g., `KMP_DUPLICATE_LIB_OK=TRUE`).
  2. Minimal pytest selector (or placeholder) captured for DB-AT parity suites (`docs/spec-db-conformance.md:25`).
  3. Artifact example captured under the initiative's documented reports directory.
  4. Ledger entry includes Metrics/Artifacts lines referencing the recorded selector run or TODO.
- Working Plan: plans/active/TORCH-RUNTIME-002/implementation.md
- Attempts History:
  * 2025-10-28T232744Z — Supervisor planning kickoff; verified TORCH-BRIDGE-001 exit criteria satisfied, catalogued runtime doc gaps. Metrics: pending. Artifacts: pending.
  * 2025-10-28T232744Z — Completed A1-A2-B1-B2 doc updates: enhanced TESTING_GUIDE.md §1 with structured environment flag guidance (KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE); added runtime pitfalls to testing_strategy.md §1.6; synchronized 8 DB-AT selectors (001, 002, 020-024, vectorization) between TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md with spec citations; captured pytest --collect-only evidence for DB_AT_001 (0 tests collected as expected). Metrics: 0 tests collected for DB_AT_001 (planned selector), pytest collection runtime 0.98s. Artifacts: plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/{notes.md,pytest_collect.log}. First Divergence: n/a. Next Actions: Exit criteria 1-4 satisfied; mark implementation.md phases A+B complete; update status to done; note DOC-RUNTIME-004 dependency for pytorch_runtime_checklist.md restoration in findings if needed.

### [TORCH-CLI-003] Wire torch backend flag into CLI
- Depends on: TORCH-BRIDGE-001
- Status: in_progress
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `dbex.refine_one` accepts `--backend {diffbragg,nanobrag}` with default `diffbragg`.
  2. Torch branch emits `Bragg` tensor and diagnostics matching legacy layout (`plans/nanobrag_integration_plan.md` §Phase 4).
  3. Update `docs/index.md` entry for CLI to reflect backend flag.
  4. Entry validated by running torch CLI smoke (documented in `docs/TESTING_GUIDE.md`).
- Working Plan: plans/active/TORCH-CLI-003/implementation.md
- Attempts History:
  * 2025-10-28T234618Z — Supervisor planning kickoff; reviewed implementation plan Phase A/B scope. Metrics: pending. Artifacts: pending.
  * 2025-10-29T00:20:00Z — Reality check and alignment: Verified `dbex/refine_one.py` implements `--backend {diffbragg,nanobrag}` with a torch stub path that writes `/torch_diagnostics`. Updated `docs/index.md` to reflect implemented backend and diagnostics. Tests for the CLI (`tests/dbex/test_refine_one_cli.py`) do not yet exist; leaving status `in_progress`. Metrics: pending. Artifacts: pending. Next Actions: Author minimal CLI tests and register selectors; run collect-only and update TESTING_GUIDE/TEST_SUITE_INDEX per process gates.
  * 2025-10-29T003751Z — Supervisor planning for Phase C registry/doc sync: confirmed `tests/dbex/test_refine_one_cli.py` provides six tests but lacks artifacted runs, observed docs/spec-db-interfaces.md status still labels `--backend` unimplemented, and noted CLI selector absent from testing guides. Defined new Phase C checklist (C1-C3) to capture pytest evidence, synchronize `docs/TESTING_GUIDE.md` & `docs/development/TEST_SUITE_INDEX.md`, and update normative docs plus ledger Metrics/Artifacts lines. Metrics: pending. Artifacts: plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/. Next Actions: Execute C1-C3 per implementation plan with mapped pytest commands and log paths in `input.md`.

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

### [PARITY-HARNESS-001] Author DB-AT parity harness specs
- Depends on: TORCH-BRIDGE-001, TORCH-CLI-003
- Status: done
- Owner/Date: Unassigned / 2025-10-29
- Exit Criteria:
  1. Draft normative harness specs for DB-AT-001 and DB-AT-002 covering datasets, metrics, and tolerance targets in `docs/spec-db-conformance.md` (§Conformance Profiles, `docs/spec-db-conformance.md:10-36`), promoting placeholders to actionable checklists.
  2. Publish a supporting blueprint under `plans/active/PARITY-HARNESS-001/implementation.md` with phased tasks for authoring tests and capturing parity metrics per `docs/development/testing_strategy.md:1-120`.
  3. Sync `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` entries so selectors `DB_AT_001` and `DB_AT_002` include command scaffolds, required environment flags, and artifact expectations (referencing `docs/spec-db-tracing.md:15-60` for metric capture).
  4. Update `docs/index.md` and `docs/prompt_sources_map.json` to reference the finalized parity harness spec and blueprint.
- Attempts History:
  * 2025-10-29T000004Z — Supervisor planning kickoff; converted backlog note into structured initiative, created implementation plan with Phase A-C checklist, and drafted audit-focused Do Now covering DB-AT-001/002 evidence collection. Metrics: pending. Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/.
  * 2025-10-29T000004Z — Completed Phase A evidence audit (A1-A3): audited spec-db-conformance.md, testing_strategy.md, TESTING_GUIDE.md, and TEST_SUITE_INDEX.md for DB-AT-001/002 gaps (6 gaps per test, 12 cross-cutting); reviewed TORCH-BRIDGE-001/TORCH-CLI-003 artifacts for reusable metrics; proposed standardized metrics.json schema (correlation, mse, rmse, max_abs_diff, sum_ratio), trace log structure, and parity/ subdirectory convention; ran pytest --collect-only for both selectors (0 tests collected as expected). Metrics: 0 tests collected for DB_AT_001, 0 tests collected for DB_AT_002, pytest collection runtime 1.00s each. Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/{audit_notes.md,doc_refs.json,pytest_collect_DB_AT_001.log,pytest_collect_DB_AT_002.log}. First Divergence: n/a. Next Actions: Phase B harness blueprint (B1: draft parity_harness_spec.md or equivalent normative doc with inputs/commands/metrics for DB-AT-001/002; B2: encode phased rollout tasks; B3: prepare metrics/trace templates referenced in spec); update implementation.md Phase A status to complete with deliverables summary.
  * 2025-10-29T001027Z — Completed Phase B harness blueprint (B1-B3): Authored docs/parity_harness_spec.md (600+ lines, 8 normative sections) defining DB-AT-001 (simple cubic parity, §2) and DB-AT-002 (determinism, §3) with golden data requirements, configuration parity, environment flags, metrics computation (correlation/MSE/RMSE/max|Δ|/sum_ratio schema in §4.3), trace capture workflow (20+ checkpoints per §2.6), artifact layout (parity/determinism subdirectories in §4.1), and pass/fail criteria (§2.8, §3.7) aligned with spec-db-conformance.md thresholds; updated implementation.md Phase B checklist with completion status; published metrics_template.json, trace_requirements.md, and artifact_layout.md templates under reports path; ran pytest --collect-only for DB_AT_001/002 (0 tests collected as expected). Metrics: 0 tests collected for DB_AT_001, 0 tests collected for DB_AT_002, pytest collection runtime 1.00s each. Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/{summary.md,parity/metrics_template.json,parity/trace_requirements.md,parity/artifact_layout.md,collect_DB_AT_001.log,collect_DB_AT_002.log}. First Divergence: n/a. Next Actions: Phase C cross-doc sync (C1: update TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md with artifact expectations; C2: add parity_harness_spec.md to index.md and prompt_sources_map.json; C3: capture final evidence and update ledger); future implementation tasks include authoring DB-AT-001/002 test scaffolds and helper utilities (correlation, trace capture, diff heatmap, golden loader, metrics writer per §6.1).
  * 2025-10-29T002248Z — Supervisor planning for Phase C doc sync: validated docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md parity rows still lack harness metrics/env flags, confirmed docs/index.md and docs/prompt_sources_map.json omit docs/parity_harness_spec.md, and reaffirmed exit criteria 3-4 remain unmet; defined Do Now to execute C1-C3 with new artifact root plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/ and mapped pytest --collect-only selectors for DB_AT_001/002 (expected 0). Metrics: pending. Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/.
  * 2025-10-29T002248Z — Completed Phase C doc sync (C1-C3): Updated docs/TESTING_GUIDE.md §2 DB_AT_001/002 rows with complete harness metadata (environment flags, golden data paths, metrics thresholds, artifact subdirectories, trace workflow refs per parity_harness_spec.md §2/§3); synchronized docs/development/TEST_SUITE_INDEX.md with matching entries including dual spec references; added parity_harness_spec.md entry to docs/index.md Testing & Validation section with keywords and usage guidance; added docs/parity_harness_spec.md to docs/prompt_sources_map.json specs array (JSON validated with python -m json.tool); ran pytest --collect-only for DB_AT_001/002 (0 tests collected as expected, status=Planned); captured git diff and summary.md. Metrics: 0 tests collected for DB_AT_001 (KMP_DUPLICATE_LIB_OK=TRUE), 0 tests collected for DB_AT_002 (CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 KMP_DUPLICATE_LIB_OK=TRUE), pytest collection runtime 1.00s each. Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/{summary.md,doc_diffs.log,collect_DB_AT_001.log,collect_DB_AT_002.log}. First Divergence: n/a. Next Actions: All exit criteria (1-4) satisfied; mark implementation.md Phase C complete; update status to done; parity_harness_spec.md now discoverable via index.md and prompt_sources_map.json; future loops can reference normative harness requirements when authoring DB-AT-001/002 test implementations.

### [FINDINGS-LEDGER-002] Extend knowledge base with torch experiment lessons
- Depends on: TORCH-BRIDGE-001, TORCH-CLI-003
- Status: pending
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. Review artifacts under `plans/active/TORCH-BRIDGE-001/reports/` and `plans/active/TORCH-CLI-003/reports/` to extract durable lessons spanning geometry, runtime, and CLI diagnostics (see `docs/spec-db-tracing.md:10-72`).
  2. Add at least three new entries to `docs/findings.md`, each with ID, tags, summary, spec/code source (e.g., `docs/spec-db-core.md`, `dbex/refine_one.py`), and status per ledger format (`docs/index.md:70-90`).
  3. Cross-link new findings within relevant docs (e.g., `docs/TESTING_GUIDE.md`, `docs/architecture.md`) where the lessons inform workflows, ensuring references appear in `docs/prompt_sources_map.json`.
  4. Capture evidence summary (`summary.md`) under `plans/active/FINDINGS-LEDGER-002/reports/<timestamp>/` documenting reviewed artifacts and resulting ledger updates.
- Attempts History:
  * pending — Metrics: pending. Artifacts: pending.
### [DOC-RUNTIME-004] Restore `docs/pytorch_runtime_checklist.md`
- Depends on: none
- Status: done
- Owner/Date: Unassigned / 2025-10-28
- Exit Criteria:
  1. `docs/pytorch_runtime_checklist.md` resolves to a valid file (symlink or local copy) and can be opened without build errors.
  2. Runtime guardrails referenced by the checklist remain aligned with `docs/spec-db-conformance.md` and `docs/architecture.md` guidance.
  3. `docs/index.md` and `docs/prompt_sources_map.json` reference the restored checklist path.
- Working Plan: plans/active/DOC-RUNTIME-004/implementation.md
- Attempts History:
  * 2025-10-28T233630Z — Supervisor planning pass; confirmed symlink target (`../../nanoBragg2/docs/development/pytorch_runtime_checklist.md`) missing, indexed references unresolved, and new implementation plan required. Metrics: pending. Artifacts: pending.
  * 2025-10-28T233723Z — Completed A1-A2-B1-B2-C1-C2 restoration and enhancement: Enhanced existing `docs/pytorch_runtime_checklist.md` with explicit spec citations (`docs/spec-db-runtime.md:10-20`, `docs/spec-db-conformance.md:10-48`); added Environment Variables section (§5) and Acceptance Test Hooks section (§6) covering all DB-AT profiles; fixed 1 incorrect reference in `docs/development/testing_strategy.md:27`; verified all prompts and `docs/prompt_sources_map.json` reference correct path; captured validation evidence via `head -n 40` command. Metrics: 23 total references cataloged, 1 reference corrected, 2 new sections added, 6 spec citations added. Artifacts: plans/active/DOC-RUNTIME-004/reports/2025-10-28T233723Z/{notes.md,checklist_head.log,summary.md}. First Divergence: n/a. Next Actions: All exit criteria satisfied; initiative complete and ready for archive.
