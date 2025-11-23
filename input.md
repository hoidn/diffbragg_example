# Phase C2.2 — CPU Fallback Device Routing Fix (Loop i=215)

## Summary
Implement targeted 7-line fix to route CPU fallback device to final Bragg generation helper, eliminating CUDA OOM on full detector Stage B runs.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2 CPU fallback device routing)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (small detector — regression guard)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (full detector — primary validation, `--smoke-detector-size=full`)

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/

## Do Now

**Context:** Loop i=214 instrumentation identified root cause with HIGH confidence (~95%): CPU fallback condition logic is PERFECT (all three conditions evaluate correctly, `use_stage_b_cpu_fallback=true`, `eval_device="cpu"`), but `_build_final_bragg_from_stage_b_telemetry` (lines 2740-2945) ignores the fallback flag and hardcodes `device=cuda:0`, causing OOM during final Bragg regeneration at line 2912, NOT in LBFGS closure.

**Fix Required:** Pass `use_stage_b_cpu_fallback` parameter through to final Bragg helper and route device parameter accordingly.

### Implementation Tasks (7 lines total)

1. **Add `use_stage_b_cpu_fallback` parameter to function signature** (dbex/nanobrag_refinement.py:2740)
   - Add `use_stage_b_cpu_fallback=False,` to parameter list (after `dtype`, before closing paren)

2. **Compute final device at top of function** (after line 2754, inside function body)
   - Insert: `final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device`

3. **Replace hardcoded device references with final_device** (5 locations):
   - Line ~2902: `Crystal(..., device=final_device, ...)`
   - Line ~2906: `.to(device=final_device, ...)`
   - Line ~2926: `.to(..., device=final_device)`
   - Line ~2934: `Detector(..., device=final_device, ...)`
   - Line ~2935: `Crystal(..., device=final_device, ...)`
   - Line ~2937: `.to(device=final_device, ...)`
   - Line ~2939: `Simulator(..., device=final_device, ...)`

   (Exact line numbers may shift slightly; search for `device=device` inside `_build_final_bragg_from_stage_b_telemetry`)

4. **Update call site** (dbex/nanobrag_refinement.py:3126)
   - Add `use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,` to function call arguments

5. **Run Stage B full detector test** (primary validation)
   ```bash
   DBEX_SMOKE_DETECTOR_SIZE=full \
   DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/telemetry_stage_b_full.json \
   KMP_DUPLICATE_LIB_OK=TRUE \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     --smoke-detector-size=full \
     | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/pytest_stage_b_full.log
   ```
   - **Expected:** PASSED with telemetry showing `cache_mode="warm"`, CPU device usage in logs

6. **Run Stage B small detector test** (regression guard)
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/pytest_stage_b_small.log
   ```
   - **Expected:** PASSED (ROI mode should still use CUDA, no CPU fallback)

7. **Extract test outcomes via T0 micro probe**
   ```bash
   cd plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/ && \
   python -c "
   import re, json
   full_log = open('pytest_stage_b_full.log').read()
   small_log = open('pytest_stage_b_small.log').read()

   def extract_status(log, name):
       m = re.search(r'test_stage_b_shell_modifiers\s+(PASSED|FAILED)', log)
       return m.group(1) if m else 'NOT_RUN'

   result = {
       'full_detector_status': extract_status(full_log, 'full'),
       'small_detector_status': extract_status(small_log, 'small'),
       'full_has_cpu_fallback_diagnostics': 'CPU_FALLBACK_DIAGNOSTICS' in full_log,
       'small_has_cpu_fallback_diagnostics': 'CPU_FALLBACK_DIAGNOSTICS' in small_log,
   }
   print(json.dumps(result, indent=2))
   " | tee test_outcomes.json
   ```

8. **Remove instrumentation** (ONLY if both tests PASS)
   - Delete diagnostic print at dbex/nanobrag_refinement.py:2197 (CPU_FALLBACK_DIAGNOSTICS_PARAMS)
   - Delete diagnostic print at dbex/nanobrag_refinement.py:2394 (CPU_FALLBACK_DIAGNOSTICS_CLOSURE)
   - Keep the production CPU fallback logic itself (lines 2178-2182, 2199-2214, 2367-2368)
   - Delete json import if no longer used elsewhere in file (check `git diff`)

9. **Write decision synthesis** (plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/decision.md)
   - **Path A** (both tests PASS): Document fix success, confirm CPU fallback active for full detector, ROI mode unaffected
   - **Path B** (full detector FAIL): Document failure signature, escalate to Galph with blocker
   - **Path C** (small detector FAIL): Document regression, revert changes, escalate

10. **Update implementation.md Phase C status** (plans/active/ARCH-REFINE-FLOW-001/implementation.md)
    - If Path A: Mark Phase C2.2 COMPLETE, note next action is Phase C validation (run Stage B smokes + DB-AT-024)
    - If Path B/C: Mark Phase C2.2 BLOCKED with specific failure

11. **Write summary.md with Turn Summary block**
    ```markdown
    ### Turn Summary
    [3-5 sentences: what was shipped, main problem resolution status, single next step]
    Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/ (decision.md, pytest logs, telemetry, test_outcomes.json)
    ```

12. **Commit and push**
    ```bash
    git add -A && \
    git commit -m "ARCH-REFINE-FLOW-001 Phase C2.2: CPU fallback device routing fix — tests: $(cat plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/test_outcomes.json | jq -r '.full_detector_status + "/" + .small_detector_status')" && \
    git push
    ```

## How-To Map

**File locations:**
- Helper function: `dbex/nanobrag_refinement.py:2740-2945` (`_build_final_bragg_from_stage_b_telemetry`)
- Call site: `dbex/nanobrag_refinement.py:3126` (inside engine delegation path)

**Device routing logic:**
```python
# Add at top of _build_final_bragg_from_stage_b_telemetry (after line 2754)
final_device = torch.device("cpu") if use_stage_b_cpu_fallback else device
```

**Search pattern for replacements:**
Search for `device=device` inside `_build_final_bragg_from_stage_b_telemetry` (there should be exactly 7 occurrences across warm/cold paths). Replace each with `device=final_device`.

**Verification strategy:**
1. Full detector test MUST PASS (proves CPU fallback works)
2. Small detector test MUST PASS (proves ROI mode still uses CUDA)
3. Telemetry JSON MUST show `cache_mode="warm"` for full detector
4. Test logs SHOULD show `eval_device="cpu"` in CPU_FALLBACK_DIAGNOSTICS for full detector
5. Test logs SHOULD show `use_stage_b_cpu_fallback=false` for small detector (ROI mode)

## Pitfalls To Avoid

1. **Device Neutrality:** Do NOT hardcode `torch.device("cpu")` anywhere except the conditional routing line. All other references MUST use `final_device` variable.

2. **Parameter Forwarding:** MUST add `use_stage_b_cpu_fallback=use_stage_b_cpu_fallback,` to call site at line 3126. Missing this parameter means the flag never reaches the helper.

3. **Instrumentation Cleanup:** ONLY remove diagnostic prints if BOTH tests pass. Keep instrumentation if ANY test fails (Galph needs diagnostics for debugging).

4. **Production Code Preservation:** Do NOT remove the CPU fallback condition logic itself (lines 2178-2182). Only remove the temporary diagnostic print statements.

5. **Regression Risk:** Small detector test uses ROI mode and should NOT activate CPU fallback. If it does, the condition logic has regressed.

6. **Import Guard:** If removing `json` import, first verify no other code in the file uses it (check `git diff` for json.dumps/loads calls).

7. **Line Number Drift:** Exact line numbers in this Do Now may shift by ±5 lines due to instrumentation. Use function names and code patterns to locate targets, not just line numbers.

8. **Telemetry Validation:** Full detector telemetry MUST include `cache_mode="warm"` (proves Stage A context was correctly cloned to CPU per PERF-WARM-012 canonical).

9. **Protected Assets:** Do NOT modify `_build_stage_b_params` or `_build_stage_b_lbfgs_closure` helpers. Those are proven correct per loop i=214 instrumentation. Only touch `_build_final_bragg_from_stage_b_telemetry`.

10. **Environment Freeze:** Do NOT install packages. If torch import fails, mark blocked with error signature.

## If Blocked

1. **Capture blocker signature:**
   - Full test failure: Extract pytest output showing failure location + error message
   - Regression (small test fails): Document what changed vs baseline
   - Import errors: Record exact ModuleNotFoundError message

2. **Write blocker.md** (plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/blocker.md)
   ```markdown
   # Phase C2.2 Blocker

   ## Test Outcomes
   - Full detector: [PASSED|FAILED|NOT_RUN]
   - Small detector: [PASSED|FAILED|NOT_RUN]

   ## Failure Signature
   [Paste exact error message, traceback location, pytest output]

   ## Hypothesis
   [1-2 sentences on suspected root cause]

   ## Artifacts
   - pytest_stage_b_full.log
   - pytest_stage_b_small.log
   - test_outcomes.json
   ```

3. **Update galph_memory.md Attempts History:** Add timestamp, action="cpu_fallback_device_routing_fix", outcome="blocked", blocker="[brief description]"

4. **Do NOT revert** instrumentation if blocked. Keep diagnostic prints for next loop debugging.

## Findings Applied

- **REFINE-008** (Stage B ±1% shell modifier gate): Stage B full detector must keep shell modifiers within ±1% of identity and loss improvement ≥-1e-6.
- **PHYSICS-LOSS-001** (Variance-weighted loss): Stage B uses same chi-squared denominator as Stage A.
- **PHYSICS-LOSS-002** (sigma_floor requirement): Stage B inherits sigma_floor from Stage A via stage_a_ctx.
- **POLICY-001** (Environment Freeze): No package installs; instrumentation is temporary diagnostic, will be removed this loop.
- **CONFIG-001** (Detector metadata contracts): CPU fallback preserves detector metadata during CPU context cloning.

**Loop i=214 diagnostic finding (not yet numbered):** CPU fallback condition evaluation is CORRECT (all three conditions true, `use_stage_b_cpu_fallback=true`, `eval_device="cpu"`). Bug is NOT in condition logic; bug is in final Bragg helper ignoring device routing.

## Pointers

- **Spec:** docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- **Implementation Plan:** plans/active/ARCH-REFINE-FLOW-001/implementation.md (Phase C checklist)
- **Fix Plan Entry:** docs/fix_plan.md `[ARCH-REFINE-FLOW-001]`
- **Test Registry:** docs/TESTING_GUIDE.md §2 (Stage smoke selectors)
- **Loop i=214 Evidence:**
  - plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/decision.md (root cause analysis)
  - plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/instrumentation_summary.md (diagnostic strategy)
  - plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/cpu_fallback_conditions.json (extracted conditions proving logic is correct)

## Next Up (if Ralph finishes early)

If both tests PASS and instrumentation is removed:
1. **Option A (continue Phase C validation):** Run DB-AT-024 mapping consistency test to verify Stage B extraction didn't regress forward model
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_torch_diffbragg_acceptance.py::test_forward_mapping_consistency | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/pytest_db_at_024.log
   ```
2. **Option B (mark Phase C2.2 complete):** Update implementation.md and write summary.md, commit, push. Galph will plan full Phase C validation next loop (C3-C5 combined: telemetry completeness + full validation + DB-AT selectors).

**Default choice:** Option B (mark complete and hand back to Galph for Phase C validation planning). Only pursue Option A if explicitly directed in a follow-up message.
