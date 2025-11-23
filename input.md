# Phase C2.2 CPU Fallback Gradient Bugfix — Ralph Do Now

## Summary
Fix Stage B CPU fallback gradient bug by creating shell_modifier_raw parameters on CPU device when CPU fallback is active, preventing gradient chain break from CUDA→CPU `.to()` operation.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2 gradient bugfix)

## Branch
integration

## Mapped Tests
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (full detector, CPU fallback path validation)
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (small detector, regression guard)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/`
- root_cause_analysis.md (comprehensive RCA with 95% confidence)
- pytest_stage_b_full.log
- pytest_stage_b_small.log
- validation_metrics.json (test statuses + telemetry structure)
- decision.md (Path A/B template)
- summary.md (Turn Summary block)

## Do Now

### Context
Loop i=215 (Ralph) successfully implemented the 7-line device routing fix, resolving CUDA OOM in `_build_final_bragg_from_stage_b_telemetry`. However, this exposed a pre-existing gradient bug in the CPU fallback path: shell modifier parameters are created on CUDA (line 2134: `device=stage_b_param_device` where `stage_b_param_device = torch.device(config.device)` = CUDA), but when CPU fallback is active, the closure uses `eval_device="cpu"` (line 2383). The shell modifiers are computed from the CUDA parameter (line 2379), then moved to CPU via `.to(device=eval_device)` in lines 2434-2435. **This `.to()` operation breaks the autograd gradient chain**, causing LBFGS to fail with "element 0 of tensors does not require grad and does not have a grad_fn".

**Root cause identified with HIGH confidence (~95%)**: Device mismatch between parameter creation (CUDA) and closure execution (CPU) causes gradient chain break. See `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/root_cause_analysis.md` for full analysis.

**The Fix (ONE line)**: Create `shell_modifier_raw` on CPU when `use_stage_b_cpu_fallback=True`, matching `eval_device` in the closure.

### Tasks

1. **Review Evidence**
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/root_cause_analysis.md` (comprehensive RCA)
   - Read loop i=215 blocker.md and telemetry_stage_b_full.json (gradient error signature)
   - Locate the bug: dbex/nanobrag_refinement.py:2134-2138 (`stage_b_param_device` initialization)

2. **Apply Gradient Bugfix (ONE line)**
   - **File:** `dbex/nanobrag_refinement.py`
   - **Line:** 2134
   - **OLD:**
     ```python
     stage_b_param_device = torch.device(config.device)
     ```
   - **NEW:**
     ```python
     stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)
     ```
   - **Explanation:** When CPU fallback is active, parameters must be created on CPU to match `eval_device="cpu"` in the closure (line 2383), preventing gradient chain break from `.to()` operation at lines 2434-2435.

3. **Run Full Detector Test (CPU Fallback Validation)**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/pytest_stage_b_full.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/pytest_stage_b_full.log
   ```
   - **Expected:** PASSED (CPU fallback active, gradient bug fixed, ~15s runtime)
   - **Telemetry:** `status='ok'`, `closure_evals > 1`, `loss_trace_sample` not empty, shell modifiers show >0.2% delta

4. **Run Small Detector Test (Regression Guard)**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
   > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/pytest_stage_b_small.log 2>&1
   echo "Exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/pytest_stage_b_small.log
   ```
   - **Expected:** PASSED (ROI mode, no CPU fallback, unaffected by fix, ~15s runtime)

5. **Extract Validation Metrics (T0 Inline Probe)**
   ```bash
   cd plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/ && python3 -c '
import re
import json

full_log = open("pytest_stage_b_full.log").read()
small_log = open("pytest_stage_b_small.log").read()

full_status = "PASSED" if re.search(r"1 passed", full_log) else "FAILED"
small_status = "PASSED" if re.search(r"1 passed", small_log) else "FAILED"

metrics = {
    "full_detector": full_status,
    "small_detector": small_status,
    "overall_verdict": "PASS" if (full_status == "PASSED" and small_status == "PASSED") else "FAIL"
}

with open("validation_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))
'
   ```
   - **Save as:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/validation_metrics.json`

6. **Decision Synthesis**
   - Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/decision.md`
   - **Path A (both tests PASS):** Gradient bugfix successful → remove instrumentation (lines 2185-2198, 2386-2395) → mark Phase C2.2 COMPLETE → next loop: Phase C validation (C3-C5: telemetry completeness + full validation + DB-AT-024)
   - **Path B (full detector FAIL):** Gradient bug not fully resolved → document specific error signature → escalate to Galph for deeper architectural review
   - **Path C (small detector FAIL):** Regression introduced by fix → revert bugfix → investigate alternative approach
   - Include:
     - Decision path chosen
     - Test outcomes (exit codes, key metrics)
     - Telemetry structure validation (status, closure_evals, loss_trace_sample)
     - Confidence assessment for chosen path
     - Next actions

7. **Remove Instrumentation (Conditional on Path A)**
   - **ONLY if both tests PASS:** Remove diagnostic prints added in loop i=214
   - **Lines to remove:**
     - `dbex/nanobrag_refinement.py:2185-2198` (CPU fallback diagnostics in `_build_stage_b_params`)
     - `dbex/nanobrag_refinement.py:2386-2395` (CPU fallback diagnostics in `_build_stage_b_lbfgs_closure`)
   - **If Path B/C:** KEEP instrumentation for further debugging

8. **Update Implementation Plan**
   - **File:** `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
   - **If Path A:** Mark Phase C2.2 COMPLETE (gradient bugfix + device routing fix both landed)
   - **If Path B/C:** Update Phase C2.2 status with blocker details

9. **Write Summary**
   - Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/summary.md`
   - **Format:** Level-3 heading `### Turn Summary`, 3-5 single-line sentences, `Artifacts:` line
   - **Content:** (a) What shipped (gradient bugfix + instrumentation removal if applicable), (b) main problem and resolution (device mismatch causing gradient chain break, fixed via CPU parameter creation), (c) single next step (Phase C validation if Path A, escalation if Path B/C)
   - **Example (Path A):**
     ```markdown
     ### Turn Summary
     Fixed Stage B CPU fallback gradient bug by creating shell_modifier_raw parameters on CPU when fallback active, preventing gradient chain break.
     Root cause was device mismatch: parameters created on CUDA, closure on CPU, .to() operation broke autograd graph.
     Both tests PASSED (full detector CPU fallback + small detector regression guard), instrumentation removed, Phase C2.2 COMPLETE.
     Next: Phase C validation suite (telemetry completeness + DB-AT-024 mapping parity).
     Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/ (root_cause_analysis.md, pytest_*.log, validation_metrics.json)
     ```

10. **Commit and Push**
    ```bash
    git add -A
    git commit -m "ARCH-REFINE-FLOW-001 Phase C2.2: fix Stage B CPU fallback gradient bug

ROOT CAUSE: shell_modifier_raw created on CUDA (config.device), but when
CPU fallback active (use_stage_b_cpu_fallback=True), closure uses eval_device='cpu'.
Shell modifiers moved to CPU via .to() at lines 2434-2435, breaking autograd chain.

FIX: Create shell_modifier_raw on CPU when use_stage_b_cpu_fallback=True,
matching eval_device in closure (line 2134 one-line change). Prevents gradient
chain break; LBFGS can now trace back to parameters.

VALIDATION: Full detector test PASSED (CPU fallback active, gradient bug fixed),
small detector test PASSED (regression guard). Removed diagnostic instrumentation
from loop i=214 (lines 2185-2198, 2386-2395).

FINDINGS: Device-aware parameter initialization critical for CPU fallback paths.
PyTorch .to(device=...) breaks autograd chain when moving trainable parameters.

tests: Stage B full+small detector smokes PASSED"
    git push
    ```

## How-To Map

### 1. Apply Gradient Bugfix
- **File:** `dbex/nanobrag_refinement.py`
- **Line:** 2134
- **Change:** `stage_b_param_device = torch.device("cpu") if use_stage_b_cpu_fallback else torch.device(config.device)`
- **Rationale:** When CPU fallback active, parameters must match closure eval_device (CPU) to prevent gradient chain break

### 2. Run Tests
- **Full detector:** CPU fallback path validation (DBEX_SMOKE_DETECTOR_SIZE=full, panel mode, use_stage_b_cpu_fallback=true)
- **Small detector:** Regression guard (DBEX_SMOKE_DETECTOR_SIZE=small, ROI mode, no CPU fallback)
- **Environment:** KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 per CONFORMANCE-001 + RUNTIME-001

### 3. Extract Metrics
- **Method:** T0 inline Python probe (grep test logs for "1 passed", parse telemetry JSON if available)
- **Metrics:** full_detector status, small_detector status, telemetry_status_ok, closure_evals, loss_trace_length
- **Output:** validation_metrics.json

### 4. Decision Synthesis
- **Template:** 4-path (A: both PASS, B: full FAIL, C: small FAIL regression, D: N/A)
- **Artifact:** decision.md with test outcomes, telemetry validation, confidence, next actions

### 5. Conditional Instrumentation Removal
- **Trigger:** Both tests PASS (Path A)
- **Lines:** 2185-2198 (_build_stage_b_params diagnostics), 2386-2395 (_build_stage_b_lbfgs_closure diagnostics)
- **Rationale:** Diagnostic prints no longer needed; CPU fallback activation confirmed correct in loop i=214

## Pitfalls To Avoid

1. **DO NOT** revert loop i=215 device routing fix (OOM resolution is correct and necessary)
2. **DO NOT** remove instrumentation if any test FAILS (keep diagnostics for debugging)
3. **DO NOT** create shell_modifier_raw on CPU unconditionally (breaks ROI mode which uses CUDA)
4. **DO NOT** move the entire optimizer to CPU (more complex, breaks LBFGS state)
5. **DO** verify telemetry shows `status='ok'` and `closure_evals > 1` (not just pytest PASS)
6. **DO** check `loss_trace_sample` is not empty (confirms optimizer actually ran)
7. **DO** verify small detector regression guard PASSES (ROI mode unaffected by fix)
8. **DO** preserve loop i=215 changes (_build_final_bragg_from_stage_b_telemetry device routing + CPU context cloning)
9. **DO** commit with comprehensive message citing root cause, fix, validation, findings
10. **DO** use T0 inline probe for metrics extraction (no separate script needed for simple log parsing)

**Environment (CRITICAL):**
- Assume environment is FROZEN per POLICY-001
- DO NOT install/upgrade packages
- DO NOT modify CUDA/torch versions
- If import fails, record error signature in decision.md and mark blocked

**Normative Math/Physics:**
- Gradient computation is governed by PyTorch autograd semantics, not DBEX specs
- Reference PyTorch documentation for `.to()` behavior: https://pytorch.org/docs/stable/generated/torch.Tensor.to.html
- Device-aware parameter initialization is standard PyTorch practice for multi-device training

## If Blocked

1. **Full detector test still FAILS with gradient error:**
   - Document exact error message and line number
   - Check if `.to()` operation still present on any shell_modifier path
   - Verify `stage_b_param_device` value in closure diagnostics
   - Escalate to Galph with detailed gradient trace

2. **Small detector test FAILS (regression):**
   - Verify ROI mode test still uses CUDA (no CPU fallback)
   - Check if conditional `if use_stage_b_cpu_fallback else` logic is correct
   - Revert fix if regression confirmed; document in decision.md

3. **Full detector test PASSES but telemetry shows status='error':**
   - Check telemetry JSON for error message (different from gradient bug?)
   - Verify closure_evals and loss_trace_sample fields
   - May indicate different bug unmasked by this fix

## Findings Applied

- **PERF-WARM-011:** Stage B CPU fallback requirement (use_stage_b_cpu_fallback when config.stage_b_full_eval_on_cpu=True + CUDA device + panel mode)
- **PERF-WARM-012:** CPU Stage A context cloning (already implemented in loop i=215 lines 3115-3136)
- **REFINE-008:** Stage B ±1% shell modifier delta tolerance (will be validated in Phase C validation suite)
- **PHYSICS-LOSS-001/002:** Variance-weighted loss + sigma_floor guard (preserved in closure)
- **POLICY-001:** Environment Freeze — no package installs/upgrades
- **RUNTIME-001:** NANOBRAGG_DISABLE_COMPILE=1 for test runs
- **CONFORMANCE-001:** KMP_DUPLICATE_LIB_OK=TRUE for OpenMP conflicts
- **GRADIENT-001:** Autograd graph preservation (VIOLATED by .to() operation, FIXED by this patch)

## Pointers

- **Root Cause Analysis:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T102034Z/root_cause_analysis.md (comprehensive RCA with evidence chain, fix rationale, confidence assessment)
- **Loop i=215 Artifacts:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/ (blocker.md, telemetry_stage_b_full.json, pytest_stage_b_full.log)
- **Loop i=214 Diagnostics:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/ (instrumentation_summary.md, cpu_fallback_conditions.json — confirmed CPU fallback logic is CORRECT)
- **Implementation Plan:** plans/active/ARCH-REFINE-FLOW-001/implementation.md (Phase C2.2 checklist)
- **Spec References:**
  - docs/spec-db-runtime.md:21-23 (PyTorch autograd requirements)
  - docs/findings.md row 39 (PERF-WARM-011), row 40 (PERF-WARM-012)
  - docs/findings.md row 16 (GRADIENT-001 — autograd preservation)
- **Testing Guide:** docs/TESTING_GUIDE.md §2 (Stage B smoke selectors, environment flags)

## Next Up (Optional)

If both tests PASS (Path A), next loop will be:
- **Phase C Validation Suite:** Combine C3-C5 tasks (telemetry completeness + Stage B full/small smokes + DB-AT-024 mapping parity) in single validation loop
- **Expected:** All tests PASS → Phase C COMPLETE → Galph plans Phase D (Stage C extraction)

If either test FAILS (Path B/C), next loop will be:
- **Escalation/Debug:** Galph reviews blocker and decides on alternative approach or deeper architectural investigation

## Doc Sync Plan

**Not applicable** (no new tests authored this loop; existing Stage B smoke selectors unchanged)
