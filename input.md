# Input for Ralph — ARCH-REFINE-FLOW-001 Phase C Planning (DEFERRED - SUPERVISOR PLANNING ONLY)

**IMPORTANT:** This is a **supervisor planning-only loop**. Ralph should NOT execute this Do Now. Galph will author the Phase C plan and create the Phase C0 baseline Do Now in the next supervisor turn.

**Summary:** Plan Phase C (Stage B extraction) strategy following proven multi-loop approach from Phase B.

**Mode:** Docs (supervisor planning only)

**Focus:** ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C planning)

**Branch:** integration

**Mapped tests:** none — planning-only

**Artifacts:** `plans/active/ARCH-REFINE-FLOW-001/reports/<timestamp>/`

---

## Supervisor Planning Context

### Phase B Completion Evidence
- **Status:** Phase B COMPLETE (2025-11-23T052000Z)
- **Validation:** ALL 4 test suites PASSED
  - Stage A smoke small (12.42s)
  - Stage A smoke full (17.76s)
  - DB-AT-024 mapping (31.59s)
  - DB-AT-010 gradcheck (5 tests, 614.36s)
- **Achievements:** 7 loops, 4 helpers extracted (~1,000 lines), StageA class, engine delegation, ~692 lines reduced
- **Confidence:** HIGH (~98%) engine delegation production-ready

### Phase C Scope Analysis
- **Target:** Extract Stage B shell-modifier logic into StageB class
- **Location:** `dbex/nanobrag_refinement.py:2527-3141` (~614 lines)
- **Complexity:** Similar to Stage A (LBFGS closure, telemetry, optimizer)
- **Dependencies:** REFINE-005 (tricubic + halo), REFINE-008 (Stage B telemetry gates)

### Multi-Loop Strategy (Proven from Phase B)
**Total Loops:** 4-6 estimated
1. **C0:** Baseline artifacts (Stage B smoke selectors, telemetry)
2. **C1-C3:** Extract 3 helpers (~600 lines):
   - C1: `_build_stage_b_params` (shell modifier initialization, optimizer setup)
   - C2: `_build_stage_b_lbfgs_closure` (LBFGS closure with shell modifier logic)
   - C3: `_run_stage_b_lbfgs` (optimizer execution, telemetry aggregation)
3. **C4:** StageB wrapper class (call helpers, package telemetry)
4. **C5:** Engine delegation logic (A→B sequence in run_nanobrag_refinement)
5. **C6:** Full smoke validation (Stage B small/full + DB-AT selectors)

### Key Differences from Stage A
- **Simpler parameterization:** Only 1 shell modifier parameter (vs 3 modes in Stage A)
- **No geometry:** Pure structure factor refinement (no crystal/detector deltas)
- **HKL grid dependency:** Must respect REFINE-005 (halo + default_F fallback)
- **CPU fallback:** PERF-WARM-011/012 (Stage B can run on CPU to avoid GPU OOM)

### Findings to Apply
- **REFINE-005:** Tricubic interpolation + halo (HKL grid caching)
- **REFINE-008:** Stage B telemetry gates (≥3% improvement)
- **PHYSICS-LOSS-001/002/003:** Variance-weighted loss + telemetry stack
- **PERF-WARM-011/012:** CPU fallback for panel mode
- **GRADIENT-001:** Autograd graph preservation
- **SCALE-007:** Structure factor telemetry

---

## Galph Planning Tasks (This Loop)

1. **Read Stage B implementation** (`dbex/nanobrag_refinement.py:2527-3141`)
2. **Identify helper boundaries:**
   - Parameters initialization (shell_modifier_raw, optimizer, telemetry accumulators)
   - LBFGS closure (compute_loss + closure functions)
   - Optimizer execution (optimizer.step, validation, convergence check)
3. **Design StageB class interface:**
   - Inputs: RefinementInputs (from Phase A), telemetry from Stage A
   - Outputs: Dict with "B" telemetry key
   - Configuration: stage_b_mode (shell | per_reflection), enable_stage_b flag
4. **Estimate extraction complexity:**
   - Compare with Stage A (similar LBFGS structure)
   - Identify nonlocal variables and closure captures
   - Plan lazy imports for nanobrag_bridge/nanobrag_torch
5. **Draft Phase C0 Do Now:**
   - Baseline Stage B smoke selectors (test_stage_b_shell_modifiers)
   - Capture telemetry JSON (small + full detector)
   - Record selector status and runtime
6. **Update implementation.md Phase C checklist:**
   - C0-C6 tasks with specific file/line targets
   - Dependencies and exit criteria
7. **Author Phase C planning summary:**
   - Extraction strategy rationale
   - Multi-loop breakdown
   - Risk analysis
   - Lessons learned from Phase B

---

## Output Expected from This Loop

**NOT Ralph's responsibility — Galph handles this:**
- Phase C planning document under `plans/active/ARCH-REFINE-FLOW-001/reports/<timestamp>/`
- Updated `implementation.md` with Phase C checklist details
- Phase C0 baseline Do Now ready for next Ralph loop
- `galph_memory.md` updated with planning decision

**NO code changes expected** — This is a supervisor planning loop only.

---

## Blocker Scenarios

If Galph encounters blockers during planning:
1. **Stage B complexity exceeds estimation:** Revise multi-loop strategy (split C1-C3 further)
2. **HKL grid dependencies unclear:** Read REFINE-005 and nanobrag_torch docs
3. **CPU fallback logic complex:** Defer to separate perf initiative if needed
4. **Telemetry schema conflicts:** Review PHYSICS-LOSS-001 and SCALE-007 findings

---

## Next Actions After Planning

**Next Loop (Ralph i=200):**
- Execute Phase C0 baseline (if Galph completes planning this loop)
- Capture Stage B smoke artifacts
- Record telemetry baselines

**Subsequent Loops:**
- C1: Extract `_build_stage_b_params` helper ONLY
- C2: Extract `_build_stage_b_lbfgs_closure` helper ONLY
- C3: Extract `_run_stage_b_lbfgs` helper + refactor main function
- C4-C6: StageB wrapper, engine delegation, full validation

---

## Reminder: Supervisor Focus

This loop is **Galph planning only**. Ralph will NOT execute any implementation tasks. Galph will:
1. Analyze Stage B code structure
2. Draft Phase C extraction strategy
3. Prepare Phase C0 baseline Do Now
4. Update planning documents

**No production code changes** in this loop.
