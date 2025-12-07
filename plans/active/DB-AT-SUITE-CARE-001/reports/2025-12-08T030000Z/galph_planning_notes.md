# DB-AT-SUITE-CARE-001 Phase B.3 — FORWARD-EQUIV-002 Artifact Check

**Loop**: i=144 (Galph supervisor planning)
**Date**: 2025-12-08T03:00:00Z
**Phase**: B.3 — External Dependency Validation
**Action**: evidence_collection
**DecisionStatus**: patch_ready

---

## Context

**Prior Loop (i=143, Ralph)**:
- Completed Phase B.2 (centralized asset validation)
- Validated 4 canonical refGeom assets: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`
- All assets VALID (checksums established, format checks passed)
- Output: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/` with 4 artifacts

**Current Focus**:
- Phase B.3: Validate FORWARD-EQUIV-002 external dependency for DB-AT-002 Phase A1
- Target directory: `tests/fixtures/golden_data/simple_cubic/`
- Expected assets: `manifest.json` + `.npy` tensor payloads
- Prerequisite for DB-AT-002 member plan progression

**Portfolio Status**:
- **Tier 0**: Exhausted (all done/blocked)
  - ARCH-GRADIENT-FLOW-001: blocked_pending_environment (i=141 lifecycle decision)
  - Others: done/archived
- **Tier 1 (Current)**: DB-AT-SUITE-CARE-001 Phase B ongoing
  - Phase A: ✅ Complete (i=131)
  - Phase B.1: Escalated to ARCH-GRADIENT-FLOW-001 (now blocked)
  - Phase B.2: ✅ Complete (i=143)
  - Phase B.3: ⏳ This loop (i=144)

---

## Objectives

**Primary Goal**: Validate that FORWARD-EQUIV-002 artifacts exist and are usable by DB-AT-002 Phase A1.

**Validation Steps**:
1. Directory existence check: `tests/fixtures/golden_data/simple_cubic/`
2. Manifest verification: `manifest.json` presence, checksum, co-located `.npy` payloads
3. Tensor inventory: List all `.npy` files with sizes/timestamps
4. Status classification: Case A (all valid) / B (manifest missing) / C (manifest broken) / D (directory missing)

**Deliverables** (under `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/`):
1. `forward_equiv_002_check.md` — Primary validation report
2. `ls_golden_data.txt` — Directory listing
3. `manifest_verification.txt` — Checksum comparison (if manifest exists)
4. `summary.md` — Loop summary with outcome and next steps

---

## Risk Assessment

**Likely Outcome (Case A)**: Manifest + tensors exist and valid → proceed to Phase B.4 (member plan Phase A coordination)

**Risk Scenarios**:
- **Case B** (manifest missing): Escalate to FORWARD-EQUIV-002 owner; DB-AT-002 blocked
- **Case C** (manifest broken/foreign paths): Recommend regeneration via `scripts/generate_simple_cubic_golden.py`
- **Case D** (directory missing): CRITICAL escalation; FORWARD-EQUIV-002 must regenerate golden suite

**Mitigation**:
- If Case B/C/D, switch next loop focus to Phase B.4 for DB-AT-020/021/023/024 (which do NOT depend on FORWARD-EQUIV-002)
- Cross-link blocker to FORWARD-EQUIV-002 owner plan
- Update fix_plan.md with blocker classification

---

## Applied Constraints

**Non-Negotiables (from galph_prompt)**:
- ✅ No production edits by Galph
- ✅ Evidence→Action contract: recommend concrete next action
- ✅ Type discipline: harness initiative (asset validation, not test implementation)
- ✅ Scriptization policy: shell commands only (no plan-local `.py` scripts per PROBE-FREEZE-001)

**Initiative Typing**:
- Type: harness (portfolio coordination)
- Mode: none (evidence collection, not test execution)
- Action: evidence_collection (external dependency validation)

**Lifecycle**:
- Dwell: 0 (new subtask; Phase B.3 first attempt)
- Decision: patch_ready (routine validation, confidence 0.98)
- Budget: Well within Phase B limits (3 implementation loops allowed; this is evidence)

---

## Findings Applied

**MANIFEST-001** (Canonical manifest emission):
- Validation protocol: check manifest.json + co-located `.npy` payloads
- Ownership: `scripts/generate_simple_cubic_golden.py:620-717`
- Adherence: Phase B.3 checks for foreign paths per MANIFEST-001 guidance

**DIAGNOSTICS-001** (Diagnostic artifact expectations):
- All 4 deliverables emitted under timestamped reports directory
- Structured artifact pattern for cross-referencing

**No other findings relevant** — Asset validation only; no refinement/physics/gradient code touched.

---

## Next Loop Decision Tree

**If Case A (all valid)**:
- Next loop: Phase B.4 (member plan Phase A coordination)
- Focus: DB-AT-002/020/021/022/023 Phase A execution
- Action: implementation_ready (coordinate 4-5 member plan Phase A loops)

**If Case B/C (manifest missing/broken)**:
- Next loop: Switch to Phase B.4 for DB-AT-020/021/023/024 (unblocked by Phase B.2)
- Secondary: Escalate to FORWARD-EQUIV-002 owner for DB-AT-002 unblocking
- Action: review_or_housekeeping (blocker triage + portfolio re-sequencing)

**If Case D (directory missing)**:
- Next loop: CRITICAL escalation to FORWARD-EQUIV-002 owner
- Alternative focus: Phase B.4 for DB-AT-020/021/023/024
- Action: planning (regeneration coordination)

---

## Galph Checklist (Pre-Delegation)

- [x] Startup steps complete (git pull, docs read, problems.md reviewed)
- [x] Focus selection: DB-AT-SUITE-CARE-001 Phase B.3 from Tier 1
- [x] Non-negotiables applied (no production edits, evidence→action, type discipline)
- [x] Loop discipline checked (dwell=0, budget OK, implementation floor N/A)
- [x] Findings applied (MANIFEST-001, DIAGNOSTICS-001)
- [x] input.md written with validity contract (objectives, tasks, deliverables, If Blocked)
- [x] galph_memory.md updated (loop i=144 entry prepended)
- [x] Artifacts directory created: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T030000Z/`

**Ready to delegate to Ralph** (loop i=144, engineer agent).

---

**Next milestone**: Phase B.4 (member plan Phase A coordination) — pending Phase B.3 outcome.
