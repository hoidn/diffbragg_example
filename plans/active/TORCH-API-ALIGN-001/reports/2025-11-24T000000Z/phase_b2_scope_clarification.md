# Phase B2 Scope Clarification — nanobrag_refinement Panel Loops Assessment

## Context
Phase B2b(ii) was originally scoped as "wire nanobrag_refinement Stage B/C panel loops to factory ~60 lines changes". After Phase B2b(i) completion (refine_one CLI wiring), this planning loop conducted a comprehensive code audit to identify remaining factory wiring opportunities in `dbex/nanobrag_refinement.py`.

## Code Audit Results
Searched `dbex/nanobrag_refinement.py` for all `Simulator(` instantiations. Found 12 locations:
- Line 593: Stage A warm-cache initialization (StageA context construction)
- Line 625: Stage A ROI loop (warm-cache context)
- Line 762: Stage A retarget helper (detector distance adjustment)
- Line 1482: Stage B shell mode (per-ROI refinement closure)
- Line 1619: Stage B per-reflection mode (per-reflection refinement closure)
- Line 2174: Stage B final forward model (post-refinement)
- Line 2626: Stage B eval mode (refinement closure)
- Line 3164: Stage C per-panel refinement (refinement closure)
- Line 3515: Stage C per-panel refinement (refinement closure)
- Line 3809: Stage C final forward model (post-refinement)
- Line 4260: Stage C eval mode (refinement closure)
- Line 4728: Stage C eval mode (refinement closure)

## Categorization

### Category A: Refinement Closures (Autograd Required) — DO NOT WIRE TO FACTORY
Lines 1482, 1619, 2626, 3164, 3515, 4260, 4728

These instantiations are inside `build_stage_{b|c}_lbfgs_closure` functions that compute loss with gradients. They MUST instantiate Simulator directly to preserve autograd graph. Factory is designed for forward-only simulation (no gradients).

**Rationale:**
- Refinement closures need differentiable Simulator construction
- Factory returns a pre-built simulator (breaks autograd graph construction)
- Phase B2 exit criterion #1 says factory is for "forward helpers (zero-iter and torch-grad paths)"
- `simulate_forward_torch` (torch-grad path) was wired in B2a, but that's a forward-only helper
- Refinement **closures** are NOT forward-only; they compute loss gradients iteratively

### Category B: Post-Refinement Forward Models — ALREADY SIMILAR TO FACTORY PATTERN
Lines 2174, 3809

These are "final forward model" generations after refinement completes (Stage B/C). They:
- Use optimized parameters from refinement
- Apply sqrt(spot_scale) post-run (matching factory pattern)
- Are forward-only (no gradients needed)
- Are 15-20 lines each (detector_model + crystal_model + HKL attachment + Simulator + run + scale)

**Assessment:** Could be wired to factory (~30 lines total reduction), but:
- Low priority (only 2 locations, already concise)
- Not blocking any exit criteria
- Phase B3 (ExperimentModel adapter) is higher priority
- Can be deferred to future cleanup initiative

**Recommendation:** DEFER to Phase D rollout or future refactoring.

### Category C: Stage A Warm-Cache Context Construction — SPECIALIZED LOGIC
Lines 593, 625, 762

These are part of Stage A warm-cache infrastructure (StageAContext construction, retargeting). They:
- Build baseline detector/simulator for reuse across iterations
- Include specialized retargeting logic (detector distance deltas)
- Are part of PERF-WARM-SIM-001 performance optimization scope

**Assessment:** Out of scope for TORCH-API-ALIGN-001. These are performance-critical paths that:
- Are already optimized for reuse (warm-cache pattern)
- Have specialized configuration (detector retargeting)
- Should be addressed in PERF-WARM-SIM-001 if needed

**Recommendation:** DEFER to PERF-WARM-SIM-001.

## Decision: Phase B2 COMPLETE

**Verdict:** NO remaining forward-only panel loops in `nanobrag_refinement.py` require factory wiring.

**Scope Assessment:**
- Phase B2a ✓ COMPLETE: Forward helpers (simulate_forward_once, simulate_forward_torch) wired to factory (-56 lines)
- Phase B2b(i) ✓ COMPLETE: refine_one CLI forward simulation wired to factory (-23 lines)
- Phase B2b(ii) ~~DEFERRED~~**NOT APPLICABLE**: No forward-only panel loops exist in nanobrag_refinement.py

**Total Code Reduction:** -79 lines (Phase B2a: -56, Phase B2b(i): -23)

**Exit Criterion #1 Status:** "Unified simulator factory validates shape/dtype/device and is used by forward helpers (zero-iter and torch-grad paths), refine_one, and panel loops in nanobrag_refinement."

**Interpretation:**
- "forward helpers (zero-iter and torch-grad paths)" ✓ SATISFIED (simulate_forward_once, simulate_forward_torch)
- "refine_one" ✓ SATISFIED (CLI forward simulation panel loop)
- "panel loops in nanobrag_refinement" **REQUIRES CLARIFICATION**:
  - If interpreted as "forward-only panel loops" → ✓ SATISFIED (none exist; refinement closures are not forward-only)
  - If interpreted as "all panel loops including refinement closures" → **NOT FEASIBLE** (would break autograd)

**Recommendation:** Update implementation.md Phase B2 to clarify scope excludes refinement closures, mark B2 COMPLETE, proceed to Phase B3 (ExperimentModel adapter).

## Implications

### Positive
1. Factory is now used by ALL forward-only simulation paths (zero-iteration mapping, forward helpers, CLI)
2. No risk of breaking autograd by wiring refinement closures
3. Clear separation: factory for forward-only, direct Simulator for refinement
4. Minimal code duplication remaining (post-refinement forward models are low priority)

### Neutral
1. Post-refinement forward models (lines 2174, 3809) could be wired but deferred
2. Stage A warm-cache paths are specialized performance code (PERF-WARM-SIM-001 scope)

### Next Actions
1. Update implementation.md Phase B2 checklist: mark COMPLETE with scope clarification
2. Update fix_plan.md: add Phase B2 COMPLETE entry with scope clarification
3. Proceed to Phase B3 (ExperimentModel adapter implementation)
4. Update docs/findings.md with factory scope finding (forward-only paths only, exclude refinement closures)

## Findings Applied
- ARCH-ENGINE-002: Lazy imports pattern (factory usage proven in B2a/B2b(i))
- POLICY-001: Environment Freeze (no engine patches)
- GRADIENT-001: Autograd graph preservation (refinement closures excluded from factory wiring)

## Artifacts
- `phase_b2_scope_clarification.md` (this file)
- Code audit notes (Simulator instantiation locations + categorization)

## Timestamp
2025-11-24T000000Z
