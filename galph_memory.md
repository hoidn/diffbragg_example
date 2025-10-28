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
