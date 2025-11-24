# Ralph Input — PERF-WARM-SIM-001 Phase D Evidence Gathering (Stage C Chi-Squared Mismatch)

## Summary
Investigate Stage C initial chi² mismatch (0.32% gap vs Stage A final, exceeds 0.1% tolerance).

## Mode
none

## Focus
PERF-WARM-SIM-001 — Phase D: Stage C Detector Reuse (Evidence Gathering on Chi-Squared Initialization)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (Phase D blocker)
- NO test modifications (evidence-only loop)

## Artifacts
`plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/`
- `stage_c_chi2_investigation.md`, `summary.md`

## Do Now

**Context:** Phase D D1-D3 code COMPLETE (commit 1bdeca3), telemetry routing RESOLVED (commit 5be669c). NEW blocker: Stage C initial chi² (2.918e+08) != Stage A final chi² (2.909e+08), gap 0.94e+06 (0.32%) exceeds ±2.9e+05 tolerance (0.1%). Test assertion fails at test_torch_refine_smoke.py:1032. This is NOT a routing issue—both stages execute successfully, telemetry keys correct. Hypothesis: Stage C context initialization differs from Stage A final state (detector distances, HKL grid, param reconstruction).

**Task:** Evidence-only investigation (NO code changes). Identify root cause of chi-squared mismatch.

### Steps (7 total)

1. **Read blocker context:**
   - plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/summary.md (blocker description)
   - plans/active/PERF-WARM-SIM-001/implementation.md:Phase D (D1-D3 implementation notes)
   - tests/dbex/test_torch_refine_smoke.py:1020-1050 (assertion logic)

2. **Review Stage C initialization code** (dbex/nanobrag_refinement.py):
   - **compute_loss_stage_c warm path** (lines 3121-3146): How are detectors/simulators retrieved from stage_a_ctx? Are distance offsets applied correctly?
   - **Stage C initial params** (lines 3101-3120): Which params are used? Are they Stage A final or something else?
   - **HKL grid attachment** (line 3118): Is this the same grid from Stage A or freshly cloned?

3. **Compare Stage A final vs Stage C initial state:**
   Create comparison table documenting:
   - **log_scale:** Stage A final value vs Stage C initial (should be identical?)
   - **cell params:** a,b,c, alpha,beta,gamma (Stage A final vs Stage C)
   - **misset_deg:** Stage A final vs Stage C
   - **detector distances:** baseline_detector vs stage_a_ctx.detector_models (are distance mutations preserved?)
   - **HKL grid:** Same object reference? Device/dtype match?
   - **beam_config:** Same object from stage_a_ctx?

4. **Hypothesis ranking:**
   Based on code review + comparison, rank most likely causes:
   - **H1 (LIKELY):** Stage C uses stage_a_ctx.detector_models BUT those have Stage A **baseline distances**, not Stage A **final refined distances** (if Stage A refined distances). Check if Stage A modifies detector distances.
   - **H2 (POSSIBLE):** Stage C crystal_model uses perturbed cell params (lines 3101-3120) BUT Stage A final params are slightly different due to LBFGS refinement. Check if cell deltas from Stage A telemetry are applied.
   - **H3 (POSSIBLE):** HKL grid device/dtype mismatch causing numerical differences in structure factor lookups.
   - **H4 (UNLIKELY):** Telemetry chi² extraction bug (wrong index, wrong stage).

5. **Root cause verdict:**
   Write `stage_c_chi2_investigation.md` with:
   - **Section 1:** Blocker summary (gap 0.94e+06, 0.32%, tolerance 0.1%)
   - **Section 2:** Code review findings (state comparison table, detector/crystal/HKL initialization paths)
   - **Section 3:** Hypothesis analysis (H1-H4 likelihood + evidence)
   - **Section 4:** Root cause verdict (95% confidence: "Stage C uses Stage A baseline detector distances, not final refined distances" OR "Stage C cell params don't match Stage A final state" OR "Investigation inconclusive, needs instrumentation")
   - **Section 5:** Recommended fix (if root cause clear) OR recommended next step (if instrumentation needed)

6. **Summary.md:**
   Write Turn Summary (investigation outcome, root cause verdict, next action)

7. **Return to Galph:**
   NO commit (evidence-only). Galph will decide:
   - Path A (Root cause clear): Draft ready_for_implementation Do Now for targeted fix (1 loop)
   - Path B (Needs instrumentation): Draft ready_for_implementation Do Now for telemetry injection + diagnostic run
   - Path C (Multi-loop fix): Escalate to new initiative STAGE-C-CHI2-001

## How-To Map

**State Comparison Approach:**
Read Stage A telemetry final state from test log (plans/.../pytest_stage_c_full.log):
```python
# Extract from telemetry_a.param_deltas['log_scale']['final'], telemetry_a.chi_squared_trace_full[-1]
```

Then trace Stage C initialization (dbex/nanobrag_refinement.py:3101-3146):
```python
# compute_loss_stage_c uses:
# 1. perturbed_cell_a/b/c (line 3101-3107) — are these Stage A refined or baseline?
# 2. misset_deg_for_crystal (line 3113) — where does this come from?
# 3. stage_a_ctx.detector_models[pid] (line 3142) — what distance do these have?
# 4. crystal_model.hkl_data = hkl_grid (line 3118) — same grid from Stage A?
```

**Expected Evidence:**
- If H1: Stage C uses stage_a_ctx detectors BUT those were built with baseline distances (e.g., 100mm), not Stage A refined distances (e.g., 100.1mm if Stage A refined distances, though unlikely since Stage A doesn't refine detector geometry). VERDICT: H1 unlikely—Stage A doesn't refine detector distances.
- If H2: Stage C crystal_model uses **baseline cell** (perturbed_cell_a = baseline_cell_a + perturbation) BUT Stage A refined cell is slightly different. Check if perturbed_cell_a accounts for Stage A deltas. **EXPECTED ROOT CAUSE:** Stage C doesn't apply Stage A cell refinement deltas.
- If H3: HKL grid is cloned but device transfer corrupted indices (unlikely, would cause larger chi² jump).

## Pitfalls

1. **NO code changes** — Evidence-only loop per Mode: none
2. Stage A doesn't refine detector distances — only cell/scale/misset
3. Check if Stage C uses Stage A **final params** or **baseline params**
4. Tolerance is **relative 1e-3** (0.1%), not absolute
5. Gap is 0.32% — **outside tolerance** but not catastrophic (not 10×)
6. Chi-squared calculated same way in both stages (variance-weighted, PHYSICS-LOSS-003 fixes applied)

## If Blocked

**Reading code unclear:** Document ambiguity, return to Galph with partial findings
**Cannot determine root cause:** Recommend instrumentation loop (inject telemetry comparing Stage A final params vs Stage C initial params)

## Findings Applied

PERF-WARM-013 (Stage C instantiation overhead, D1-D3 addressed), PHYSICS-LOSS-003 (chi-squared calculation consistency), ARCH-ENGINE-002 (telemetry packaging, routing fixed), REFINE-007 (Stage C acceptance gates), POLICY-001 (Environment Freeze, evidence-only)

## Pointers

- dbex/nanobrag_refinement.py:3061-3200 (compute_loss_stage_c function, warm path lines 3121-3146)
- tests/dbex/test_torch_refine_smoke.py:1020-1050 (Stage C chi-squared assertion)
- plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/summary.md (blocker diagnosis)
- docs/spec-db-workflow.md §Stage C (Stage C inherits Stage A frozen params)
- docs/findings.md row 29 (REFINE-009: Stage C baseline detector seeding)

## Next Up

**If root cause H2 confirmed (Stage C missing Stage A cell deltas):**
- Targeted fix (1 loop): Apply Stage A final cell deltas to Stage C initialization
- Validation: test_stage_c_detector_microslip should PASS with chi² gap <0.1%

**If investigation inconclusive:**
- Instrumentation loop: Inject telemetry logging Stage A final params vs Stage C initial params, rerun test, compare outputs
