# Focus Selection Decision — TORCH-REFINE-004

**Date:** 2025-11-24T125000Z
**Actor:** Galph (Supervisor)
**Context:** Loop i=259 post-ARCH-REFACTOR-001 Phase D D2 completion, selecting next Tier 3 focus

## Decision: SELECT TORCH-REFINE-004 (Stage B Per-Reflection Mode)

**Rationale:** Highest priority Tier 3 Feature Completeness item per Execution Roadmap, NOW UNBLOCKED.

## Status Assessment

### Tier 2 Complete
- **ARCH-REFINE-FLOW-001:** ✓ DONE (2025-11-23T172000Z) — All Phases A-E complete, Stage A/B/C wrappers validated
- **TORCH-API-ALIGN-001:** ✓ DONE (2025-11-24T004500Z) — Factory-only path complete, unified factory -79 lines

### Tier 3 Candidates

#### Option A: TORCH-REFINE-004 (Stage B Per-Reflection Mode) — **RECOMMENDED**
- **Status:** Pending → **NOW UNBLOCKED**
- **Dependency:** ARCH-REFINE-FLOW-001 Phase C (Stage B extraction complete) — ✓ **SATISFIED** (Phases A-E ALL COMPLETE, not just Phase C)
- **Priority:** HIGH (Tier 3 Feature Completeness, normative spec requirement)
- **Spec Requirement:** docs/spec-db-workflow.md:59 — "Per-reflection Fhkl multipliers mapped to unique ASU indices **SHALL be the default (Parity Mode)**"
- **Current State:** Shell mode implemented and working (Phases 1-5 complete per implementation.md), per-reflection mode NOT YET IMPLEMENTED
- **Normative Gap:** Shell mode is currently default, violating spec (shell mode MUST NOT be default per spec:60)
- **Estimated Effort:** 2-4 loops (~4-8 hours):
  1. Phase 6: Per-reflection parameterization (ASU index mapping, modifier initialization)
  2. Phase 7: Optimization loop (LBFGS closure with per-reflection modifiers)
  3. Phase 8: Tests (smoke test with per-reflection default, shell mode fallback test)
  4. Phase 9: Documentation (registry sync, findings update)
- **Risk:** MEDIUM (HKL-to-ASU mapping complexity, parameter count may require Adam vs LBFGS)
- **Confidence:** HIGH (~85%) — Clear spec requirement, shell mode pattern proven, engine delegation operational
- **Roadmap Alignment:** Tier 3 Feature Completeness (highest priority after Tier 2 complete)

#### Option B: TOOLING-VIS-001 (Visual Diagnostics Library)
- **Status:** In Progress
- **Dependency:** PHYSICS-LOSS-001 (telemetry stack) — ✓ SATISFIED
- **Priority:** MEDIUM (Tier 3 Tooling & Observability)
- **Current State:** Phase D realignment complete (2025-11-21T223420Z), Phases A-C pending
- **Estimated Effort:** 5-8 loops (~10-16 hours) for library + integration + tests
- **Risk:** LOW (isolated visualization code, no production impact)
- **Confidence:** MEDIUM (~70%) — Larger scope, less clear ROI than normative feature
- **Roadmap Alignment:** Tier 3 Tooling (lower priority than Feature Completeness)

#### Option C: PERF-WARM-SIM-001 (Warm Simulator)
- **Status:** Blocked (ENV-CUDA-001 environmental CUDA caching allocator error)
- **Dependency:** TORCH-API-ALIGN-001 — ✓ SATISFIED (unblocked 2025-11-24T004500Z)
- **Priority:** HIGH (Tier 3 Architectural Maturity)
- **Block Status:** Environmental issue, not architectural
- **Risk:** HIGH (env error may persist, outside agent control)
- **Confidence:** LOW (~40%) — Environmental blocker may not be resolvable in single loop
- **Roadmap Alignment:** Tier 3 Architectural Maturity (Refactoring)

## Decision Matrix

| Criterion | TORCH-REFINE-004 (A) | TOOLING-VIS-001 (B) | PERF-WARM-SIM-001 (C) |
|-----------|---------------------|---------------------|----------------------|
| Unblocked | ✓ YES | ✓ YES | ❌ ENV-CUDA-001 |
| Spec Normative | ✓ YES (SHALL) | ❌ NO | ❌ NO |
| Roadmap Priority | ✓ HIGH (Feature) | MEDIUM (Tooling) | HIGH (Refactoring) |
| Estimated Loops | 2-4 loops | 5-8 loops | Unknown (env-blocked) |
| Confidence | ✓ HIGH (~85%) | MEDIUM (~70%) | LOW (~40%) |
| CLAUDE.md Incremental | ✓ YES (2-4 loops) | ❌ NO (5-8 loops) | ❌ BLOCKED |

**Winner:** Option A (TORCH-REFINE-004) — Highest priority unblocked Tier 3 item with normative spec requirement.

## Implementation Strategy

### Phase 6: Per-Reflection Parameterization
**Objective:** Map HKL grid voxels to unique ASU indices and parameterize per-reflection Fhkl multipliers.

**Scope Analysis:**
1. **ASU Mapping:** Extend `compute_hkl_shell_lookup` pattern to compute `hkl_asu_map: torch.Tensor[int64]` shape `(h_count, k_count, l_count)` where each voxel maps to its unique ASU index. Use cctbx symmetry ops to fold HKL into ASU (similar to shell radius calculation but with symmetry equivalence).
2. **Modifier Parameterization:** Initialize `asu_modifiers: nn.Parameter` shape `(n_asu_unique,)` with values near 1.0 (log-space or softplus for positivity). Count unique ASU indices from symmetry analysis.
3. **Application:** In LBFGS closure, `hkl_grid_modified = hkl_grid_base * asu_modifiers[hkl_asu_map]` broadcasts modifiers to all HKL grid voxels via index lookup.

**Risks:**
- R1: ASU index computation complexity (MEDIUM) — Mitigate with cctbx Miller index asymmetric unit helpers, fallback to shell mode if cctbx unavailable per Environment Freeze.
- R2: Parameter count explosion (MEDIUM) — Typical protein ~10K-50K unique ASU reflections, may require Adam optimizer vs LBFGS. Check spec:107 allows Adam for Stage B.
- R3: HKL halo handling (LOW) — Halo voxels outside MTZ range should map to dummy ASU index 0 with fixed modifier=1.0.

**Dependencies:**
- cctbx.miller for ASU symmetry operations (already in environment per upstream tools)
- `hkl_metadata["space_group"]` from MTZ ingestion (already available per MAP-SCALE-001)

### Phase 7: Optimization Loop
**Objective:** Implement LBFGS closure with per-reflection modifiers, validate gradient flow.

**Scope:**
1. Conditional branching: `if config.stage_b_mode == "per_reflection"` use ASU modifiers, else shell modifiers (existing path).
2. LBFGS vs Adam decision: If `n_asu_unique > 10000`, use Adam with learning rate 1e-3 (per spec:107 "Stage B MAY use L-BFGS or Adam").
3. Telemetry extension: Add `asu_count`, `asu_modifier_stats` (min/max/std) to Stage B telemetry.

### Phase 8: Tests
**Objective:** Validate per-reflection mode as default, shell mode as fallback.

**Test Plan:**
1. `test_stage_b_per_reflection_default`: Assert Stage B runs in per-reflection mode when `enable_stage_b=True` and `stage_b_mode` unspecified (default).
2. `test_stage_b_shell_fallback`: Assert shell mode works when explicitly requested via `stage_b_mode="shell"`.
3. Regression: Existing Stage A/C smokes continue to PASS with Stage B disabled (no behavior change).

### Phase 9: Documentation
**Objective:** Update registry and findings.

**Deliverables:**
1. `docs/TESTING_GUIDE.md` §2: Add `test_stage_b_per_reflection_default` selector.
2. `docs/development/TEST_SUITE_INDEX.md`: Add row for per-reflection test.
3. `docs/findings.md`: Add REFINE-008 or extend existing Stage B finding with per-reflection mode conventions (ASU index mapping, optimizer choice, parameter count guidance).
4. `docs/fix_plan.md`: Mark TORCH-REFINE-004 status `done` with completion timestamp.

## Findings Applied
- **REFINE-001** (LBFGS scale warm-start) ✓ — Stage B inherits scale from Stage A
- **REFINE-002** (acceptance gate) ✓ — Stage B improvement gate separate from Stage A
- **REFINE-005** (HKL halo) ✓ — Differentiable interpolation mandatory
- **SCALE-001/002** (structure factors unscaled) ✓ — Modifiers applied post-interpolation
- **PHYSICS-LOSS-001** (variance-weighted loss) ✓ — Stage B uses same denominator as Stage A
- **POLICY-001** (Environment Freeze) ✓ — Use existing cctbx, no new installs
- **ARCH-ENGINE-002** (lazy imports) ✓ — Import cctbx.miller inside Stage B setup
- **spec-db-workflow.md:59** (per-reflection SHALL be default) ✓ — Core requirement

## Next Actions
1. Write `input.md` with Phase 6 planning protocol (ASU mapping design, parameterization strategy, risk mitigation).
2. Ralph executes Phase 6 planning (9-step: read spec, analyze cctbx symmetry ops, design ASU index computation, estimate parameter counts, assess LBFGS vs Adam, write planning artifacts, decision synthesis).
3. After planning approval, Phase 6 implementation (2-3 loops estimated for Phases 6-8 combined).

## Artifacts
- This decision: `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/focus_selection_decision.md`
- Implementation plan: `plans/active/TORCH-REFINE-004/implementation.md`
- Fix plan entry: `docs/fix_plan.md:227-239`
- Spec: `docs/spec-db-workflow.md:58-61`
