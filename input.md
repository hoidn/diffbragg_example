# Phase C2.2 CPU Fallback Instrumentation — Identify Failing Condition

## Summary
Add diagnostic instrumentation to `_build_stage_b_params` and `_build_stage_b_lbfgs_closure` to identify which CPU fallback condition is evaluating to False, preventing Stage B from switching to CPU and causing CUDA OOM on full detector.

## Mode
None (debugging instrumentation + evidence collection)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2 CPU fallback debugging)

## Branch
`integration`

## Mapped Tests
- `pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -k "not expansion and not detector_microslip" --timeout=180` (Stage B small detector regression guard, should PASS)
- `DBEX_SMOKE_DETECTOR_SIZE=full pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -k "not expansion and not detector_microslip" --timeout=180` (Stage B full detector with instrumentation, expect diagnostic output + decision)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/`
- `instrumentation_summary.md` — What was instrumented and where
- `pytest_stage_b_small_instrumented.log` — Small detector run with instrumentation (should PASS)
- `pytest_stage_b_full_instrumented.log` — Full detector run with instrumentation (may still OOM but will show condition values)
- `cpu_fallback_conditions.json` — Extracted condition values from stdout
- `decision.md` — Root cause diagnosis and next action (fix condition OR escalate)

## Do Now

### Task 1: Add Instrumentation to _build_stage_b_params
**Location:** `dbex/nanobrag_refinement.py`, inside `_build_stage_b_params` helper

**Add after line 2182 (after `use_stage_b_cpu_fallback` is computed):**

```python
# DIAGNOSTIC INSTRUMENTATION (TEMPORARY — remove after CPU fallback bug fixed)
import json
fallback_diagnostics = {
    "location": "_build_stage_b_params",
    "config_stage_b_full_eval_on_cpu": config.stage_b_full_eval_on_cpu,
    "device_str": str(device),
    "device_type": type(device).__name__,
    "device_is_cuda": str(device).startswith("cuda"),
    "use_stage_a_roi_mode": use_stage_a_roi_mode,
    "use_stage_a_roi_mode_type": type(use_stage_a_roi_mode).__name__,
    "stage_a_ctx_is_not_none": stage_a_ctx is not None,
    "use_stage_b_cpu_fallback": use_stage_b_cpu_fallback,
}
print(f"CPU_FALLBACK_DIAGNOSTICS_PARAMS: {json.dumps(fallback_diagnostics)}", flush=True)
```

**Rationale:** Capture all three sub-conditions and the final `use_stage_b_cpu_fallback` value at the point of computation.

### Task 2: Add Instrumentation to _build_stage_b_lbfgs_closure
**Location:** `dbex/nanobrag_refinement.py`, inside `_build_stage_b_lbfgs_closure` helper

**Add after line 2368 (after `eval_device` is computed):**

```python
# DIAGNOSTIC INSTRUMENTATION (TEMPORARY — remove after CPU fallback bug fixed)
import json
eval_device_diagnostics = {
    "location": "_build_stage_b_lbfgs_closure",
    "use_stage_b_cpu_fallback": use_stage_b_cpu_fallback,
    "device_param": str(device),
    "eval_device": str(eval_device),
    "eval_device_type": eval_device.type,
}
print(f"CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {json.dumps(eval_device_diagnostics)}", flush=True)
```

**Rationale:** Verify that `eval_device` is correctly set to CPU when fallback is active.

### Task 3: Run Stage B Small Detector with Instrumentation
**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -k "not expansion and not detector_microslip" \
  --timeout=180 \
  2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/pytest_stage_b_small_instrumented.log
```

**Expected:** Test PASSES, diagnostic output shows CPU fallback conditions for small detector (baseline)

### Task 4: Run Stage B Full Detector with Instrumentation
**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -k "not expansion and not detector_microslip" \
  --timeout=180 \
  2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/pytest_stage_b_full_instrumented.log
```

**Expected:** Test may still OOM BUT diagnostic output will show which condition failed

### Task 5: Extract CPU Fallback Conditions from Logs
**Script:** Use grep + jq to extract diagnostic JSON lines

```bash
cd plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z

# Extract from full detector log (the one with the problem)
grep "CPU_FALLBACK_DIAGNOSTICS_" pytest_stage_b_full_instrumented.log | \
  sed 's/.*CPU_FALLBACK_DIAGNOSTICS_//' | \
  jq -s '.' > cpu_fallback_conditions.json

# Show parsed conditions
cat cpu_fallback_conditions.json
```

**Expected:** JSON array with 2 objects (one from _build_stage_b_params, one from _build_stage_b_lbfgs_closure)

### Task 6: Analyze Conditions and Identify Root Cause
**Review `cpu_fallback_conditions.json`:**

Check which condition is False:
1. `config_stage_b_full_eval_on_cpu` — should be `true` (default)
2. `device_is_cuda` — should be `true` for CUDA device
3. `use_stage_a_roi_mode` — should be `false` for full detector panel mode
4. `stage_a_ctx_is_not_none` — should be `true` (context exists)
5. `use_stage_b_cpu_fallback` — final result (should be `true` if all above pass)
6. `eval_device` — should be `"cpu"` if fallback active, `"cuda:0"` if not

**Decision Paths:**

**Path A:** All conditions TRUE except `use_stage_b_cpu_fallback=false`
→ Logic bug in condition evaluation (line 2178-2182)
→ Fix boolean expression

**Path B:** `config_stage_b_full_eval_on_cpu=false`
→ Config propagation bug (config object not forwarding default)
→ Check RefinementConfig defaults and StageB.configure()

**Path C:** `use_stage_a_roi_mode=true` (should be false for full detector)
→ ROI mode detection bug
→ Check panel_slices computation

**Path D:** `device_is_cuda=false` (but device="cuda:0")
→ Device type/string conversion bug
→ Fix device check (use `device.type == "cuda"` instead of `str(device).startswith("cuda")`)

**Path E:** `stage_a_ctx_is_not_none=false`
→ Context propagation bug in engine
→ Escalate to engine/stage architecture layer

### Task 7: Document Root Cause in decision.md
**Template:**

```markdown
# Phase C2.2 CPU Fallback Instrumentation — Root Cause Identified

## Diagnostic Results

### Extracted Conditions
[Paste cpu_fallback_conditions.json content here]

### Failing Condition
[Identify which specific condition is False]

### Root Cause (HIGH/MEDIUM/LOW confidence ~XX%)
[Explain WHY the condition is failing]

## Decision Path
[Select A/B/C/D/E from Task 6]

## Next Actions
[Specific fix to implement OR escalation if architectural bug]

## Code Changes (Loop i=214)
[If targeted fix applied, document here. Otherwise "None — instrumentation only"]

## Blocker Status
[RESOLVED if fix applied and tests pass, BLOCKED if escalation needed]
```

### Task 8: Write instrumentation_summary.md
Document what was instrumented, where, and the rationale:

```markdown
# CPU Fallback Instrumentation Summary

## Objective
Identify which CPU fallback condition is failing, causing Stage B full detector to attempt GPU execution and OOM.

## Instrumentation Locations
1. **`_build_stage_b_params`** (dbex/nanobrag_refinement.py:~2183)
   - Captures: config flag, device string, ROI mode, context availability
   - Output: `CPU_FALLBACK_DIAGNOSTICS_PARAMS: {...}`

2. **`_build_stage_b_lbfgs_closure`** (dbex/nanobrag_refinement.py:~2369)
   - Captures: eval_device selection
   - Output: `CPU_FALLBACK_DIAGNOSTICS_CLOSURE: {...}`

## Expected Findings
One of the three CPU fallback conditions (config, device, ROI mode) OR context availability is False despite appearing to be True in code review.

## Cleanup
Remove instrumentation print statements after root cause identified and fix validated.
```

### Task 9: Apply Targeted Fix (Conditional)
**ONLY IF** decision.md identifies a clear, one-line fix (e.g., Path D: use `device.type == "cuda"` instead of `str(device).startswith("cuda")`):

1. Apply the fix
2. Remove instrumentation print statements
3. Rerun both tests (small + full detector)
4. If both PASS → proceed to Task 10
5. If still fails → document in decision.md and STOP

**ELSE IF** root cause requires architectural changes (Path E):
→ Skip this task, document escalation in decision.md

### Task 10: Verify Fix (If Applied)
**Commands:**
```bash
# Small detector regression guard
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -k "not expansion and not detector_microslip" \
  --timeout=180 \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/pytest_stage_b_small_fixed.log 2>&1

# Full detector (should now use CPU fallback and PASS)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -k "not expansion and not detector_microslip" \
  --timeout=180 \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/pytest_stage_b_full_fixed.log 2>&1
```

**Acceptance:**
- Small detector: PASS (no regression)
- Full detector: PASS with telemetry showing `cache_mode="warm"`, `eval_device="cpu"`

### Task 11: Write summary.md
**Template:**
```markdown
### Turn Summary
[One sentence: what condition was failing]
[One sentence: root cause and fix applied OR escalation decision]
Next: [If fixed: run full Phase C validation suite; If escalated: await supervisor guidance]
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/ (instrumentation_summary.md, cpu_fallback_conditions.json, decision.md)
```

Prepend to existing `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/summary.md`

### Task 12: Commit and Push
**Commit message:**
```
ARCH-REFINE-FLOW-001 Phase C2.2: CPU fallback condition instrumentation + [fix if applied] — tests: [status]

Added diagnostic logging to _build_stage_b_params and _build_stage_b_lbfgs_closure
to identify which CPU fallback condition fails for full detector OOM.

[If fix applied: "Root cause: <brief>. Fix: <one-liner>. Full detector now passes with CPU fallback."]
[If instrumentation only: "Root cause identified: <brief>. [Escalation needed OR targeted fix deferred to next loop]"]

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/
```

**Commands:**
```bash
git add -A
git commit -m "<message from above>"
git push
```

## How-To Map

### Environment
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Test Execution Pattern
```bash
# Small detector (baseline with instrumentation)
DBEX_SMOKE_DETECTOR_SIZE=small pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -k "not expansion and not detector_microslip" --timeout=180 \
  2>&1 | tee <artifact_path>/pytest_stage_b_small_instrumented.log

# Full detector (problem case with instrumentation)
DBEX_SMOKE_DETECTOR_SIZE=full pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -k "not expansion and not detector_microslip" --timeout=180 \
  2>&1 | tee <artifact_path>/pytest_stage_b_full_instrumented.log
```

### Condition Extraction
```bash
# Parse JSON diagnostics from log
grep "CPU_FALLBACK_DIAGNOSTICS_" <log_file> | \
  sed 's/.*CPU_FALLBACK_DIAGNOSTICS_//' | \
  jq -s '.' > cpu_fallback_conditions.json
```

### Likely Root Causes (Ranked by Probability)

**1. Device type check bug (40% likelihood):**
- Current: `str(device).startswith("cuda")`
- May fail if device is not string or has unexpected format
- Fix: Use `device.type == "cuda"` (PyTorch standard)

**2. ROI mode detection bug (30% likelihood):**
- `use_stage_a_roi_mode` may be True despite full detector configuration
- Check: panel_slices computation, Stage A telemetry roi_mode field
- Fix: Verify ROI mode extraction from stage_a_telemetry (line ~2170)

**3. Config propagation bug (20% likelihood):**
- `config.stage_b_full_eval_on_cpu` may be False despite default True
- Check: RefinementConfig initialization, StageB.configure() method
- Fix: Ensure config object passed to StageB has correct defaults

**4. Context propagation bug (10% likelihood):**
- `stage_a_ctx` may be None due to engine/stage handoff issue
- Escalation required (architectural change outside _build_stage_b_params scope)

## Pitfalls To Avoid

1. **DO NOT** remove instrumentation until root cause confirmed and fix validated
2. **DO NOT** apply speculative fixes — wait for diagnostic evidence
3. **DO NOT** modify production logic before seeing condition values
4. **DO** capture stdout to file (use `tee`) so diagnostic JSON is preserved
5. **DO** verify JSON parsing succeeds before analyzing conditions
6. **DO** check BOTH _build_stage_b_params AND _build_stage_b_lbfgs_closure diagnostics
7. **DO** run small detector test first to establish baseline
8. **DO** document exact condition values in decision.md (not just "it failed")

## If Blocked

**Scenario 1:** Instrumentation print statements not appearing in logs
→ Check that `flush=True` is present
→ Verify pytest is not buffering stdout (use `-s` flag)
→ Try running without pytest capture: `python -c "import tests.dbex.test_torch_refine_smoke; tests.dbex.test_torch_refine_smoke.test_stage_b_shell_modifiers()"`

**Scenario 2:** JSON parsing fails (malformed output)
→ Manually inspect log file around "CPU_FALLBACK_DIAGNOSTICS" lines
→ Check for partial output or exception during print
→ Fallback: extract conditions manually from log text

**Scenario 3:** All conditions appear TRUE but `use_stage_b_cpu_fallback=false`
→ Logic bug in boolean expression (line 2178-2182)
→ Add additional print statement showing intermediate values:
```python
cond1 = config.stage_b_full_eval_on_cpu
cond2 = str(device).startswith("cuda")
cond3 = not use_stage_a_roi_mode
print(f"CPU_FALLBACK_CONDS: cond1={cond1}, cond2={cond2}, cond3={cond3}, result={cond1 and cond2 and cond3}")
```

**Scenario 4:** Fix applied but test still fails with OOM
→ Check telemetry shows `eval_device="cpu"` (verify fix worked)
→ If eval_device still "cuda", device routing broken elsewhere (escalate)
→ If eval_device "cpu" but still OOM, different issue (not CPU fallback bug)

**Scenario 5:** Multiple conditions FALSE
→ Config object is corrupted or not being forwarded correctly
→ Add instrumentation to StageB.run() entry point (line ~116) to check config state
→ Escalate to engine/stage architecture review

## Findings Applied

- **PERF-WARM-011** — Stage B CPU fallback canonical requirement (config.stage_b_full_eval_on_cpu default True)
- **PERF-WARM-012** — CPU Stage A context cloning requirement (clone stage_a_ctx to CPU when fallback active)
- **REFINE-008** — Stage B ±1% improvement gate (will validate after CPU fallback working)
- **PHYSICS-LOSS-001/002** — Variance-weighted loss + sigma_floor guard (preserved in helpers)
- **POLICY-001** — Environment Freeze (instrumentation is temporary diagnostic code, not production change)

## Pointers

### Normative Specs
- `docs/spec-db-workflow.md` §7 — Refinement Protocol Architecture, Stage B definition
- `docs/spec-db-core.md` §Variance-Weighted Loss — Sigma floor guard mandate

### Code Locations
- CPU fallback logic: `dbex/nanobrag_refinement.py:2178-2182` (_build_stage_b_params)
- Eval device selection: `dbex/nanobrag_refinement.py:2368` (_build_stage_b_lbfgs_closure)
- StageB.run() entry: `dbex/refinement/stage_b.py:116-129`
- Engine delegation: `dbex/nanobrag_refinement.py:3036-3108`

### Related Artifacts
- Loop i=212 partial fix: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/` (final Bragg device only)
- Loop i=213 investigation: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/decision.md` (hypothesis rejected)
- PERF-WARM-011 finding: `docs/findings.md` row 26 (CPU fallback requirement)
- PERF-WARM-012 finding: `docs/findings.md` row 27 (warm context cloning, marked Resolved but engine delegation path may not have it)

### Testing Selectors
- `docs/TESTING_GUIDE.md` §2 — test_stage_b_shell_modifiers Active selector
- `docs/development/TEST_SUITE_INDEX.md` — Stage B smoke test entry

## Next Up (Optional)

**If Fix Applied and Tests Pass:**
1. Remove instrumentation (clean up print statements)
2. Run full Phase C validation suite:
   - Stage B small detector (verify no regression)
   - Stage B full detector (verify CPU fallback + warm cache telemetry)
   - DB-AT-024 mapping consistency (verify Stage B extraction didn't break bridge)
3. Update `implementation.md` Phase C2.2 status to COMPLETE
4. Proceed to Phase C3 planning (full validation + docs) next loop

**If Escalation Required:**
→ Document architectural issue in decision.md
→ Await supervisor guidance (may need engine/config refactor)
→ Consider temporary workaround (e.g., force CPU device in test fixture)
