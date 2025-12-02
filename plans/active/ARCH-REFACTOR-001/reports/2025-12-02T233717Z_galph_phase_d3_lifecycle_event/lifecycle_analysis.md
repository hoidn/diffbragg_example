# Lifecycle Event Analysis — ARCH-REFACTOR-001 Phase D.3

**Timestamp:** 2025-12-02T233717Z
**Event:** Implementation budget exhausted; escalation required per `<initiative_lifecycle/>`
**Galph Loop:** i=446
**Ralph Commit:** 6db57f45 (Phase D.3 bugfix implementation)

---

## Executive Summary

ARCH-REFACTOR-001 Phase D.3 (reconstruction baseline logic bugfix) has reached its implementation budget limit and triggered mandatory escalation per `<initiative_lifecycle/>` hard rules. Ralph correctly implemented the diagnosed fix (calibration baseline conditional logic in reconstruction.py:195-217), matching the normative pattern from stage_a.py:1194-1202 exactly. However, tests DB-AT-028/029 still FAIL with essentially identical signatures, revealing a **deeper architectural issue** beyond the originally diagnosed bug.

**Key finding:** The fix executes correctly (log_scale_baseline=20.14, scale_factor=5.57e8 as expected), but the simulator raw output is ~10^4.4× too small (1.8e-14 vs expected ~4.3e-10), suggesting systematic convention mismatch between training (Stage A) and reconstruction simulator construction.

**Lifecycle decision:** Mark Phase D.3 `blocked_pending_architecture` and open new `architecture` initiative to investigate and align simulator construction paths.

---

## Lifecycle Budget Tracking

### ARCH-REFACTOR-001 Phase D.3 Attempts (DB-AT-028/029 acceptance criteria)

1. **2025-12-02T000000Z (Galph planning)** — Problems ledger diagnosis, scoped fix, issued Do Now
2. **2025-12-02 (Ralph impl, commit 6db57f45)** — Implemented baseline logic, tests FAIL (same signature)
3. **2025-12-02T233717Z (this loop)** — Lifecycle escalation per repeat-failure guard

**Implementation loop count:** 1 (within budget)
**Blocked count:** 0 → 1 (escalating to blocked_pending_architecture)
**Acceptance criteria status:** FAIL (2 consecutive loops, same signature)

### Repeat-Failure Guard Triggered

Per `<loop_discipline/>` hard rule:
> If the same acceptance criterion fails in two consecutive loops with substantially the same failure signature, you must either
> (a) reclassify the root cause and switch to/open a fix-plan item that targets the suspected implementation defect (bug), or
> (b) document explicit evidence that only the gate/spec needs adjustment and then follow `<spec_change_flow/>`.

**Evidence review:**
- Loop 1 (diagnosis): identified missing baseline logic, cited spec violations (TOOLING-VIS-001 Phase D.C, DB-AT-027)
- Loop 2 (implementation): fix is **spec-compliant** and executes correctly, but tests still fail
- Failure signature: `bragg_after_mean ~1e-5` (should be ~0.24), `chi²/pixel initial ~1e5` (should be ≤1e2)

**Analysis:** This is **not** a gate/spec issue. The fix is correct per normative spec. The failure exposes a systemic architectural mismatch where reconstruction helpers build simulators differently than training stages, violating the `create_unified_simulator` factory contract.

**Decision:** Open `architecture` initiative per (a) above, targeting the simulator construction convention mismatch.

---

## Root Cause Re-Classification

### Original Diagnosis (problems.md, 2025-12-02T000000Z)

**Suspected bug:** `build_final_bragg_from_stage_a_telemetry` applies `log_scale` as absolute exponent, ignoring `log_scale_baseline`.

**Expected fix:** Add conditional baseline logic matching stage_a.py:1194-1202.

**Expected outcome:** `bragg_after_mean ≈ O(1) ≈ 0.24` (matching `bragg_before_mean`).

### Actual Outcome (Ralph findings, commit 6db57f45)

**Fix status:** ✓ Implemented correctly, executes as expected
**Test status:** ✗ FAIL (same signature as before fix)

**Debug evidence:**
```
log_scale_baseline_value = 20.138489594990745
log_scale_final = 5.549979675834038e-08
log_scale_effective_final = 20.13848965049054
scale_factor = exp(20.14) = 557230080.0  ← CORRECT

bragg_panel (simulator raw) mean = 1.839e-14  ← TOO SMALL
bragg_scaled (after scale_factor) = 1.025e-05  ← TOO SMALL

Expected bragg_after ≈ 0.24
Implies bragg_panel should be ≈ 0.24 / 5.57e8 ≈ 4.3e-10 (not 1.8e-14)
Missing factor: ~4.3e-10 / 1.8e-14 ≈ 23,900 ≈ 10^4.38
```

### New Root Cause Hypothesis

The simulator construction path in `build_final_bragg_from_stage_a_telemetry` (reconstruction.py:140-190) differs from Stage A's simulator construction in a way that produces outputs ~10^4.4× too small.

**Plausible mechanisms:**

1. **Spot-scale application mismatch:** Stage A may apply `spot_scale_override` at simulator construction time (baked into the forward model), while reconstruction builds simulators without it, expecting to apply scale post-hoc. The missing factor ~10^4.4 does not match `sqrt(spot_scale_override)=5.57e8`, so this may be a **double-counting** or **missing intermediate scale** issue.

2. **Warm vs. cold path divergence:** Stage A may reuse warm-cached simulators that have calibration-aware scaling baked in, while reconstruction always builds fresh simulators using the `create_unified_simulator` factory without calibration metadata threading.

3. **Telemetry structure assumptions:** The `param_deltas_a` dict may encode parameters in a normalized/pre-scaled form that the reconstruction helper misinterprets (e.g., `log_scale` already divided by baseline, or `q` parameters already adjusted for some gain factor).

4. **Factory contract violation:** `create_unified_simulator(..., spot_scale_override=None, ...)` may be incorrect; perhaps reconstruction should pass `calibration_metadata['spot_scale_override']` to the factory so simulators are built with the same conventions Stage A uses.

---

## Spec/Architecture Alignment Check

### Normative References

- **TOOLING-VIS-001 Phase D.C:** Log_scale baseline separation for calibrated runs (satisfied by fix)
- **DB-AT-027:** Stage A mapping parity with calibration metadata (violated by reconstruction helper)
- **ARCH-FACTORY-001:** Unified simulator factory contract (possibly violated)
- **docs/spec-db-core.md §§20-40:** Geometry/crystal/calibration contracts

### Contradiction Analysis

**Spec:** Calibration metadata (spot_scale_override, sigma, gain) must be applied consistently across training and reconstruction paths.

**Current implementation:**
- Stage A (training): Applies `spot_scale_override` → `log_scale_baseline = log(sqrt(spot_scale_override))` → learns `log_scale` as delta → final scale = exp(baseline + delta)
- Reconstruction (current): Extracts `log_scale_baseline` and `log_scale` from telemetry → computes scale = exp(baseline + delta) ← **CORRECT**

**But:** Simulator construction paths differ. Stage A builds simulators via warm cache or factory with calibration awareness; reconstruction builds via `create_unified_simulator(..., spot_scale_override=None)` and expects telemetry to carry all scaling.

**Violation:** The factory contract (ARCH-FACTORY-001) likely requires `spot_scale_override` to be passed during simulator construction, not applied post-hoc. Reconstruction violates this by omitting it.

---

## Initiative Type Decision

Per `<initiative_types/>`, this is an **architecture** issue, not a bugfix:

**Why not bugfix?**
- The diagnosed bug (missing baseline logic) was fixed correctly
- Tests still fail, revealing a **design flaw** in how reconstruction and training paths interact
- The fix exposed that the current architecture has **inconsistent simulator construction conventions**

**Why architecture?**
- Requires changing **structural boundaries** between factory, telemetry, and reconstruction
- Affects **interface contracts** (factory signature, telemetry structure, reconstruction helper API)
- Does not change external semantics (DB-AT tests should pass once internal conventions align)
- Scope: simulator construction, calibration threading, factory contract enforcement

---

## Lifecycle Transition

### From: ARCH-REFACTOR-001 Phase D.3
- **Status:** `in_progress` → `blocked_pending_architecture`
- **Blocked by:** New initiative `[ARCH-SIM-CONSTRUCTION-001]` (simulator construction convention alignment)
- **Reason:** Implementation budget exhausted (2 loops, same failure signature); fix correct but uncovered deeper issue
- **Attempts History entry:**
  ```
  * 2025-12-02T233717Z — Lifecycle escalation: Phase D.3 bugfix (commit 6db57f45) implemented correctly per spec (baseline logic matching stage_a.py:1194-1202), but tests DB-AT-028/029 still FAIL (bragg_after_mean=1.02e-05 vs expected O(1)=0.24). Debug evidence shows simulator raw output 10^4.4× too small (1.8e-14 vs expected 4.3e-10), suggesting systematic convention mismatch between training (Stage A) and reconstruction simulator construction paths. Marked Phase D.3 blocked_pending_architecture and opened [ARCH-SIM-CONSTRUCTION-001] to investigate factory contract, calibration threading, and warm/cold path alignment. See plans/active/ARCH-REFACTOR-001/reports/2025-12-02T233717Z_galph_phase_d3_lifecycle_event/lifecycle_analysis.md and ralph_findings.md (commit 6db57f45).
  ```

### To: New initiative [ARCH-SIM-CONSTRUCTION-001]
- **Type:** architecture
- **Title:** Simulator Construction Convention Alignment (Training vs Reconstruction)
- **Goals:**
  1. Ensure reconstruction helpers (`build_final_bragg_from_stage_*_telemetry`) build simulators with identical conventions as training stages (Stage A/B/C)
  2. Enforce factory contract: `create_unified_simulator` must apply calibration metadata (spot_scale_override, gain, sigma) at construction time, not post-hoc
  3. Validate DB-AT-028/029 pass once simulator outputs are aligned
- **Exit Criteria:**
  - [ ] Reconstruction simulator raw output magnitude matches Stage A simulator raw output (within 1% for same parameters)
  - [ ] DB-AT-028: `chi²/pixel initial ≤ 1e2`
  - [ ] DB-AT-029: `median ROI correlation before ≥ 0.2`
  - [ ] No changes to external API or test harness (internal alignment only)
- **Dependencies:** ARCH-FACTORY-001 (factory contract), TOOLING-VIS-001 (calibration semantics), DB-AT-027 (mapping parity)
- **Plan:** `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md` (to be created next loop)

---

## Evidence for Escalation

### Spec Compliance
- ✓ Fix matches normative pattern (stage_a.py:1194-1202)
- ✓ Calibration semantics correct (TOOLING-VIS-001 Phase D.C)
- ✓ Telemetry extraction correct (log_scale_baseline from param_deltas_a)
- ✓ Device/dtype handling correct
- ✓ Config defaults correct

### Implementation Quality
- ✓ Code review: logic sound, no syntax/import errors
- ✓ Debug instrumentation shows correct execution
- ✓ Arithmetic verified: scale_factor = 5.57e8 as expected

### Failure Persistence
- ✗ Tests FAIL with same signature after fix
- ✗ Simulator raw output ~10^4.4× too small
- ✗ Acceptance criteria not met (chi²/pixel, ROI correlation)

### Conclusion
**The diagnosed bug was real and is now fixed.** However, the fix revealed a **second, deeper bug** in the architectural conventions between training and reconstruction. Continuing implementation work under Phase D.3 would violate the implementation budget and obscure the root cause. Escalation to architecture initiative is mandatory per `<initiative_lifecycle/>`.

---

## Recommended Next Actions

1. **Mark ARCH-REFACTOR-001 Phase D.3 `blocked_pending_architecture`** in fix_plan.md
2. **Create new fix-plan row `[ARCH-SIM-CONSTRUCTION-001]`** (architecture initiative)
3. **Create implementation plan** at `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md`
4. **Update problems.md ledger:**
   - Close original entry (lines 26-60) with resolution summary + pointer to Phase D.3 commit
   - Add new entry describing simulator construction mismatch with pointer to new initiative
5. **Switch focus** to `[ARCH-SIM-CONSTRUCTION-001]` for next loop (evidence collection / callchain analysis)
6. **Update galph_memory.md** with lifecycle event, dwell reset, and new focus

---

## Artifacts

- Commit 6db57f45: Phase D.3 bugfix implementation (reconstruction.py baseline logic)
- Ralph findings: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`
- Test logs: `pytest_db_at_028_029.log` (FAIL signatures)
- Debug metrics: `at028/db_at_028_metrics.json`, `at029/db_at_029_metrics.json`
- This analysis: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T233717Z_galph_phase_d3_lifecycle_event/lifecycle_analysis.md`

---

## FSM State Transition

**Before:** `state=ready_for_implementation`, `dwell=1`, `focus=ARCH-REFACTOR-001 Phase D.3`
**After:** `state=gathering_evidence`, `dwell=0`, `focus=ARCH-SIM-CONSTRUCTION-001`

**Justification:** New architecture initiative requires evidence collection (callchain analysis, simulator construction comparison) before implementation. Dwell resets to 0 for new focus.
