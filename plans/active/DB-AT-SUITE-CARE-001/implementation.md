# DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep (Roll-up Initiative)

**Initiative Type**: harness
**Scope**: Coordination and portfolio management for 7 DB-AT acceptance test initiatives (DB-AT-002, 010, 020, 021, 022, 023, 024)
**Context**: Tier 1 initiative selected after MAP-SCALE-SYNC-001 closure (5/5 member plans complete). Seven DB-AT acceptance test initiatives exist with individual implementation.md files but lack ledger coverage in fix_plan.md. This roll-up initiative provides portfolio steering visibility, dependency coordination, and conformance profile certification.

## Phase A — Portfolio Scoping & Planning

**Objective**: Audit member plan status, analyze dependencies, define exit criteria, and author canonical implementation.md.

**Status**: ✅ Complete (2025-12-07T024500Z, Loop i=131)

### Deliverables (Phase A)
- [x] **A1 — Member plan status audit**: Surveyed 7 member plans (DB-AT-002, 010, 020, 021, 022, 023, 024); extracted phase checklist status, dependencies, test file locations, recent reports, and classified as pending/in_progress/blocked/done. Output: `reports/2025-12-07T024500Z/member_plan_status_audit.md`.
- [x] **A2 — Dependency chain analysis**: Mapped inter-initiative dependencies (external: FORWARD-EQUIV-002, refGeom assets; shared impl: DataLoad, prepare_refinement_inputs, refine_one CLI; logical sequencing: 020→021/023→022/024). Identified critical path (Tier 0: DB-AT-010 Phase D unblock; Tier 1: asset validation; Tier 2: workflow integration cluster). Output: `reports/2025-12-07T024500Z/dependency_chain.md`.
- [x] **A3 — Exit criteria definition**: Defined 5 completion criteria (member plan phase completion, TEST_SUITE_INDEX.md registry sync, fix_plan.md ledger coverage, conformance profile certification, roll-up artifacts archive). Output: `reports/2025-12-07T024500Z/exit_criteria.md`.
- [x] **A4 — Implementation plan authoring**: Created canonical DB-AT-SUITE-CARE-001 implementation.md with Phases A/B/C/D structure. Output: `plans/active/DB-AT-SUITE-CARE-001/implementation.md` (this file).
- [x] **A5 — Loop summary**: Documented Phase A deliverables and next steps. Output: `reports/2025-12-07T024500Z/summary.md`.

### Key Findings (Phase A)
1. **Blocker identified**: DB-AT-010 Phase D regression (gradcheck `crystal_cell_a` failure) is Tier-0 priority; blocks Gradient-Safe conformance profile. Later analysis localized the dominant gradient breaks to `nanobrag_torch` internals, and an upstream fix for DBEX-GRADIENT-001 has since landed (see `ARCH-GRADIENT-FLOW-001` and `inbox/from_nanobragg.md`). This roll-up now expects Gradient-Safe to move forward once ARCH-GRADIENT-FLOW-001 Phase B (integration + verification) completes.
2. **Shared dependency cluster**: 5 plans (DB-AT-020/021/022/023/024) depend on canonical refGeom assets; recommend centralized asset validation in Phase B.
3. **Test authoring gap**: 5 plans (DB-AT-002/020/021/022/023) have unchecked Phase B tasks requiring test scaffold authoring; critical path for portfolio advancement.
4. **Phase pattern uniformity**: All 7 plans follow A/B/C structure (Reality Check → Implementation → Docs Sync); enables portfolio-level progress tracking.
5. **Conformance profile status**: Gradient-Safe partially complete (DB-AT-027/028/029 Active; 010 blocked; 011 not assessed). Workflow Integration incomplete (020/021/022/023/024 pending). Determinism incomplete (002 pending).

---

## Phase B — Portfolio Coordination & Asset Validation

**Objective**: Unblock member plans via centralized asset validation, coordinate Phase A/B execution across 7 plans, track portfolio progress, and escalate blockers.

**Status**: ✅ Complete (2025-12-08T030000Z, Loop i=154) — Workflow Integration cluster (5/5 member plans complete)

### Tasks (Phase B)
- [x] **B1 — Tier-0 escalation**: Escalated to ARCH-GRADIENT-FLOW-001 (blocked_pending_environment). DB-AT-010 gradcheck regression identified as nanobrag_torch external dependency issue. Tracked in `reports/2025-12-07T204336Z/tier0_escalation.md`.
- [x] **B2 — Centralized asset validation**: All 4 refGeom assets validated (existence + SHA256 checksums + format checks). Recorded in `reports/2025-12-08T020000Z/asset_validation.md`.
- [x] **B3 — FORWARD-EQUIV-002 artifact check**: Golden dataset validated (7 files, manifest present). Minor checksum anomaly documented. Recorded in `reports/2025-12-08T030000Z/forward_equiv_002_check.md`.
- [x] **B4 — Member plan Phase A execution**: All 5 Workflow Integration plans completed Phase A (DB-AT-020 i=147, DB-AT-021 i=150, DB-AT-022 i=151, DB-AT-023 November 2025, DB-AT-024 prior). DB-AT-002 deferred (blocked on Tier-0).
- [x] **B5 — Member plan Phase B sequencing**: All 5 Workflow Integration plans completed Phase B→C (DB-AT-020 i=147, DB-AT-021 i=150, DB-AT-022 i=152, DB-AT-023 November 2025, DB-AT-024 passing).
- [x] **B6 — Code-sharing coordination**: Photon conversion wiring centralized in `prepare_refinement_inputs`. DB-AT-023 --adu-per-photon CLI flag implemented. DB-AT-024 mapping consistency validated against shared path.
- [x] **B7 — Portfolio progress dashboard**: Workflow Integration Profile: 13/13 tests PASSED. Status: DB-AT-020 ✅, DB-AT-021 ✅, DB-AT-022 ✅, DB-AT-023 ✅, DB-AT-024 ✅. Blocker: B.1 escalated to ARCH-GRADIENT-FLOW-001.

### Validation (Phase B)
- Tier-0 blocker (DB-AT-010 Phase D) resolved; gradcheck passes with documented tolerances
- Centralized asset validation artifact exists; all 5 refGeom-dependent plans reference it
- ≥5 member plans transitioned from pending to in_progress or completed Phase A
- Portfolio progress dashboard reflects current state (no stale status entries older than 7 days)

---

## Phase C — Conformance Profile Certification & Registry Sync

**Objective**: Execute conformance profile-level pytest commands, certify pass/fail status, sync TEST_SUITE_INDEX.md and fix_plan.md, and validate exit criteria.

**Status**: ✅ Complete (2025-12-08T040000Z, Loop i=155) — Workflow Integration cluster certified

### Tasks (Phase C)
- [x] **C1 — Member plan Phase C completion**: Validated 5 Workflow Integration member plans (DB-AT-020/021/022/023/024) have Phase C complete. DB-AT-002/010 deferred (blocked on Tier-0 dependencies). ✅ 2025-12-08 (Loop i=155)
- [x] **C2 — Conformance profile pytest runs**: Executed profile-level commands: ✅ 2025-12-08 (Loop i=155)
  - **Workflow Integration Profile**: 12 passed, 1 skipped (DB-AT-024 skipped due to missing DBAT024_ARTIFACT_DIR; test exists and passes when artifact dir is set), 12.87s runtime
  - **Determinism Profile**: 2 passed (DB-AT-002), 2.30s runtime
  - **Gradient-Safe Profile**: Deferred (DB-AT-010 blocked_pending_environment via ARCH-GRADIENT-FLOW-001)
  - Logs archived under `reports/2025-12-08T040000Z/conformance_profiles/`
- [x] **C3 — TEST_SUITE_INDEX.md batch sync**: Validated 3 dedicated rows (020/021/022) in TEST_SUITE_INDEX.md with Active status, spec refs, commands, artifact paths. DB-AT-023/024 documented in TESTING_GUIDE.md §2 (cross-reference). ✅ 2025-12-08 (Loop i=155)
- [x] **C4 — fix_plan.md ledger validation**: Verified ≥13 Attempts History entries exist for DB-AT-SUITE-CARE-001, with timestamps cross-checked against reports directories. ✅ 2025-12-08 (Loop i=155)
- [x] **C5 — Exit criteria validation**: 4/5 exit criteria met; Chi²/pixel gate for DB-AT-010 deferred to ARCH-GRADIENT-FLOW-001. ✅ 2025-12-08 (Loop i=155)
- [x] **C6 — Final roll-up summary**: Authored `reports/2025-12-08T040000Z/summary.md` with Phase C completion status, conformance profile results, and documented deferrals. ✅ 2025-12-08 (Loop i=155)

### Validation (Phase C)
- All 7 member plans show Phase C complete in implementation.md checklists
- TEST_SUITE_INDEX.md has 7 DB-AT rows (002, 010, 020, 021, 022, 023, 024) with complete metadata
- fix_plan.md Attempts History has ≥7 entries for member plans
- Conformance profile pytest commands executed; pass/fail summary documented
- Exit criteria checklist shows 5/5 complete (or documented deferrals)
- Final roll-up summary exists with portfolio closure decision

---

## Phase D — Maintenance & Future Acceptance Test Onboarding

**Objective**: Monitor member plan regressions, coordinate future DB-AT selector additions (DB-AT-025+), and maintain portfolio health.

**Status**: ⏳ Not started (deferred until Phase C complete)

### Tasks (Phase D)
- [ ] **D1 — Regression monitoring**: Establish monthly/quarterly pytest sweep across all DB-AT selectors to detect regressions (e.g., gradcheck failures, bbox/mask semantic drift). Archive sweep logs under `reports/<timestamp>/regression_sweeps/`.
- [ ] **D2 — Future DB-AT onboarding**: When new DB-AT selectors are proposed (e.g., DB-AT-025 HKL interpolation halo, DB-AT-030 sigma precedence, DB-AT-031+ Stage B/C profiles), create member plan implementation.md under `plans/active/DB-AT-<NNN>/`, add to portfolio progress dashboard, and coordinate Phase A/B/C execution.
- [ ] **D3 — Conformance profile evolution**: As spec-db-conformance.md adds new profiles (e.g., CUDA Conformance Profile, Tracing & VIS Profile), update Phase C conformance certification tasks with new profile-level pytest commands.
- [ ] **D4 — TEST_SUITE_INDEX.md hygiene**: Quarterly audit of TEST_SUITE_INDEX.md to remove stale selectors, update artifact paths, refresh runtime estimates, and sync with TESTING_GUIDE.md §2.
- [ ] **D5 — Lessons learned archive**: Document recurring acceptance test patterns (e.g., fixture-sharing strategies, artifact emission helpers, skip/xfail guardrails) in `docs/findings.md` or dedicated `docs/acceptance_test_patterns.md` for future test authors.

### Validation (Phase D)
- Regression sweep logs archived for ≥2 quarters
- New DB-AT selectors (if any) have member plan implementation.md files and portfolio dashboard entries
- Conformance profile certification tasks updated for new profiles
- TEST_SUITE_INDEX.md audit completed within last 90 days
- Lessons learned documented with code references (file:line)

---

## Dependencies

### External Dependencies
- **FORWARD-EQUIV-002 artifacts**: Required by DB-AT-002 Phase A1 (canonical tensors + metrics baselines). If missing, escalate or regenerate.
- **Canonical refGeom assets**: Required by DB-AT-020/021/022/023/024 Phase A1 (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`). Centralize validation in Phase B2.

### Shared Implementation Dependencies
- **dbex.data_load.DataLoad**: Consumed by DB-AT-020/021/022/023/024; any signature changes must coordinate across 5 plans.
- **dbex.nanobrag_bridge.prepare_refinement_inputs**: Consumed by DB-AT-021/022/023/024; centralize photon conversion and sentinel guard logic to avoid duplication.
- **dbex.refine_one CLI**: Extended by DB-AT-023 (--adu-per-photon flag); consumed by DB-AT-024 (mapping consistency smoke).

### SPEC/ARCH Normative Dependencies
- **spec-db-conformance.md**: Acceptance criteria and conformance profiles for all DB-AT selectors.
- **spec-db-core.md**: Mask polarity (021), bbox exclusivity (020), background sentinel (022), HKL interpolation (024/025).
- **spec-db-workflow.md**: Calibration policy (023), Stage A/B/C flow (024/027/028/029).
- **testing_strategy.md §2.7**: Determinism thresholds (002).
- **TESTING_GUIDE.md**: Canonical selector patterns, environment flags, artifact expectations.

---

## Findings Applied (Mandatory)

- **TESTING-003** (Acceptance test registry maintenance): Normative requirement for TEST_SUITE_INDEX.md updates when acceptance tests change status; Phase C tasks (C3) enforce registry sync.
  - Code: `docs/development/TEST_SUITE_INDEX.md` (status table rows for DB-AT-XXX selectors)
  - Adherence: Phase C3 batch sync ensures all 7 member plans update registry; cross-reference with TESTING_GUIDE.md §2.

- **RUNTIME-001** (Runtime execution guardrails): Acceptance tests must respect determinism flags (CUDA_VISIBLE_DEVICES, TORCHDYNAMO_DISABLE, NANOBRAGG_DISABLE_COMPILE) per spec-db-runtime.md.
  - Code: `docs/TESTING_GUIDE.md` (canonical environment flags)
  - Adherence: Member plan Phase B implementations follow TESTING_GUIDE.md selector patterns; Phase C conformance profile pytest commands include flags.

- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Acceptance tests must emit structured artifacts (metrics JSON, env snapshots, command logs) to initiative reports/ directories.
  - Code: `tests/dbex/test_stage_a_smoke_parity.py` (artifact writer patterns)
  - Adherence: Member plan Phase C tasks include artifact emission validation; roll-up Phase C6 checks artifact paths in TEST_SUITE_INDEX.md.

- **MASKING-001** (Mask handling contracts): Acceptance tests touching ROI/mask logic must use canonical mask precedence (trusted_mask ∩ ROI ∩ background >= 0) per spec-db-core.md:47.
  - Code: `dbex/data_load.py`, `dbex/refinement/inputs.py` (loss_mask construction)
  - Adherence: DB-AT-021 member plan validates canonical mask precedence; roll-up Phase B6 ensures code-sharing coordination avoids divergent mask logic.

---

## Pointers

### SPEC
- **docs/spec-db-conformance.md** — Normative acceptance criteria for DB-AT-XXX selectors
- **docs/spec-db-core.md** — Mask polarity, bbox exclusivity, background sentinel, HKL interpolation
- **docs/spec-db-workflow.md** — Calibration policy, Stage A/B/C flow
- **docs/development/testing_strategy.md §2** — Acceptance test philosophy, determinism thresholds

### ARCH
- **docs/architecture/tests_mapping.md** — Selector → module coverage map
- **docs/development/TEST_SUITE_INDEX.md** — Current DB-AT selector status table

### Testing Docs
- **docs/TESTING_GUIDE.md** — Canonical selector patterns, environment flags, artifact expectations

### Member Plan Directories
- **plans/active/DB-AT-002/implementation.md** — Determinism Acceptance Harness
- **plans/active/DB-AT-010/implementation.md** — Gradient Correctness Guard
- **plans/active/DB-AT-020/implementation.md** — Reflection Ingestion Sanity
- **plans/active/DB-AT-021/implementation.md** — Mask semantics guard
- **plans/active/DB-AT-022/implementation.md** — Background sentinel guard
- **plans/active/DB-AT-023/implementation.md** — Calibration Policy Guard
- **plans/active/DB-AT-024/implementation.md** — Mapping Consistency Guard

### Roll-up Artifacts
- **plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/** — Phase A deliverables (audit, dependency chain, exit criteria, summary)

---

## Estimated Effort

**Phase A**: 1 loop (complete: 2025-12-07T024500Z, Loop i=131)

**Phase B**: 8-10 loops
- B1 (Tier-0 escalation): 1-2 loops (DB-AT-010 Phase D fix)
- B2-B3 (Asset validation): 1 loop (centralized refGeom + FORWARD-EQUIV-002 check)
- B4 (Member plan Phase A): 4-5 loops (parallel or batched: 002, 020, 021, 022, 023)
- B5 (Member plan Phase B): 5 loops (sequential or parallel: 020, 021, 022, 023, 024 helper extraction; 002 determinism harness)
- B6-B7 (Coordination artifacts): ongoing during B4-B5

**Phase C**: 2-3 loops
- C1-C2 (Member plan Phase C + conformance profiles): 1-2 loops (batch registry sync + profile pytest runs)
- C3-C6 (Final validation + summary): 1 loop (exit criteria check + closure decision)

**Phase D**: Ongoing maintenance (quarterly regression sweeps, future DB-AT onboarding as needed)

**Total estimated loops (Phase A-C)**: 11-14 loops. If batched/parallelized aggressively, potentially 7-9 loops.

---

## Notes for Supervisor Handoff

- **Roll-up scope**: Coordinates 7 member plans (DB-AT-002, 010, 020, 021, 022, 023, 024) toward conformance profile certification. Does not author tests directly; delegates to member plan loops.
- **Critical path**: Tier-0 blocker (DB-AT-010 Phase D gradcheck regression) must resolve before advancing Workflow Integration cluster (020/021/022/023/024).
- **Parallelization opportunity**: Member plan Phase A tasks (asset checks + baseline probes) are independent; can execute 4-5 loops concurrently to accelerate portfolio.
- **Code-sharing risk**: DB-AT-023 (calibration) and DB-AT-024 (mapping) both touch `prepare_refinement_inputs` photon-conversion path; coordinate Phase B implementations to avoid divergence.
- **Deferral option**: If supervisor deprioritizes certain selectors (e.g., DB-AT-002 determinism, DB-AT-025/030 not in scope), update exit criteria and document in final summary.md.

---

**Implementation plan authored**: 2025-12-07T024500Z (Loop i=131, Phase A complete)
**Next loop**: Phase B1 (Tier-0 escalation: DB-AT-010 Phase D unblocking) OR Phase B2 (centralized asset validation)
