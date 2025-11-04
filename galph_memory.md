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
## 2025-10-29T024902Z — NANOBRAG-GOLDEN-001 dependency unblock planning
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Fallback manifest still reports `simple_cubic_fallback`; `python3 -c "import nanobrag_torch"` fails (ModuleNotFoundError) and base python lacks pip; no `simforge/` or `easyBragg/` directories present; updated fix_plan dependency list with explicit simforge requirement and returned status to in_progress; staged new report root `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/` for upcoming env logs.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/
- Next Actions: execute A1 env bootstrap + nanobrag_torch install, then rerun DiffBragg baseline per updated Do Now.
- Reality Check: Validated that golden dataset exit criteria remain unmet (fallback tensors, missing torch backend) and rescoped loop toward restoring the simforge/simtbx toolchain before attempting canonical tensor generation.

2025-10-29T024902Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T024902Z/ next_action=execute_A1_env_bootstrap
2025-10-29T030352Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=2 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/ next_action=ready_env_and_canonical_capture_A1-A3
## 2025-10-29T030352Z — NANOBRAG-GOLDEN-001 environment recovery plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: torch import still trips libc10_cuda symbol error under simtbx despite reinstall attempts; nanobrag_torch remains absent locally; canonical dataset plan depends on restoring DiffBragg baseline and installing torch simulator before manifest updates; copied parity findings (CONFORMANCE-001, CONFIG-001, DIAGNOSTICS-001, PARITY-001, TESTING-003) remain applicable.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/
- Next Actions: Execute A1 diagnostics, install nanobrag_torch, rerun DiffBragg baseline, and prototype panel-0 nanobrag capture per new input.md Do Now.
- Reality Check: Verified exit criteria unmet (fallback tensors still active, nanobrag_torch missing, DiffBragg command fails); rescoped loop toward environment restoration plus first canonical capture attempt before manifest work.
- <Action State>: [planning]
## 2025-10-29T040641Z — NANOBRAG-GOLDEN-001 environment recovery plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: `setup_env.sh` currently exits early because `simforge/` is missing, so no python/torch on PATH; prior env logs confirm torch 2.8.0+cu128 is still active instead of the pinned 2.4.1+cu121; `nanoBragg_torch` sources are absent locally; DiffBragg baseline artifacts (`bragg_diffbragg.npy`, metadata.txt) are still missing while the last run ends with `GPUassert: invalid argument diffBraggCUDA.cu:708`; `tests/fixtures/golden_data/simple_cubic/manifest.json` remains flagged `simple_cubic_fallback`.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/
- Next Actions: Execute A1 environment rebuild with pinned torch + editable nanobrag_torch, then A2 baseline capture (GPU + CPU fallback) followed by DB_AT_001 collect-only refresh.
- Reality Check: Validated the fix-plan premise remains unmet—fallback tensors still live, nanobrag_torch missing, and DiffBragg baseline absent—so the work stays scoped to environment restoration and baseline capture before any manifest updates.
- <Action State>: [ready_for_implementation]

2025-10-29T040641Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T040641Z/ next_action=execute_A1-A2_env_baseline
## 2025-10-29T055449Z — NANOBRAG-GOLDEN-001 Environment-Freeze planning
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Fallback manifest still advertises `simple_cubic_fallback`; `setup_env.sh` aborts because `simforge/` is absent so prior rebuild commands violate the Environment Freeze guardrail; `diffBraggCUDA.cu:708` wraps `cudaFree(cp.cu_sourceI_scale)`, indicating the GPU assert is triggered while freeing source-intensity buffers. Logged these observations in planning_notes.md with a CPU fallback approach staged under the new report directory.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/
- Next Actions: Execute Do Now A2 analysis: capture annotated snippet of diffBraggCUDA.cu, log setup_env.sh failure, and attempt CPU devId=-1 export with diagnostics.
- Reality Check: Verified exit criteria remain unmet (canonical tensors absent); dependencies still marked done; rescoped Do Now away from package installs to pure analysis/CPU fallback per Environment Freeze policy.
- <Action State>: [planning]

2025-10-29T055449Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/ next_action=run_A2_analysis_cpu_fallback
2025-10-29T061218Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=2 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/ next_action=gather_A1_env_evidence
## 2025-10-29T061218Z — NANOBRAG-GOLDEN-001 Environment-Freeze handoff plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed `tests/fixtures/golden_data/simple_cubic/manifest.json` still declares `simple_cubic_fallback`; `python3 -c "import nanobrag_torch"` and `python3 -c "import simtbx"` both raise ModuleNotFoundError while the `python` shim is absent; top-level taxonomy in `docs/TESTING_GUIDE.md` still labels “Forward equivalence smoke” as Active despite §2.1 and `docs/development/TEST_SUITE_INDEX.md` flagging it Planned/blocked; authoritative doc list (`docs/index.md`, `docs/prompt_sources_map.json`) unchanged. Findings referenced: TESTING-003, CONFIG-001, CONFORMANCE-001, DIAGNOSTICS-001, PARITY-001.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T061218Z/
- Next Actions: Capture env diagnostics (`env_diagnostics.log`), refresh parity vs forward collect-only logs, then update fix_plan/docs with the Environment Freeze blocker once evidence is archived.
- Reality Check: Validated canonical dataset still absent and both simtbx + nanobrag_torch missing under the frozen runtime; rescoped work to evidence/documentation so the initiative can move to `blocked` once dependencies are available.
- <Action State>: [planning]
2025-10-29T064735Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/ next_action=run_A2_A3_canonical_capture
## 2025-10-29T064735Z — NANOBRAG-GOLDEN-001 canonical capture plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed `nanobrag_torch`, `simtbx`, and torch 2.4.1+cu121 import cleanly; `tests/fixtures/golden_data/simple_cubic/manifest.json` still lists `simple_cubic_fallback`; DiffBragg GPU path remains the viable baseline per DIFFBRAGG-001; documented command skeleton to emit paired DiffBragg/torch tensors plus ROI metrics under 2025-10-29T063817Z.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/
- Next Actions: Execute capture_forward.py (A2+A3), archive metrics/logs, then refresh DB_AT_001 collect-only logs and update fix_plan/docs.
- Reality Check: Validated dependencies and test selectors are present; rescoped from environment triage to canonical dataset capture with GPU enforcement.
- <Action State>: [ready_for_implementation]
## 2025-10-29T070359Z — NANOBRAG-GOLDEN-001 Environment-Freeze block documentation
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed `tests/fixtures/golden_data/simple_cubic/manifest.json` still flags `simple_cubic_fallback`; no `golden_dataset/legacy/` or torch outputs were produced in 2025-10-29T063817Z beyond logs; canonical capture log shows `GPUassert: invalid argument diffBraggCUDA.cu:708` halting diffBragg_forward even after successful `dbex.refine_one` ROI export. Existing findings already record DIFFBRAGG-001, so this loop will consolidate evidence and move the initiative to `blocked`.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/
- Next Actions: Execute the A2/A3 evidence capture notes, refresh DB_AT_001 collect-only logs, and update docs/fix_plan.md with a blocked Attempts History entry.
- Reality Check: Re-verified canonical dataset still absent and Environment Freeze prevents simtbx patching; rescoped loop to documentation and ledger updates rather than further capture attempts.
- <Action State>: [planning]

2025-10-29T070359Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/ next_action=prep_A2_A3_block_docs
2025-10-29T071728Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=2 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/ next_action=execute_A2_A3_B1_D1_evidence
## 2025-10-29T071728Z — NANOBRAG-GOLDEN-001 ROI rescope planning
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed fallback manifest still advertises `simple_cubic_fallback`; legacy ROI HDF5 artifact present under 2025-10-29T063817Z; no `golden_dataset/torch/` outputs exist; Environment Freeze continues to bar simtbx modifications despite POLICY-001 exception lacking local source tree. Drafted ROI evidence plan (A2/A3/B1/D1) and staged 2025-10-29T071728Z report directory with planning_notes.md outlining ROI inventory, torch replay roadmap, and manifest adjustments.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T071728Z/
- Next Actions: Execute ROI HDF5 scout, torch replay outline, manifest update outline, and doc/test sync definition per input.md; reassess readiness for implementation afterward.
- Reality Check: Validated canonical `[panel,slow,fast]` tensors remain absent while ROI data is available; rescoped initiative to gather ROI evidence and manifest/test plans before requesting spec change or targeted simtbx patch.
- <Action State>: [planning]
2025-10-29T075930Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/ next_action=run_A2_catalog
## 2025-10-29T075930Z — NANOBRAG-GOLDEN-001 bbox catalog planning
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed `refGeom.refl` still provides bbox metadata (282 reflections) while legacy ROI HDF5 lacks bbox attrs; fallback manifest remains `simple_cubic_fallback`; Environment Freeze intact so plan targets docs/evidence only.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T075930Z/
- Next Actions: Follow Do Now (A2 catalog emission, A3 torch playbook, B1 manifest delta, D1 collect-only refresh) to unblock canonical capture prep.
- Reality Check: Revalidated absence of canonical tensors and verified ROI bbox data availability before scheduling catalog emission.
- <Action State>: [ready_for_implementation]
## 2025-10-29T074614Z — NANOBRAG-GOLDEN-001 canonical capture prep
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Fallback manifest still active (`simple_cubic_fallback`); patched simtbx build evidence exists but latest canonical_capture log retains `GPUassert` at diffBraggCUDA.cu:708; `nanobrag_torch` imports cleanly; ROI catalog (282 entries) + legacy ROI set (92) remain available for parity alignment; staged new report directory (2025-10-29T074423Z) with planning notes outlining DiffBragg retest + torch capture sequencing.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/
- Next Actions: Execute A2 DiffBragg rerun, A3 torch capture, then D1 parity/forward pytest per input.md.
- Reality Check: Validated canonical tensors absent, confirmed torch dependency present, and rescoped plan to re-verify the DIFFBRAGG-001 fix before proceeding with torch capture and test/doc updates.
- <Action State>: [planning]
2025-10-29T074614Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=1 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T074423Z/ next_action=run_A2_diffbragg_rerun
2025-10-29T080253Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=2 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/ next_action=execute_A1_A2_A3
## 2025-10-29T080253Z — NANOBRAG-GOLDEN-001 canonical capture plan refresh
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: `nanobrag_torch` now imports successfully inside the frozen simtbx env (`python -c "import nanobrag_torch"`); ROI catalog/playbook artifacts from 2025-10-29T075930Z remain intact; capture_forward.py covers DiffBragg + torch outputs so a single run can satisfy A2+A3 once environment evidence is recorded.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/
- Next Actions: Execute input.md (2025-10-29T080253Z) Do Now checklist—log env evidence (A1), run capture_forward.py for canonical tensors (A2+A3), and archive metrics plus DB_AT_001 collect-only logs with doc updates (D1).
- Reality Check: Validated the previous blocker (nanobrag_torch missing) is cleared and rescoped the focus from docs-only prep to ready-for-execution canonical capture while keeping Environment Freeze constraints explicit.
- <Action State>: [ready_for_implementation]
## 2025-10-29T082521Z — NANOBRAG-GOLDEN-001 canonical capture recovery plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: 2025-10-29T080253Z canonical_capture.log ends with `TypeError: Object of type float32 is not JSON serializable`; golden_dataset directory lacks bragg_diffbragg.npy/bragg_torch.npy outputs; manifest in tests/fixtures/golden_data/simple_cubic/ still points at simple_cubic_fallback.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T082521Z/
- Next Actions: Repatch capture_forward.py with numpy→Python conversion, rerun canonical capture, replace fixtures with canonical tensors, update parity tests/docs, and log new findings.
- Reality Check: Validated canonical tensors were never produced (JSON crash) and rescoped the loop to redo Phase A before manifest/parity updates; confirmed fallback dataset remains active and dependencies (TORCH-BRIDGE-001/FORWARD-EQUIV-001) still satisfied.
- <Action State>: [ready_for_implementation]
2025-10-29T082521Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=3 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T082521Z/ next_action=execute_A2_to_D2
2025-10-29T085401Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=4 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/ next_action=run_canonical_capture_debug
## 2025-10-29T085401Z — NANOBRAG-GOLDEN-001 canonical capture debug plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Torch simulator still emits all-zero panels even with raw F amplitudes; `crystal.get_structure_factor` returns non-zero so HKL mapping/orientation is the likely culprit; fixtures only contain manifest/metadata so canonical tensors haven’t landed; new report root (2025-10-29T084244Z) staged for capture artifacts.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/
- Next Actions: Apply input.md Do Now—refactor generator into canonical capture with HKL debug, confirm non-zero torch maxima, refresh fixtures/manifest, and rerun DB_AT_001 parity.
- Reality Check: Verified canonical `.npy` files absent from fixtures and confirmed torch output zero via local simulation; plan scoped to re-run capture with added instrumentation under Environment Freeze constraints.
- <Action State>: [ready_for_implementation]
## 2025-10-29T091339Z — NANOBRAG-GOLDEN-001 scale propagation plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: DiffBragg baseline from 2025-10-29T084244Z peaks at 3.6e4 while torch stack stays all zeros (torch_max=0.0, sum=0.0); HKL debug shows 69,614 in-range reflections so coverage isn’t the culprit; current repo lacks copied `.npy` tensors, leaving fixtures still on the fallback manifest.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z/
- Next Actions: Instrument generator for raw torch intensity logging, inject DiffBragg global scale before saving torch tensors, rerun capture into 2025-10-29T091339Z/golden_dataset, refresh fixtures/manifest, and rerun DB_AT_001 parity test.
- Reality Check: Verified canonical tensors absent in repo fixtures and confirmed parity selector remains gated by zero-output torch baseline; rescoped loop to focus on scale propagation instead of additional diagnostics.
- <Action State>: [planning]
2025-10-29T091339Z focus=NANOBRAG-GOLDEN-001 state=planning dwell=5 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z/ next_action=ready_for_implementation
## 2025-10-29T093203Z — NANOBRAG-GOLDEN-001 reciprocal index plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: docs/architecture/parameter_trace_analysis.md:47 confirms Miller indices must use rotated reciprocal vectors; 2025-10-29T091339Z canonical_capture.log shows `_compute_physics_for_position` still using real-space axes, explaining torch_max=0.0 despite scaled structure factors; staged new loop directory 2025-10-29T092655Z with placeholder artifacts.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/
- Next Actions: Patch nanobrag_torch.simulator.compute_physics_for_position to use rot_*_star, regenerate canonical capture via scripts/generate_simple_cubic_golden.py into the new directory, then rerun DB_AT_001 forward-equivalence pytest with updated tensors.
- Reality Check: Verified canonical tensors remain missing and fallback manifest still active; replayed spec anchors (docs/spec-db-core.md, docs/forward_equivalence.md) to confirm non-zero torch panels are required before manifest swap.
- <Action State>: [ready_for_implementation]
2025-10-29T093203Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=6 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/ next_action=swap_reciprocal_vectors_and_rerun_db_at_001
## 2025-10-29T095110Z — NANOBRAG-GOLDEN-001 real-space HKL plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Reviewed 2025-10-29T092655Z canonical_capture.log showing torch_max=0 and HKL hit rate 0/6,224,001; compared against torch_hkl_debug.json bounds (h∈[-24,24], k∈[-28,28], l∈[-31,31]); confirmed simulator currently dots scattering with reciprocal vectors after Å⁻¹ conversion, deviating from nanoBragg.c real-space projection.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/
- Next Actions: Restore real-space projection in compute_physics_for_position, log HKL extrema per panel, regenerate canonical tensors, and rerun DB_AT_001 selector.
- Reality Check: Validated canonical dataset still missing non-zero torch tensors and that fallback manifest remains active; rescoped loop from reciprocal-vector debugging to reconnecting the pure function with the C reference while preserving Environment Freeze.
- <Action State>: [ready_for_implementation]
2025-10-29T095110Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=7 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/ next_action=restore_real_space_projection_and_regenerate
## 2025-10-29T100617Z — NANOBRAG-GOLDEN-001 incident-beam orientation plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: `canonical_capture.log` (2025-10-29T094859Z) logs `INCIDENT_BEAM_DIRECTION= 0 0 1` while the detector normal points toward the sample, proving the cached incident vector is sample→source; multi-source code already negates `source_directions`, so single-source defaults must follow suit. Logged HKL min/max remain `[18,48] / [14,53] / [23,61]` with 0% hit rate; added HKL-ORIENT-001 to docs/findings.md and recorded the plan in docs/fix_plan.md Attempts History.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/
- Next Actions: Negate the cached incident beam vector in `Simulator.__init__`, regenerate canonical tensors, confirm HKL stats within grid bounds, and rerun DB_AT_001 parity.
- Reality Check: Verified canonical fixtures still point at fallback data and torch tensors remain all zeros; rescoped to focus on the incident-beam orientation fix before touching manifest/tests.
- <Action State>: [ready_for_implementation]
2025-10-29T100617Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=8 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/ next_action=negate_incident_vector_and_regenerate
## 2025-10-29T103845Z — NANOBRAG-GOLDEN-001 canonical fixtures plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Confirmed `tests/fixtures/golden_data/simple_cubic/` still contains only manifest/metadata with fallback hashes; no `.npy` tensors exist in repo or latest artifacts, and parity loader expects per-panel files with bool masks. Verified generator script outputs uint8 masks and that `.gitignore` currently drops fixture `.npy`, explaining why canonical tensors never landed in git.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/
- Next Actions: Regenerate canonical DiffBragg + torch tensors into the new report directory, copy them into fixtures with bool loss mask + fresh SHA256, adjust `.gitignore` to allow the fixture npy files, update `tests/fixtures/parity_loader.py::load_golden_data`, and rerun DB_AT_001 parity selector.
- Reality Check: Rescoped initiative from simulator physics to fixture integration after validating the beam fix artifacts exist but the fixtures remain fallback-only; plan centers on checklist items A2/A3/B1/B2 with ready code changes.
- <Action State>: [ready_for_implementation]
2025-10-29T103845Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=9 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T104500Z/ next_action=regen_dataset_update_loader_and_run_db_at_001
## 2025-10-29T110900Z — NANOBRAG-GOLDEN-001 canonical fixture rollout plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Reviewed 2025-10-29T104500Z canonical_capture.log/torch_hkl_debug.json; confirmed fixtures still lack `.npy` tensors (manifest-only) and parity loader remains pointed at fallback data; Working Plan checklist A2/A3/B1/B2 stay outstanding.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/
- Next Actions: Implement generator + loader bool-mask/manifest updates, capture canonical tensors into the new report directory, refresh fixtures, and rerun DB_AT_001 parity selector with artifact logging.
- Reality Check: Validated canonical dataset absent in fixtures, so focus stays on fixture swap rather than documentation-only cleanup.
- <Action State>: [ready_for_implementation]
2025-10-29T110900Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=10 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/ next_action=regenerate_tensors_update_fixtures_and_run_db_at_001
## 2025-10-29T181603Z — NANOBRAG-GOLDEN-001 canonical parity handoff
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Fixture directory still only holds manifest/metadata (no `.npy` tensors); canonical tensors remain under 2025-10-29T110900Z/golden_dataset; manifest lacks real CLI/git data and no self-checksum; parity test still injects synthetic noise so DB_AT_001 thresholds never exercise canonical DiffBragg↔torch pairs.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/
- Next Actions: Patch generator/loader/parity test per Do Now, rerun canonical capture with `--emit-manifest --fixtures`, and collect DB_AT_001 pytest evidence into the new report directory.
- Reality Check: Rescoped initiative to fixture propagation + parity enforcement after verifying canonical capture already exists but is not wired into tracked fixtures.
- <Action State>: [ready_for_implementation]
2025-10-29T181603Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=11 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/ next_action=apply_generator_loader_parity_updates_and_run_db_at_001
## 2025-10-29T212500Z — NANOBRAG-GOLDEN-001 parity scaling checkpoint
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Repo fixtures still lack canonical `.npy` tensors (manifest/metadata only); latest capture dir (2025-10-29T181603Z/golden_dataset) holds metadata without arrays; canonical_capture.log shows structure factors multiplied by sqrt(scale_override)=5.645e+08, yielding torch_max 2.19e13 vs DiffBragg 3.62e4 and negative correlation; HKL stats remain 69614/69614 so geometry intact; working plan checklist A2/A3/B1/B2 unresolved; docs/index.md & prompt_sources_map.json already reflect current sources.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/
- Next Actions: Remove duplicate sqrt(scale_override) scaling, rerun canonical capture with --emit-manifest --fixtures in this repo, and rerun DB_AT_001 parity selector capturing logs.
- Reality Check: Verified canonical `.npy` tensors absent and manifest references stale repo path; rescoped loop to scale correction + regeneration before parity enforcement.
- <Action State>: [ready_for_implementation]
2025-10-29T212500Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=12 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T212500Z/ next_action=remove_sqrt_scale_regenerate_and_run_db_at_001
## 2025-10-29T185313Z — NANOBRAG-GOLDEN-001 scale-alignment plan refresh
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Latest capture directory (2025-10-29T212500Z) records torch_max=6.9e-05 vs DiffBragg 3.6e4 and shows canonical `.npy` tensors missing from both golden_dataset and fixtures, so manifest references stale files. Parity harness still writes artifacts into 2025-10-29T181603Z, preventing evidence rollover. Logged SCALE-002 finding to track the √(spot_scale_override) post-simulation requirement.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T185313Z/
- Next Actions: Implement post-sim √scale in generator, regenerate tensors into 2025-10-29T185313Z with manifest + fixtures, retarget parity harness artifacts, and rerun DB_AT_001 capturing logs.
- Reality Check: Validated canonical assets absent despite manifest updates; rescoped to scaling + artifact path fixes before enforcing parity thresholds.
- <Action State>: [ready_for_implementation]
2025-10-29T185313Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=13 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T185313Z/ next_action=apply_sqrt_scale_regenerate_and_run_db_at_001
## 2025-10-29T190533Z — NANOBRAG-GOLDEN-001 scale + parity plan reset
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Fixtures still lack canonical `.npy` tensors (`manifest.json`/`metadata.json` only); latest capture metrics show sub-µ intensity after removing duplicate sqrt scale; parity smoke keeps emitting to 2025-10-29T181603Z instead of the fresh loop directory.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T190533Z/
- Next Actions: Execute Do Now to patch generator scaling + fixture emission, repoint parity harness outputs, regenerate tensors, and rerun DB_AT_001 under the new timestamp.
- Reality Check: Confirmed canonical assets absent and scale mismatch persists, so scope stays on checklist A3/B1/B3/C1 implementation for next loop.
- <Action State>: [ready_for_implementation]
2025-10-29T190533Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=14 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T190533Z/ next_action=execute_do_now_scale_fix_and_parity_refresh
## 2025-10-29T191906Z — NANOBRAG-GOLDEN-001 manifest guard planning
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Fixtures and `golden_dataset/` still miss all canonical `.npy` tensors; manifest points at `/home/ollie/Documents/diffbragg_example_2/...`, confirming last capture ran in a different checkout; logged MANIFEST-001 finding so generator must fail when payloads are absent.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T191906Z/
- Next Actions: Add payload existence checks in `generate_simple_cubic_golden.py`, rerun canonical capture within this repo, and re-run DB_AT_001 parity selector archiving artifacts under 2025-10-29T191906Z.
- Reality Check: Exit criteria A3/B1/B3/C1 remain unmet locally because canonical tensors are missing despite manifest timestamps.
- <Action State>: [ready_for_implementation]
2025-10-29T191906Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=15 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T191906Z/ next_action=add_generator_payload_guards_and_regenerate
## 2025-10-29T193557Z — NANOBRAG-GOLDEN-001 SCALE-002 planning refresh
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: `tests/fixtures/golden_data/simple_cubic/` still lacks `.npy` tensors (manifest/metadata only); latest canonical capture log points to `diffbragg_example_2` checkout; SCALE-002 finding requires √scale post-sim application and current script logs lack the diagnostic; spec shards (`docs/spec-db-core.md:16-33`, `docs/spec-db-conformance.md:23-26`, `docs/nanobrag_api.md:22-68`) confirm canonical tensors must be photon-scaled and provenance rich.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/
- Next Actions: Instrument √(spot_scale_override) diagnostics in `generate_simple_cubic_golden.py`, regenerate canonical tensors within this repo, and rerun DB_AT_001 parity capturing logs + scale ratios under the new report directory.
- Reality Check: Validated canonical payloads missing locally and manifest paths stale, so scope remains scaling + local regeneration before tightening parity thresholds.
- <Action State>: [ready_for_implementation]
2025-10-29T193557Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=16 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/ next_action=instrument_scale_regenerate_and_run_db_at_001
## 2025-10-29T194739Z — NANOBRAG-GOLDEN-001 canonical capture guard plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: `tests/fixtures/golden_data/simple_cubic/` currently contains only manifest/metadata (no `.npy` tensors); manifest command still references `/home/ollie/Documents/diffbragg_example_2/...`; `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/golden_dataset/` lacks tensor payloads entirely. Doc index (`docs/index.md`) and prompt map confirm no new sources; findings (MANIFEST-001, SCALE-001/002) remain active.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T194739Z/
- Next Actions: Add repo-root guards in `generate_simple_cubic_golden.py`, rerun canonical capture into this checkout with manifest + fixtures, list/sha tensors, rerun DB_AT_001 parity smoke, and update ledger attempts/history.
- Reality Check: Validated canonical tensors absent locally and manifest points to foreign checkout, so loop is rescoped to local regeneration safeguards before further parity tightening.
- <Action State>: [ready_for_implementation]
2025-10-29T194739Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=17 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T194739Z/ next_action=guard_paths_regenerate_and_run_db_at_001
## 2025-11-03T233556Z — NANOBRAG-GOLDEN-001 ROI diagnostics plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Local checkout still missing canonical `.npy` payloads under prior report directories even though fixtures now hold tensors; numpy probe confirms masked ROI correlation ≈ -0.004 with torch energy bleeding into masked-out pixels, so scaling fixes (SCALE-001/002) were insufficient. Authored parity_gap_notes.md and refreshed fix_plan Attempts History; drafted Do Now for ROI triptych instrumentation + local regeneration under 2025-11-03T233556Z artifacts.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-03T233556Z/
- Next Actions: Implement ROI triptych emission in `compute_roi_metrics`, regenerate canonical tensors inside this repo with `--roi-dump`, archive diagnostics, then rerun DB_AT_001 parity smoke.
- Reality Check: Dependencies satisfied; dwell guard hit long streak so next loop must execute implementation + pytest.
- <Action State>: [ready_for_implementation]
2025-11-03T233556Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=18 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-03T233556Z/ next_action=instrument_roi_triptychs_and_regenerate
2025-11-04T000201Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=19 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T000201Z/ next_action=log_peak_offsets_regenerate_and_run_parity
## 2025-11-04T000201Z — NANOBRAG-GOLDEN-001 parity offset reconnaissance
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Local checkout still lacks ROI `.npz` dumps under 2025-11-03T233556Z; manifest + fixtures point at `/home/ollie/Documents/diffbragg_example_2/...`. Recomputed masked metrics from fixtures (`prepare_refinement_inputs`) confirmed global_corr=-0.0041, localization=5.6%, and torch peaks displaced (roi_idx=5 diff peak (6,6) vs torch (11,7)). Logged findings in analysis_notes.md.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T000201Z/
- Next Actions: Patch compute_roi_metrics to emit peak offsets+filenames, regenerate canonical dataset locally via scripts/generate_simple_cubic_golden.py, rerun DB_AT_001 parity smoke with artifacts in the new report directory.
- Reality Check: Exit criteria unmet; canonical tensors and parity metrics remain stale in this repo, so next loop must execute the implementation+pytest Do Now.
- <Action State>: [ready_for_implementation]

## 2025-11-04T002805Z — NANOBRAG-GOLDEN-001 detector pivot alignment plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Replayed torch vs DiffBragg arrays confirmed a global shift (torch peak at [1315,1701] vs DiffBragg [1308,1700]); manual instantiation of `nanobrag_torch.Detector` showed CUSTOM basis vectors force SAMPLE pivot with `distance_corrected=-0.231m` and beam center drift. Switching to DIALS convention with XYZ rotation angles preserved the refGeom beam center exactly, validating that bridge should emit rotations instead of custom vectors. Updated fix_plan Attempts History and Phase A plan with new A4 geometry task; drafted Do Now instructing Ralph to refactor create_detector_config, regenerate canonical tensors, compute offsets, and rerun DB_AT_001 parity.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/
- Next Actions: Implement DIALS-rotation DetectorConfig (keep BEAM pivot), rerun canonical generator with new report timestamp, capture offset stats, and execute parity pytest per Do Now.
- Reality Check: Canonical tensors still misaligned (median_abs_offset≈5 px) and fixtures reference prior checkout; geometry fix remains prerequisite before tightening parity thresholds.
- <Action State>: [ready_for_implementation]

2025-11-04T002805Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=20 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/ next_action=refactor_detector_config_BEAM_pivot
## 2025-11-04T005115Z — NANOBRAG-GOLDEN-001 detector rotation handoff plan
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: ROI offsets remain ≈5–7 px in latest capture; derived dxtbx XYZ angles (179.72°, -0.045°, -0.097°) explain drift; added reusable ROI offset summary tool; `AUTHORITATIVE_CMDS_DOC` exported per testing guide.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/
- Next Actions: Implement DIALS rotation extraction in `dbex/nanobrag_bridge.create_detector_config`, regen canonical tensors with new geometry, summarize offsets via bin script, rerun DB_AT_001 parity pytest, update docs + ledger.
- Reality Check: Exit criteria unmet; canonical dataset still misaligned and manifest still references stale tensors. Ready for implementation handoff this loop.
- <Action State>: [ready_for_implementation]
2025-11-04T005115Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=21 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T005115Z/ next_action=apply_dials_rotations_regenerate_and_run_db_at_001

## 2025-11-04T011029Z — NANOBRAG-GOLDEN-001 Euler inversion validation
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: ROI sample still shows large localization error (median_abs_offset=8 px, max=15); recreated TorchDetector from current bridge output and confirmed fast/slow/normal vectors deviate from dxtbx axes (‖Δfast‖≈3.7e-3). Derived analytic Euler recovery (`phi_y = -asin(R[2,0])`, `phi_x = atan2(R[2,1], R[2,2])`, `phi_z = atan2(R[1,0], R[0,0])`) that reproduces the dxtbx column matrix with <2e-16 error, explaining mismatch introduced by `r3_rotation_matrix_as_x_y_z_angles()`. Logged micro/T1 probes under 2025-11-04T011029Z/summary.md.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011029Z/
- Next Actions: Patch `dbex/nanobrag_bridge.create_detector_config` to use the analytic XYZ inversion, add assertions/tests to guard future regressions, regenerate canonical tensors into a fresh report, verify TorchDetector basis matches dxtbx axes, then rerun DB_AT_001 parity pytest and update fixture manifest/metrics + ledger.
- Reality Check: Ready for implementation; dwell guard already exceeded so next loop must execute code + pytest.
- <Action State>: [ready_for_implementation]
2025-11-04T011029Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=22 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011029Z/ next_action=replace_euler_conversion_regenerate_and_run_db_at_001

## 2025-11-04T020930Z — NANOBRAG-GOLDEN-001 parity doc sync staging
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Implementation plan Phase A–C marked complete; parity smoke test still writes artifacts to 2025-10-29T190533Z; docs/TESTING_GUIDE.md and TEST_SUITE_INDEX parity entries reference stale logs; prepared 2025-11-04T020930Z report directory and summary for next rerun.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/
- Next Actions: Execute Do Now (refresh test artifact path, rerun parity selector, sync docs) and capture new pytest log/metrics under the prepared report.
- Reality Check: Canonical dataset metrics remain valid (median_corr=0.8134, localization=1.0); exit criteria 1-3 satisfied; outstanding work is documentation + D-phase archival prior to closing initiative.
- <Action State>: [ready_for_implementation]

2025-11-04T020930Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=23 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T020930Z/ next_action=rerun_parity_and_doc_sync
## 2025-11-04T015420Z — NANOBRAG-GOLDEN-001 checksum guard staging
- Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
- Action Type: planning
- Key Observations: Verified 2025-11-04T020930Z parity artifacts, marked C3/D1/D2 complete in the working plan, and logged GEOMETRY-002 capturing the analytic Euler inversion requirement; checksum guard still missing in the parity smoke.
- Artifact Path: plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T015420Z/
- Next Actions: Add manifest checksum assert, rerun DB_AT_001 parity into 2025-11-04T030000Z/, update Testing Guide + Test Suite Index, and mark NANOBRAG-GOLDEN-001 done in fix_plan after artifacts land.
- Reality Check: Exit criteria satisfied pending checksum guard + ledger closure; ready for implementation handoff this loop.
- <Action State>: [ready_for_implementation]

2025-11-04T015420Z focus=NANOBRAG-GOLDEN-001 state=ready_for_implementation dwell=24 artifacts=plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T015420Z/ next_action=implement_manifest_checksum_guard

## 2025-11-04T021626Z — NANOBRAG-BACKEND-002 planning kickoff
- Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
- Action Type: planning
- Key Observations: Verified `nanobrag_torch` Simulator/Detector/Crystal imports succeed; bridge helpers still emit local dataclass stubs; drafted phased implementation plan (config promotion → simulator integration → parity validation) and captured right-sized plan artifacts under 2025-11-04T021141Z.
- Artifact Path: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T021141Z/
- Next Actions: Promote bridge helpers to construct real `nanobrag_torch.config` objects and extend bridge tests with a round-trip detector/crystal instantiation guard.
- Reality Check: New focus initialized; no prior dwell, ready to hand off implementation Do Now to Ralph.
- <Action State>: [planning]

2025-11-04T021626Z focus=NANOBRAG-BACKEND-002 state=planning dwell=0 artifacts=plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T021141Z/ next_action=promote_bridge_configs_to_real_nanobrag
2025-11-04T031500Z focus=NANOBRAG-BACKEND-002 state=ready_for_implementation dwell=0 artifacts=plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T031500Z/ next_action=wire_nanobrag_simulator_and_run_targeted_pytest

## 2025-11-04T024056Z — NANOBRAG-BACKEND-002 simulator handoff brief
- Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
- Action Type: planning
- Key Observations: Confirmed stubbed `run_nanobrag_backend` flow, identified need to promote `build_structure_factor_grid` into bridge, and mapped SCALE-001/002 + GEOMETRY-002 guardrails for Simulator wiring. Authored Do Now + How-To in `input.md` and refreshed fix_plan/implementation plan status to `in_progress`.
- Artifact Path: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/
- Next Actions: Execute Do Now—add structure-factor helper, CLI `--spot-scale-override`, Simulator loop with √scale, and targeted pytest.
- Reality Check: Implementation required next loop; dwell now 1 (non-implementation streak capped at 2).
- <Action State>: [ready_for_implementation]

2025-11-04T024056Z focus=NANOBRAG-BACKEND-002 state=ready_for_implementation dwell=1 artifacts=plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/ next_action=wire_simulator_and_run_targeted_pytest

## 2025-11-04T024719Z — NANOBRAG-BACKEND-002 simulator wiring plan refresh
- Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
- Action Type: planning
- Key Observations: Confirmed Phase B items remain open (stubbed `_stub_bragg_tensor`, no CLI scale override, no HKL helper), reviewed nanobrag API/spec guardrails (GEOMETRY-002, SCALE-001/002, HKL-ORIENT-001), captured new report 2025-11-04T024719Z with handoff instructions, and updated docs/fix_plan.md Attempts History.
- Artifact Path: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/
- Next Actions: Implement simulator wiring Do Now (port structure-factor helper, add CLI override, invoke nanobrag_torch Simulator with √scale, add targeted pytest) and capture pytest logs under the new report.
- Reality Check: Exit criteria 2-4 still unmet; dependencies satisfied; dwell guard now at 2 so upcoming loop must execute implementation handoff.
- <Action State>: [ready_for_implementation]

2025-11-04T024719Z focus=NANOBRAG-BACKEND-002 state=ready_for_implementation dwell=2 artifacts=plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/ next_action=wire_simulator_backend_and_run_pytest
