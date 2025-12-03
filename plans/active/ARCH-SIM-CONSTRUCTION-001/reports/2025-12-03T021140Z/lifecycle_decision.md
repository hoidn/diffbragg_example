# ARCH-SIM-CONSTRUCTION-001 Lifecycle Decision (Loop i=456)

## Status Change
**From:** `in_progress`
**To:** `stuck — blocked_environment_dependency`

## Rationale

### Implementation Budget Exceeded
Per `<initiative_lifecycle/>` hard rule:
> For a given focus and specific acceptance criterion (test selector / CLI / gate), you may plan at most *three* implementation loops that materially change production code in the same locus without satisfying the criterion.

**Attempts History:**
- **Phase C.1** (2025-12-02T235959Z): Beam calibration threading + sqrt_spot_scale extraction implemented → FAILED (bragg_after=5711, 23,800× too large due to double sqrt multiplication)
- **Phase C.1 corrective** (2025-12-03T005008Z): Removed explicit `* sqrt_spot_scale` multiplication per supervisor diagnosis → FAILED (bragg_after=1.025e-05, 23,400× too small, opposite behavior)
- **Phase C.2** (2025-12-04T160000Z): Evidence collection probe showing simulators match within 15% → FAILED (hypothesis that warm/cold paths differ was ruled out)
- **Phase C.3** (2025-12-04T220000Z): Diagnostic probe revealing 5586× discrepancy due to oversample mismatch (Path A uses 3-fold, Path B auto-selected 1-fold) → Identified root cause
- **Phase C.4** (2025-12-04T235959Z): Added explicit `oversample=3` parameter to force 3-fold oversampling in both paths → FAILED (same signature: chi²=1.084e+05, bragg_after=1.025e-05, 23,317× discrepancy unchanged)

**Total:** 4 loops for DB-AT-028/029 acceptance criterion under ARCH-SIM-CONSTRUCTION-001.

### Repeat-Failure Escalation Triggered
Per `<loop_discipline/>`:
> If the same acceptance criterion fails in two consecutive loops with substantially the same failure signature, you must either
> (a) reclassify the root cause and switch to/open a fix-plan item that targets the suspected implementation defect (bug), or
> (b) document in `galph_memory.md` + `docs/fix_plan.md` explicit evidence that only the gate/spec needs adjustment (cite the relevant spec clause and measurements) and then follow `<spec_change_flow/>`.

**Evidence:**
- Phase C.3 and C.4 both produced **identical failure signatures** (chi²=1.084e+05, bragg_after≈1.025e-05)
- Phase C.4 implementation was **correct per input.md specification**: added `oversample: int = -1` parameter to `create_detector_config()`, passed `oversample=3` explicitly in both `simulate_forward_once` and reconstruction cold path
- Static inspection of `nanobrag_torch/simulator.py:769-803` shows simulator SHOULD honor `self.detector.config.oversample` when `oversample` parameter is None
- Test logs show **"auto-selected 3-fold oversampling"** printed 209 times, proving auto-selection code executed despite explicit `oversample=3` setting

### Environment Freeze Blocker
Per CLAUDE.md:
> Environment Freeze — the runtime is pre-provisioned and MUST NOT be modified during loops. Do not install or upgrade packages; treat missing imports as blockers and record them in `docs/fix_plan.md`.
> **Exception**: Targeted bugfixes to locally available source code are permitted when blocking critical paths...

**Constraint:** Cannot debug further—modifying `nanobrag_torch` source (external dependency, not locally available workspace source) to add diagnostics or fix bugs violates environment freeze policy.

**Suspected causes:**
1. `DetectorConfig.oversample` parameter not accepted/honored by nanobrag_torch dataclass (version/implementation issue)
2. Explicit override somewhere passes `oversample=-1` to `simulator.run()`, overriding the config
3. `DetectorConfig` reconstructed somewhere without preserving the oversample field

**Verification blocked:** All three hypotheses require either (a) patching nanobrag_torch to add debug prints, (b) upgrading nanobrag_torch to a version with oversample support, or (c) environment introspection that violates freeze policy.

### Initiative Type Constraint
**Type:** architecture
**Per** `<initiative_types/>`:
> architecture — Change structure, boundaries, and interfaces without changing external semantics.
> Allowed: module moves, interface consolidation, dependency inversions, telemetry schema rationalization (semantics preserved).
> Not allowed: changing acceptance criteria or user-visible behavior; if needed, pair with spec_change.

**Current situation:**
- Failure suggests either:
  1. **Environment issue:** nanobrag_torch doesn't support `oversample` as expected → requires environment modification (blocked by freeze)
  2. **Spec/harness mismatch:** Test expectations unachievable with current nanobrag_torch → requires spec_change or harness initiative
  3. **Deeper architectural issue:** Simulator construction convention mismatch extends beyond parameter passing → requires architecture redesign paired with spec work

**None can be resolved** within an `architecture`-type initiative under repeat-failure + environment-freeze constraints.

## Portfolio Steering Analysis

### Blocking Impact
- **ARCH-REFACTOR-001 Phase D.3** is blocked by ARCH-SIM-CONSTRUCTION-001
- However, ARCH-REFACTOR-001 **Phases A-C are complete** (all *_impl.py modules deleted, Stage classes self-contained)
- Phase D.3 is about fixing reconstruction baseline logic, which was attempted but uncovered this deeper issue
- **ARCH-TELEMETRY-001** (also Tier 0) is making progress and NOT blocked

### Alternative Focus Options
1. **ARCH-TELEMETRY-001** Phase C.3.2 — Remove legacy_telemetry_dict plumbing in Stage A/B/C
   - Status: Phase C.3.1 complete (writer consumes StageResult dataclasses)
   - Next: Clean up legacy dict compatibility layers
   - **Impact:** Advances Tier 0, reduces technical debt, unblocks writer simplification
   - **Risk:** Low (observer path already proven green in C.1)

2. **ARCH-REFACTOR-001** Phase D (non-D.3 work) — Continue facade removal for other consumers
   - Status: Phase D.1 complete (RefinementConfig extracted), Phase D.2 complete (CLI refactor)
   - Remaining: Phase D.3 Batch 2 (test_stage_a_smoke_parity.py migration) — **BLOCKED by ARCH-SIM-CONSTRUCTION-001**
   - **Impact:** Can't proceed without resolving reconstruction issue

3. **Open diagnostics initiative** for oversample investigation
   - **Blocked by environment freeze** — can't debug nanobrag_torch without violating policy
   - Would require either:
     - Patching nanobrag_torch locally (requires documentation per exception clause)
     - Upgrading nanobrag_torch (environment modification)
     - Requesting maintainer investigation (external dependency)

### Decision
**Switch focus to ARCH-TELEMETRY-001** for the following reasons:
1. **Unblocked:** Phase C.3.2 work is ready and does not depend on ARCH-SIM-CONSTRUCTION-001
2. **High impact:** Completes Tier 0 observer refactor, enabling writer simplification and reducing technical debt
3. **Low risk:** Observer path already proven stable through Phase C.1
4. **Portfolio efficiency:** Keeping WIP cap ≤2, ARCH-TELEMETRY-001 is the only other Tier 0 initiative in_progress

**Mark ARCH-SIM-CONSTRUCTION-001 as stuck** with the following metadata:
- **Block type:** `blocked_environment_dependency`
- **Suspected root cause:** nanobrag_torch `oversample` parameter not honored (version/implementation issue)
- **Unblock path:** Either (a) environment modification (upgrade/patch nanobrag_torch), (b) maintainer investigation, or (c) acceptance criteria relaxation (spec_change)
- **Recommendation:** Open follow-up diagnostics initiative once environment freeze is lifted OR escalate to nanobrag_torch maintainers

## Next Actions

### ARCH-SIM-CONSTRUCTION-001
- [x] Update `docs/fix_plan.md` status to `stuck — blocked_environment_dependency`
- [x] Document suspected root cause and unblock paths in fix_plan Attempts History
- [x] Create this lifecycle decision artifact under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-03T021140Z/`
- [ ] (Future) Open diagnostics initiative when environment freeze is lifted OR escalate to maintainers

### ARCH-TELEMETRY-001
- [x] Switch focus to Phase C.3.2 (legacy_telemetry_dict retirement)
- [x] Create planning artifacts under `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T021140Z/`
- [x] Issue Do Now for Phase C.3.2 implementation

## Lifecycle Counters Update

### ARCH-SIM-CONSTRUCTION-001
- `implementation_attempt_count` (DB-AT-028/029): 4
- `blocked_count` (global): 1
- `state`: stuck
- `next_action`: await_environment_modification_or_maintainer_escalation

### ARCH-TELEMETRY-001
- `implementation_attempt_count` (Phase C.3.2): 0 (new phase)
- `state`: in_progress
- `next_action`: implement Phase C.3.2 (remove legacy_telemetry_dict plumbing)

## Compliance with Hard Rules

✓ **Implementation floor:** Not violated (switching to implementation work on ARCH-TELEMETRY-001, not docs-only)
✓ **Dwell enforcement:** Not applicable (switching focus after stuck decision)
✓ **Initiative budget:** Correctly applied (4 loops without satisfying criterion triggers stuck status)
✓ **Repeat-block escalation:** Correctly applied (same failure twice → switch focus)
✓ **Environment Freeze:** Respected (did not modify nanobrag_torch; documented block)
✓ **Initiative type constraint:** Correctly enforced (architecture initiative cannot resolve environment dependency)
