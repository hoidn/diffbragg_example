# Member Plan Status Audit — TORCH-REFINE-CLEANUP-001 Phase A

**Audit Date:** 2025-12-08T150000Z
**Auditor:** Ralph (i=186)
**Scope:** 6 TORCH-REFINE member plans (001/002/002D/002E/003/004)

---

## Status Matrix

| Plan ID | Current Status | Phases Complete | Remaining Phases | Classification |
|---------|---------------|-----------------|------------------|----------------|
| TORCH-REFINE-001 | substantial_progress | A1-A3 | B1-B2, C1-C2 | **revive** |
| TORCH-REFINE-002 | done (delegated) | P1.1-P3.2 | P4.1-P4.3 → 002D | N/A (see 002D) |
| TORCH-REFINE-002D | in_progress | P0.1, P1.1-P1.3 | P2.1-P2.2, P3.1-P3.2 | **revive** |
| TORCH-REFINE-002E | in_progress | A0, A2-A3, B1 | B2-B5, C1-C3 | **blocked** |
| TORCH-REFINE-003 | pending | None | P0-P4 (all) | **blocked** |
| TORCH-REFINE-004 | done | All phases | None | **archive** |

---

## Detailed Audit by Plan

### TORCH-REFINE-001 — LBFGS Refinement Nucleus (Stage A)

**Source:** `plans/active/TORCH-REFINE-001/implementation.md`

**Phases Verified:**
- [x] A1: Nucleus implementation (`run_nanobrag_refinement`) — COMPLETE
- [x] A2: Telemetry emission to `/torch_diagnostics` — COMPLETE
- [x] A3: Minimal pytest smoke test — COMPLETE (Outcome: 2025-11-05T024454Z, ~0.15% improvement)
- [ ] B1: Periodic full-frame validations + `loss_trace_full` — PENDING
- [ ] B2: Stage expansion prep (parameter groups, learning rates) — PENDING
- [ ] C1: Backend flag/mode for nucleus — PENDING
- [ ] C2: Docs sync (fix_plan, TESTING_GUIDE) — PENDING

**Classification:** `revive`
- No Tier 0 blockers affect this work
- Moderate complexity (validation scheduling, CLI wiring)
- Can proceed independently of other member plans

---

### TORCH-REFINE-002 — Stage A Expansion (Full Crystal + Orientation)

**Source:** `plans/active/TORCH-REFINE-002/implementation.md`

**Phases Verified:**
- [x] P1.1-P1.3: Parameter surface + warm-starts — COMPLETE
- [x] P2.1-P2.3: Telemetry + safety rails — COMPLETE
- [x] P3.1-P3.2: Test + docs sync — COMPLETE
- [ ] P4.1-P4.3: Deterministic miscalibration + gate rebaseline — **DELEGATED to TORCH-REFINE-002D**

**Classification:** `done (delegated)`
- Phases 1-3 delivered the Stage A expansion with full crystal + orientation
- Phase 4 (HKL perturbation dataset) explicitly tracked in TORCH-REFINE-002D
- No further work needed in this plan

---

### TORCH-REFINE-002D — Stage A HKL-aware Perturbation Dataset

**Source:** `plans/active/TORCH-REFINE-002D/implementation.md`

**Phases Verified:**
- [x] P0.1: HKL metadata probe — COMPLETE (hkl_probe.json captured)
- [x] P1.1: ±1 halo support in `build_structure_factor_grid` — COMPLETE
- [x] P1.2: Interpolation toggle in Stage A config — COMPLETE
- [x] P1.3: Smoke harness with haloed grid — COMPLETE
- [ ] P2.1: Remove `pytest.xfail`, assert ≥0.2% improvement — PENDING
- [ ] P2.2: Verify orientation telemetry with interpolation — PENDING
- [ ] P3.1: Update REFINE-004/005 findings — PENDING
- [ ] P3.2: Refresh fix_plan + test registry sync — PENDING

**Classification:** `revive`
- No direct Tier 0 blocker
- REFINE-004/005 findings need resolution as exit criteria
- Can proceed with xfail removal once HKL grid coverage is confirmed
- Low complexity remaining (test gate update, docs sync)

---

### TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity

**Source:** `plans/active/TORCH-REFINE-002E/implementation.md`

**Phases Verified:**
- [x] A0: Probe extension — COMPLETE (H1 confirmed: symmetric strain dominates)
- [ ] A1: Multi-config sweep — DEFERRED (low ROI)
- [x] A2: Baseline B_ideal variants — COMPLETE (H2 rejected)
- [x] A3: Mapping forward vs Stage-A configs — COMPLETE (geometry encoding gap confirmed: 24.5% chi² difference)
- [x] B1: Local gradient probe — COMPLETE (large non-zero gradients at mapping zero point confirmed; chi² at zero-delta is 2.6× higher than mapping path)
- [ ] B2: Scale analytical optimum check — DEFERRED
- [ ] B3: LR/step sensitivity sweep — PENDING
- [ ] B4: Outlier ROI analysis — PENDING
- [ ] B5: Loss parity re-audit — PENDING
- [ ] C1: Select branch and implement — PENDING
- [ ] C2: Re-run core selectors — PENDING
- [ ] C3: Update findings/fix_plan — PENDING

**Classification:** `blocked`
- **Blocker:** ARCH-GRADIENT-FLOW-001 (blocked_pending_upstream)
  - Jacobian mismatch (~640× magnitude with sign flip) in `nanobrag_torch/models/crystal.py::compute_cell_tensors()`
  - Escalation filed in `inbox/to_nanobrag_gradient_magnitude_2025_12_07.md`
- Phase B/C gradient diagnosis and action work requires gradient magnitude/sign resolution
- Phase A diagnostics are complete — geometry encoding gap is understood
- **Decision:** Branch G (geometry fix) is indicated, but blocked on upstream gradient audit

---

### TORCH-REFINE-003 — Stage C Detector Microslip

**Source:** `plans/active/TORCH-REFINE-003/implementation.md`

**Phases Verified:**
- [ ] P0.1: Baseline reality check (detector offset impact) — PENDING
- [ ] P0.2: Document offset magnitude — PENDING
- [ ] P1.1-P1.3: Config + parameterization — PENDING
- [ ] P2.1-P2.3: LBFGS integration + geometry update — PENDING
- [ ] P3.1-P3.3: Telemetry + output — PENDING
- [ ] P4.1-P4.3: Validation + ledger updates — PENDING

**Classification:** `blocked`
- **Dependency chain:** TORCH-REFINE-003 depends on Stage A gate being live
- Stage A gate (002D/002E) blocked on:
  - 002D: xfail removal (revivable)
  - 002E: gradient flow (blocked upstream)
- **Note:** Once 002D completes and Stage A gate is restored, 003 can begin Phase 0
- **Recommendation:** Keep pending until 002D revives

---

### TORCH-REFINE-004 — Stage B Fhkl Modifiers

**Source:** `plans/active/TORCH-REFINE-004/implementation.md`

**Phases Verified:**
- [x] Phase 1: Config + metadata scaffolding — COMPLETE
- [x] Phase 2: Stage B optimization loop (shell mode) — COMPLETE
- [x] Phase 3: Persistence + telemetry plumbing — COMPLETE
- [x] Phase 4: Tests + documentation — COMPLETE
- [x] Phase 5: Follow-up calibration — COMPLETE
- [x] Outstanding cleanup (bridge config realignment) — COMPLETE

**Classification:** `archive`
- **All phases complete** with documented outcomes
- Exit criteria satisfied (per-reflection mode operational, ASU mapping, shell mode fallback)
- Ready for move to `archive/plans/TORCH-REFINE-004/`

---

## Dependency Map

```
                    ARCH-GRADIENT-FLOW-001 (blocked_pending_upstream)
                              |
                              v
                    TORCH-REFINE-002E (blocked)
                              |
                              v
    TORCH-REFINE-002D ------> Stage A Gate Live
           |                          |
           v                          v
      xfail removal          TORCH-REFINE-003 (blocked)
           |
           v
      ≥0.2% gate restored


TORCH-REFINE-001 (revive) -----------> independent (no blockers)

TORCH-REFINE-002 (done) ------------> delegated to 002D

TORCH-REFINE-004 (archive) ----------> standalone complete
```

---

## Tier 0 Blocker Status

| Blocker ID | Status | Impact on TORCH-REFINE |
|------------|--------|------------------------|
| ARCH-GRADIENT-FLOW-001 | blocked_pending_upstream | Blocks 002E Phase B/C gradient work |
| ARCH-SIM-CONSTRUCTION-001 | blocked_pending_environment | Affects DB-AT-028/029 acceptance (not directly gating TORCH-REFINE) |

---

## Classification Summary

| Classification | Plans | Description |
|----------------|-------|-------------|
| **revive** | 001, 002D | Actionable now — no Tier 0 blockers, low-to-moderate complexity |
| **blocked** | 002E, 003 | Requires Tier 0 resolution (ARCH-GRADIENT-FLOW-001) first |
| **done/delegated** | 002 | Work complete; Phase 4 tracked in 002D |
| **archive** | 004 | All phases complete; ready for archive move |

---

## Recommendations for Phase B

1. **Archive TORCH-REFINE-004** — Move to `archive/plans/` with closure summary
2. **Revive TORCH-REFINE-002D** — Priority: remove xfail, restore ≥0.2% Stage A gate
3. **Revive TORCH-REFINE-001** — Priority: Phase B full-trace telemetry (can run in parallel with 002D)
4. **Keep TORCH-REFINE-002E blocked** — Document escalation dependency on ARCH-GRADIENT-FLOW-001
5. **Keep TORCH-REFINE-003 pending** — Will unblock once 002D restores Stage A gate
6. **Close TORCH-REFINE-002** — Mark as `done (delegated to 002D)` in roll-up

---

## Test Selector Inventory

**Captured:** `collect_refine_smoke.log`

| Selector | Status |
|----------|--------|
| `test_stage_a_expansion` | Active |
| `test_stage_a_expansion_incremental_ub` | Active |
| `test_stage_a_engine_delegation_telemetry` | Active |
| `test_stage_c_detector_microslip` | Active (Stage C) |
| `test_stage_b_shell_modifiers` | Active (Stage B) |
| `test_stage_b_per_reflection_smoke` | Active (Stage B) |

Total: 6 tests collected
