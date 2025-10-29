# galph_memory.md — Supervisor Turn Log (DBEX)

Use this file to append a single line per supervisor turn capturing the FSM state and dwell count for the current focus.

Template (copy/paste and fill values each turn):
```
[timestamp] focus=<id/slug> state=<gathering_evidence|planning|ready_for_implementation> dwell=<n> artifacts=plans/active/<initiative>/reports/<YYYY-MM-DDTHHMMSSZ>/ next_action=<one-liner or 'switch_focus'>
```

Example:
```
2025-10-28T12:34:56Z focus=TORCH-BRIDGE-001 state=gathering_evidence dwell=1 artifacts=plans/active/TORCH-BRIDGE-001/reports/2025-10-28T123456Z/ next_action=map parity selector and artifact hub
```

Notes
- Enforce the dwell guard: on the 3rd consecutive turn in `gathering_evidence` or `planning` for the same focus, either transition to `ready_for_implementation` with a concrete Do Now or switch focus and record the block in `docs/fix_plan.md`.
- See `prompts/fsm_analysis.md` for the canonical state list and transitions.

## 2025-10-28T224846Z — TORCH-BRIDGE-001 Phase B plan
- Focus: TORCH-BRIDGE-001 — Bridge DataLoad to nanobrag_torch
- Action Type: planning
- Key Observations: Phase A helper/tests already landed; no DetectorConfig/BeamConfig/CrystalConfig helpers or tests exist yet (`rg DetectorConfig` only hits docs); spec shards (docs/spec-db-core.md §35-41, docs/config_crosswalk.md §15-66, docs/dxtbx_api.md §5-50, docs/nanobrag_api.md §23-58) remain current; docs/index.md and prompt_sources_map.json already list required references.
- Artifact Path: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/
- Next Actions: Execute Phase B checklist (B1-B2) via new tests/helper, capture pytest log + notes under the artifact path, then progress toward Phase C smoke harness.
- Reality Check: Verified exit criteria 2 & 4 still unmet (no config hydration, no smoke harness); runtime checklist symlink still unresolved per backlog DOC-RUNTIME-004; selected item remains active and dependencies satisfied.
- <Action State>: [planning]

## 2025-10-28T230500Z — TORCH-BRIDGE-001 Phase C planning
- Focus: TORCH-BRIDGE-001 — Bridge DataLoad to nanobrag_torch
- Action Type: planning
- Key Observations: Phase C smoke harness and ROI artifacts remain undone; no files matching *triptych* under plans/active/TORCH-BRIDGE-001/reports/; nanobrag_torch still unavailable so bridge stubs must be guarded; verified dataset assets (`refGeom.expt`, `_geom_ref.refl`, `scaled.mtz`) present for the run; `docs/pytorch_runtime_checklist.md` still missing per DOC-RUNTIME-004 backlog.
- Artifact Path: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/
- Next Actions: Execute Do Now checklist (author smoke pytest scaffolding, implement stitched Bragg + masked MSE harness, capture ROI triptych & metrics, update ledgers).
- Reality Check: Confirmed exit criteria 4 unmet (no smoke harness artifacts/logs) and verified plan prerequisites (dataset paths, config helpers, pending runtime checklist restoration); rescoping not required.
- <Action State>: [ready_for_implementation]

## 2025-10-28T233500Z — TORCH-BRIDGE-001 closeout plan
- Focus: TORCH-BRIDGE-001 — Bridge DataLoad to nanobrag_torch
- Action Type: planning
- Key Observations: Phase A–C artifacts/ledgers complete; exit criteria 1-4 satisfied with tests and ROI evidence; refGeom dataset absent by default so rerun needs asset check; added Phase D (D1-D2) closeout checklist to implementation plan for rerun + ledger updates; prior smoke test hardcodes artifact path so copy step required for new report timestamp.
- Artifact Path: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z/
- Next Actions: Execute D1-D2 closeout (rerun bridge/smoke pytest, update fix_plan status + attempts entry)
- Reality Check: Verified helper/config/smoke harness code + artifacts satisfy exit criteria; rescope focus from new implementation to verification/documentation wrap-up before marking `TORCH-BRIDGE-001` done.
- <Action State>: [planning]

2025-10-28T233500Z focus=TORCH-BRIDGE-001 state=planning dwell=1 artifacts=plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z/ next_action=execute_D1-D2_closeout

## 2025-10-28T232915Z — TORCH-RUNTIME-002 planning kickoff
- Focus: TORCH-RUNTIME-002 — Author torch runtime checklist + testing harness seed
- Action Type: planning
- Key Observations: TORCH-BRIDGE-001 reports reviewed (closure artifacts intact); runtime checklist symlink (docs/pytorch_runtime_checklist.md) still broken per DOC-RUNTIME-004; docs/TESTING_GUIDE.md already lists flags/selectors but needs explicit torch references and artifact guidance; TEST_SUITE_INDEX placeholders align with spec but lack evidence runs; no reports yet under plans/active/TORCH-RUNTIME-002/.
- Artifact Path: plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/
- Next Actions: Execute Do Now items (A1–A2 doc updates, B1 selector sync, B2 collect-only artifact) and refresh fix_plan attempts metadata.
- Reality Check: Confirmed exit criteria unmet (no TORCH-RUNTIME-002 artifacts, ledger metrics pending); dependencies satisfied (TORCH-BRIDGE-001 status done); rescoping not needed beyond noting DOC-RUNTIME-004 dependency for checklist restoration.
- <Action State>: [planning]

2025-10-28T232915Z focus=TORCH-RUNTIME-002 state=planning dwell=1 artifacts=plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/ next_action=execute_A1-A2-B1-B2

## 2025-10-28T233723Z — DOC-RUNTIME-004 planning kickoff
- Focus: DOC-RUNTIME-004 — Restore docs/pytorch_runtime_checklist.md
- Action Type: planning
- Key Observations: Confirmed docs/pytorch_runtime_checklist.md is a dangling symlink pointing to ../../nanoBragg2/... (target absent); `rg` shows prompts, docs/index.md:142-150, and testing_strategy.md:27 rely on the checklist; spec shards docs/spec-db-runtime.md:10-20 and docs/spec-db-conformance.md:10-48 capture required guardrails/tests; prompt_sources_map.json still references the broken path.
- Artifact Path: plans/active/DOC-RUNTIME-004/reports/2025-10-28T233723Z/
- Next Actions: Execute A1-A2-B1-B2-C1-C2 checklist to restore the checklist file, align references, and capture validation artifacts.
- Reality Check: Validated the premise (symlink broken, exit criteria unmet, no reports directory existed prior to this loop) and recorded the new implementation plan without rescoping the objective.
- <Action State>: [planning]

2025-10-28T233723Z focus=DOC-RUNTIME-004 state=planning dwell=1 artifacts=plans/active/DOC-RUNTIME-004/reports/2025-10-28T233723Z/ next_action=execute_A1-A2-B1-B2-C1-C2

## 2025-10-28T234618Z — TORCH-CLI-003 planning kickoff
- Focus: TORCH-CLI-003 — Wire torch backend flag into CLI
- Action Type: planning
- Key Observations: `dbex/refine_one.py` still hardcodes DiffBragg with no backend flag; Phase A/B checklist in plans/active/TORCH-CLI-003/implementation.md covers CLI flag + diagnostics; docs/spec-db-interfaces.md:7-16 and docs/architecture.md:28-55 define the required CLI surface; no reports yet under plans/active/TORCH-CLI-003/reports/.
- Artifact Path: plans/active/TORCH-CLI-003/reports/2025-10-28T234618Z/
- Next Actions: Execute A1–A2–B1–B2 to add the flag, implement dispatch, capture diagnostics, and update docs.
- Reality Check: Confirmed exit criteria unmet (no `--backend` support, no torch diagnostics), dependencies satisfied (TORCH-BRIDGE-001 done), and verified artifact directory absent so create new report path; rescoping not required.
- <Action State>: [ready_for_implementation]

2025-10-28T234618Z focus=TORCH-CLI-003 state=ready_for_implementation dwell=1 artifacts=plans/active/TORCH-CLI-003/reports/2025-10-28T234618Z/ next_action=execute_A1-A2-B1-B2

## 2025-10-29T000120Z — PARITY-HARNESS-001 planning kickoff
- Focus: PARITY-HARNESS-001 — Author DB-AT parity harness specs
- Action Type: planning
- Key Observations: Backlog parity note normalized into structured initiative; dependencies TORCH-BRIDGE-001/TORCH-CLI-003 confirmed done; created implementation plan with Phase A–C checklist and set reports timestamp (2025-10-29T000004Z) for audit artifacts; exit criteria still unmet (no harness spec doc yet).
- Artifact Path: plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/
- Next Actions: Execute A1–A3 evidence audit (doc gap review, artifact mining, report scaffolding) per implementation plan.
- Reality Check: Verified no existing parity harness documentation beyond placeholders (docs/spec-db-conformance.md) and no prior reports for this initiative; rescoping not required.
- <Action State>: [planning]

2025-10-29T000120Z focus=PARITY-HARNESS-001 state=planning dwell=1 artifacts=plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/ next_action=execute_A1-A3

## 2025-10-29T001132Z — PARITY-HARNESS-001 Phase B planning
- Focus: PARITY-HARNESS-001 — Author DB-AT parity harness specs
- Action Type: planning
- Key Observations: Reviewed Phase A artifacts (audit_notes.md, doc_refs.json) and confirmed B1-B3 checklist items remain outstanding; validated docs/spec-db-conformance.md:10-28, testing_strategy.md:168-180, TESTING_GUIDE.md:58-67, and TEST_SUITE_INDEX.md:7-13 references for parity scope; observed no docs/parity_harness_spec.md file yet and prompt sources map already lists current authoritative docs.
- Artifact Path: plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/
- Next Actions: Execute Phase B checklist (B1 draft spec, B2 update plan, B3 publish metrics/trace template) and capture evidence under the new report directory.
- Reality Check: Confirmed exit criteria unmet (no harness spec, selectors still planned, metrics template absent) and rescoping unnecessary; ready to proceed with documentation-focused implementation.
- <Action State>: [planning]

2025-10-29T001132Z focus=PARITY-HARNESS-001 state=planning dwell=2 artifacts=plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/ next_action=execute_B1-B3_spec_draft

## 2025-10-29T002248Z — PARITY-HARNESS-001 Phase C planning
- Focus: PARITY-HARNESS-001 — Author DB-AT parity harness specs
- Action Type: planning
- Key Observations: Implementation plan now shows Phase B complete; docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md parity rows still lack harness metrics/env guards; docs/index.md and docs/prompt_sources_map.json do not reference docs/parity_harness_spec.md; selectors DB_AT_001/002 remain Planned with 0 collection (expected); exit criteria C1-C3 remain open.
- Artifact Path: plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/
- Next Actions: Execute C1-C3 doc sync checklist (update testing docs, index and prompt map, capture evidence, refresh fix-plan Attempts History).
- Reality Check: Validated required docs exist but are out of sync with the newly published parity_harness_spec.md; no rescope needed because exit criteria 3-4 still unmet and dependencies remain satisfied.
- <Action State>: [ready_for_implementation]

2025-10-29T002248Z focus=PARITY-HARNESS-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PARITY-HARNESS-001/reports/2025-10-29T002248Z/ next_action=execute_C1-C3_doc_sync

## 2025-10-29T003751Z — TORCH-CLI-003 Phase C planning
- Focus: TORCH-CLI-003 — Wire torch backend flag into CLI
- Action Type: planning
- Key Observations: `tests/dbex/test_refine_one_cli.py` already exercises the backend flag but no recent pytest artifacts exist; `docs/spec-db-interfaces.md:7-12` still claims `--backend` is unimplemented; CLI selector absent from docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md despite six passing tests; created Phase C checklist (C1-C3) to capture evidence and synchronize docs/ledger.
- Artifact Path: plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/
- Next Actions: Execute C1-C3 to run pytest + collect-only with artifacts, update testing docs & spec status, and refresh fix-plan Metrics/Artifacts lines.
- Reality Check: Validated exit criteria 1-3 satisfied (backend flag + diagnostics + docs/index update present); exit criterion 4 still open because torch CLI smoke lacks documented evidence/logs; rescope from implementation to evidence/registry alignment.
- <Action State>: [planning]

2025-10-29T003751Z focus=TORCH-CLI-003 state=planning dwell=1 artifacts=plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/ next_action=execute_C1-C3

## 2025-10-29T010945Z — FINDINGS-LEDGER-002 planning kickoff
- Focus: FINDINGS-LEDGER-002 — Extend knowledge base with torch experiment lessons
- Action Type: planning
- Key Observations: Dependencies TORCH-BRIDGE-001 and TORCH-CLI-003 are complete with rich artifacts (smoke_metrics.json, pytest_cli.log); docs/findings.md still contains only four entries covering geometry/runtime/parity basics; authored implementation plan with Phases A-D to guide artifact survey, findings drafting, doc sync, and ledger closure; new reports root created at plans/active/FINDINGS-LEDGER-002/reports/2025-10-29T010945Z/.
- Artifact Path: plans/active/FINDINGS-LEDGER-002/reports/2025-10-29T010945Z/
- Next Actions: Execute Phase A (A1-A3) to inventory bridge/CLI evidence and capture candidate lessons before drafting ledger updates.
- Reality Check: Confirmed required artifacts exist and exit criteria remain unmet (knowledge base lacks torch bridge/CLI lessons); no rescope needed because new findings and cross-links still outstanding.
- <Action State>: [planning]

2025-10-29T010945Z focus=FINDINGS-LEDGER-002 state=planning dwell=1 artifacts=plans/active/FINDINGS-LEDGER-002/reports/2025-10-29T010945Z/ next_action=run_phase_A_inventory
## 2025-10-29T010326Z — PARITY-HARNESS-002 Phase A planning
- Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
- Action Type: planning
- Key Observations: No simple-cubic golden data exists under tests/; nanoBragg2 mirror absent so fallback mirror must be generated; docs/TESTING_GUIDE.md:62-77 and docs/development/TEST_SUITE_INDEX.md:18-36 still list DB_AT_001/002 as Planned with 0 collection; parity_harness_spec.md §2 highlights manifest+checksum rules and metrics schema needed before enforcing correlation thresholds; findings (CONFORMANCE-001, DIAGNOSTICS-001, TESTING-003, GEOMETRY-001) govern fixture design.
- Artifact Path: plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/
- Next Actions: Execute Phase A checklist (A1-A4) to mirror golden data, author manifest+loader, seed minimal DB_AT_001 test, and capture smoke/log evidence.
- Reality Check: Confirmed golden dataset absent locally, selectors remain Planned (0 tests) so plan adds minimal test + collect-only logging before marking Active; no rescope required, dependencies satisfied.
- <Action State>: [ready_for_implementation]

2025-10-29T010326Z focus=PARITY-HARNESS-002 state=ready_for_implementation dwell=1 artifacts=plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/ next_action=execute_A1-A4_fixture_bootstrap
## 2025-10-29T013411Z — FORWARD-EQUIV-001 planning kickoff
- Focus: FORWARD-EQUIV-001 — Forward equivalence smoke validation
- Action Type: planning
- Key Observations: TORCH-BRIDGE-001 and TORCH-CLI-003 artifacts verified; parity harness manifest tests already occupy DB_AT_001 but emit no forward metrics; golden dataset directory currently holds manifest/metadata only (no .npy arrays), so forward harness must regenerate or supply tensors before metrics can run; torch backend still stubbed with random peaks, so DB_AT_001 must xfail while capturing diagnostics.
- Artifact Path: plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/
- Next Actions: Execute implementation.md Phase A-B checklist to capture DiffBragg/torch baselines, compute ROI metrics, and emit forward_equiv artifacts prior to doc sync.
- Reality Check: Confirmed refGeom.expt/refl and scaled.mtz exist; noted absence of golden `.npy` tensors and planned RNG seeding + xfail policy to keep harness reproducible until real simulator lands; no rescope needed.
- <Action State>: [ready_for_implementation]

2025-10-29T013411Z focus=FORWARD-EQUIV-001 state=ready_for_implementation dwell=1 artifacts=plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/ next_action=execute_A1-A4_baseline_capture
## 2025-10-29T015235Z — PARITY-HARNESS-002 planning restart
- Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
- Action Type: planning
- Key Observations: Added missing fix-plan entry (status in_progress) and authored implementation checklist (A-D); confirmed dependencies TORCH-BRIDGE-001 and FORWARD-EQUIV-001 are done; existing DB_AT_001 manifest tests collect 3 passes but emit no metrics/artifacts beyond checksum logs; no parity metrics helper or traces exist yet, and torch simulator remains stubbed so future test must xfail while capturing diagnostics; planning notes stored under new reports timestamp with spec anchors (`docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:30-53`).
- Artifact Path: plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/
- Next Actions: Execute B1-B3 metrics harness build-out then sync docs per Do Now checklist.
- Reality Check: Validated FALLBACK golden dataset checksum (`df88c7d2…`) matches recorded manifest, and confirmed spec thresholds still govern DB_AT_001; rescoped initiative from manifest-only coverage to metrics+artifact parity work with conditional xfail.
- <Action State>: [planning]

2025-10-29T015235Z focus=PARITY-HARNESS-002 state=planning dwell=1 artifacts=plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/ next_action=execute_B1-B3_metrics_harness
## 2025-10-29T020937Z — PARITY-HARNESS-002 Phase D planning
- Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
- Action Type: planning
- Key Observations: Implementation plan Phases A-C remain synthetic-only; DB_AT_001 parity smoke still injects Gaussian noise instead of comparing DiffBragg vs torch outputs; no first-divergence capture exists despite spec-db-tracing.md:10-19 requirements; docs/TESTING_GUIDE.md:84 and docs/development/TEST_SUITE_INDEX.md:14 already list selector as Active but lack references to trace artifacts; confirmed docs/index.md and docs/prompt_sources_map.json remain in sync with available sources.
- Artifact Path: plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/
- Next Actions: Execute implementation.md D1 first-divergence instrumentation, then update ledger/docs per plan.
- Reality Check: Verified tests/dbex/test_db_at_001_parity.py still seeds synthetic noise → thresholds unmet (xfail) so exit criterion 3 not fully satisfied; confirmed golden dataset + manifest intact under tests/fixtures/golden_data/simple_cubic/; rescoped loop to add ROI scanning + trace artifacts before considering simulator swaps.
- <Action State>: [planning]

2025-10-29T020937Z focus=PARITY-HARNESS-002 state=planning dwell=2 artifacts=plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/ next_action=execute_D1_first_divergence
## 2025-10-29T022319Z — PARITY-HARNESS-002 closure planning
- Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
- Action Type: planning
- Key Observations: Phase A-D artifacts meet exit criteria but selector evidence is dated; added Phase E checklist (E1-E3) to verify DB_AT_001 parity run, finalize ledger status, and capture closing TODOs; confirmed relevant findings (CONFORMANCE-001, DIAGNOSTICS-001, TESTING-003, PARITY-001) govern closure steps.
- Artifact Path: plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/
- Next Actions: Execute E1 parity rerun + doc sync, E2 ledger closure, E3 archival summary.
- Reality Check: Validated that prior artifacts satisfy conformance/tracing specs but require fresh logs before marking initiative done; rescoped work from implementation to verification/closure.

2025-10-29T022319Z focus=PARITY-HARNESS-002 state=ready_for_implementation dwell=1 artifacts=plans/active/PARITY-HARNESS-002/reports/2025-10-29T022212Z/ next_action=execute_E1-E3_closure
## 2025-10-29T023905Z — NANOBRAG-GOLDEN-001 planning kickoff
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed simple_cubic manifest still marked FALLBACK with synthetic Gaussian Bragg tensor; refGeom inputs and scaled.mtz present; no canonical nanoBragg2 tensors archived yet; established new implementation checklist (A1–D3) and artifacts directory; cited governing specs (`docs/spec-db-core.md:20-41`, `docs/spec-db-conformance.md:23-26`, `docs/forward_equivalence.md:21-52`, `plans/nanobrag_integration_plan.md:23-88`).
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/
- Next Actions: Execute A1–A3 canonical dataset capture, then enforce DB_AT_001 thresholds and sync docs per Do Now.
- Reality Check: Validated that fallback tensors remain the only dataset, refGeom assets exist, and nanobrag_torch availability still unverified—no rescope required but environment check is first Do Now step.
- <Action State>: [ready_for_implementation]

2025-10-29T023905Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/ next_action=execute_A1-A3_canonical_capture
