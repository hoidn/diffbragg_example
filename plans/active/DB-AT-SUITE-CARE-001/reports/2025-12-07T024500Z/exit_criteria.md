# Exit Criteria (DB-AT-SUITE-CARE-001 Phase A)

**Date**: 2025-12-07T024500Z
**Scope**: Completion criteria for DB-AT-SUITE-CARE-001 acceptance suite upkeep roll-up initiative

## Roll-up Initiative Exit Criteria

The DB-AT-SUITE-CARE-001 roll-up initiative is complete when **all 5 criteria** below are satisfied:

### 1. Member Plan Phase Completion (Normative)
**Definition**: All 7 member plans (DB-AT-002, 010, 020, 021, 022, 023, 024) have completed Phases A, B, and C per their implementation.md checklists.

**Validation**:
- Each member plan's implementation.md shows all Phase A/B/C tasks checked (`[x]`)
- Each member plan has a passing pytest selector recorded in its final Phase C report artifacts
- No member plan is in `blocked` status with unresolved escalations

**Measurement**:
- Current status (2025-12-07): 1/7 plans blocked (DB-AT-010 Phase D regression); 1/7 in_progress (DB-AT-024 Phase B partial); 5/7 pending (Phase A/B not started)
- Target: 7/7 plans with Phase C complete and Active selector status in TEST_SUITE_INDEX.md

**Blocker escalation path**: If a member plan cannot complete due to out-of-scope issues (e.g., missing SPEC clarification, blocked external dependency), document in `docs/fix_plan.md` and escalate to supervisor; roll-up may close with that plan deferred if remaining 6 plans are complete and the blocker is tagged for future initiative.

---

### 2. TEST_SUITE_INDEX.md Registry Sync (Normative per TESTING-003)
**Definition**: `docs/development/TEST_SUITE_INDEX.md` accurately reflects the status of all 7 DB-AT selectors with complete metadata.

**Validation**:
- Each DB-AT-{002,010,020,021,022,023,024} selector has a row in TEST_SUITE_INDEX.md with:
  - Status: `active` (if tests passing) or `active (xfail)` (if guarded) or `blocked` (with blocker noted)
  - Spec Reference: citations to normative docs (spec-db-conformance.md, spec-db-core.md, spec-db-workflow.md, etc.)
  - Notes: canonical command, environment flags, artifact paths, runtime estimates, applied findings
- No stale/draft selectors without implementation evidence
- Cross-reference with TESTING_GUIDE.md §2 acceptance test table for consistency

**Measurement**:
- Current status (2025-12-07): DB-AT-002 through DB-AT-024 not yet in TEST_SUITE_INDEX.md (registry update deferred to member plan Phase C tasks)
- Target: 7 new/updated rows in TEST_SUITE_INDEX.md matching member plan final Phase C artifacts

**Automation option**: Consider generating TEST_SUITE_INDEX.md rows from member plan Phase C artifacts programmatically if structure is uniform (selector, status, spec refs, notes).

---

### 3. Fix Plan Ledger Coverage (Normative per initiative selection criteria)
**Definition**: `docs/fix_plan.md` Attempts History includes entries for all 7 member plans documenting Phase B/C execution.

**Validation**:
- Each member plan has ≥1 Attempts History entry in `docs/fix_plan.md` capturing:
  - Timestamp, initiative ID, change summary (Phase B implementation + Phase C validation)
  - Mapped pytest selector(s) and test outcome (PASS/XFAIL/SKIP with justification)
  - Key metrics (if applicable: correlation, RMSE, gradcheck tolerances, coverage %, etc.)
  - Flags (if applicable: blocked, cliff, out-of-scope, regression)
- Ledger entries align with member plan Phase C reports (no orphaned reports without ledger record)

**Measurement**:
- Current status (2025-12-07): No DB-AT-{002,010,020,021,022,023,024} entries in fix_plan.md yet (member plans not executed)
- Target: ≥7 Attempts History entries (1 per plan minimum; may be multiple if Phase D or rework loops occurred)

**Cross-check**: Compare `docs/fix_plan.md` entries with `plans/active/DB-AT-*/reports/` directory timestamps; every timestamped report should map to a ledger entry.

---

### 4. Conformance Profile Certification (Normative per spec-db-conformance.md)
**Definition**: All conformance profiles defined in `docs/spec-db-conformance.md` that include DB-AT-{002,010,020,021,022,023,024} selectors can be executed and produce actionable pass/fail evidence.

**Validation**:
- **Gradient-Safe Profile** (DB-AT-010, 011, 027, 028, 029):
  - DB-AT-010 selector passes (or xfail with documented hypothesis)
  - DB-AT-011 (graph breaks guard): validate test exists and passes
  - DB-AT-027/028/029 (Stage A zero-point/loss/structure parity): validate tests exist and pass (per TEST_SUITE_INDEX.md, these are already Active as of 2025-11-24/25)
  - Profile-level command documented in TESTING_GUIDE.md or spec-db-conformance.md
- **Workflow Integration Profile** (DB-AT-020, 021, 022, 023, 024, 025, 030):
  - DB-AT-020/021/022/023/024 selectors pass (this roll-up's scope)
  - DB-AT-025 (HKL interpolation halo): validate test exists (deferred if not in member plan scope)
  - DB-AT-030 (sigma precedence): validate test exists (deferred if not in member plan scope)
  - Profile-level command documented
- **Forward Equivalence Profile** (DB-AT-001):
  - Not in this roll-up's scope; verify DB-AT-001 status unchanged (or note if this roll-up affects it)
- **Determinism Profile** (implicitly DB-AT-002):
  - DB-AT-002 selector passes with documented thresholds (same-seed corr ≥0.9999999, diff-seed corr ≤0.7, ≥50% differing pixels)

**Measurement**:
- Current status (2025-12-07): Gradient-Safe profile partially complete (027/028/029 Active; 010 blocked Phase D; 011 not assessed). Workflow Integration profile incomplete (020/021/022/023/024 pending; 025/030 not assessed). Determinism profile incomplete (002 pending).
- Target: Gradient-Safe profile fully Active (010 unblocked + 011 validated); Workflow Integration profile Active for 020/021/022/023/024 (025/030 deferred if out of scope); Determinism profile Active (002 complete).

**Evidence**: Conformance profile certification artifacts under `plans/active/DB-AT-SUITE-CARE-001/reports/<final-timestamp>/conformance_profiles/` with profile-level pytest commands + pass/fail summary.

---

### 5. Roll-up Artifacts Archive (Process requirement)
**Definition**: All roll-up planning and coordination artifacts are persisted under `plans/active/DB-AT-SUITE-CARE-001/reports/` for portfolio steering visibility.

**Validation**:
- Phase A artifacts exist (this loop's deliverables):
  - `member_plan_status_audit.md` (7-plan status table + detailed findings)
  - `dependency_chain.md` (dependency graph + critical path + priority ordering)
  - `exit_criteria.md` (this file)
  - `summary.md` (Phase A loop summary)
- Phase B artifacts (future loop):
  - Centralized asset validation report (refGeom availability + checksums)
  - Portfolio progress dashboard (member plan phase completion matrix)
- Phase C artifacts (future loop):
  - Conformance profile certification report (profile-level pytest runs + pass/fail summary)
  - Final roll-up summary with portfolio closure decision (all plans complete OR documented deferrals)
- `implementation.md` exists at `plans/active/DB-AT-SUITE-CARE-001/implementation.md` with Phases A/B/C/D structure documenting roll-up execution plan

**Measurement**:
- Current status (2025-12-07): Phase A artifacts in progress (member_plan_status_audit.md ✓, dependency_chain.md ✓, exit_criteria.md ✓, implementation.md pending, summary.md pending)
- Target: All Phase A/B/C artifacts present; implementation.md complete; final summary.md with closure decision

**Archival note**: Roll-up artifacts serve as portfolio steering evidence and should be referenced in supervisor handoff docs when DB-AT-SUITE-CARE-001 closes.

---

## Completion Checklist (Summary)

- [ ] **Criterion 1**: All 7 member plans Phase A/B/C complete (0/7 as of 2025-12-07)
- [ ] **Criterion 2**: TEST_SUITE_INDEX.md has 7 DB-AT rows with complete metadata (0/7 as of 2025-12-07)
- [ ] **Criterion 3**: fix_plan.md Attempts History has ≥7 entries for member plans (0/7 as of 2025-12-07)
- [ ] **Criterion 4**: Conformance profiles certified (Gradient-Safe: 3/5 Active, 1 blocked, 1 not assessed; Workflow Integration: 0/7 Active; Determinism: 0/1 Active)
- [ ] **Criterion 5**: Roll-up artifacts archived (Phase A: 3/5 complete; Phase B/C: not started)

**Estimated completion**: Based on dependency_chain.md priority ordering, completion requires 10-12 engineer loops (1 Tier-0 unblock + 4-5 Phase A + 5 Phase B + 1-2 Phase C batched). If batched/parallelized, potentially 6-8 loops.

**Early exit condition**: If supervisor deprioritizes certain member plans (e.g., defer DB-AT-002 determinism to future initiative), update Criterion 1 to reflect reduced scope (e.g., "6/7 plans complete; DB-AT-002 deferred per supervisor decision XYZ") and document in final summary.md.

---

**Exit criteria defined**: 2025-12-07T024500Z
**Next artifact**: implementation.md (canonical DB-AT-SUITE-CARE-001 roll-up plan)
