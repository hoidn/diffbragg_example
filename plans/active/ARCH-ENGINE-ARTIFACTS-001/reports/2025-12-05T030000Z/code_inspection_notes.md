# Code Inspection Notes — ARCH-ENGINE-ARTIFACTS-001 Phase A.3

## Objective
Verify that Stage C populates the `bragg_full` artifact field in `StageCArtifacts`.

## Findings

### Stage C Already Wires Artifacts Correctly

The implementation task described in `input.md` assumed the artifact was not being populated, but inspection shows the code already does this correctly:

**Data Flow:**

1. **Creation (stage_c.py:1150):**
   ```python
   bragg_full_stage_c = np.zeros((n_panels, *panel_shape), dtype=np.float32)
   ```
   Creates numpy float32 array with correct shape.

2. **Population (stage_c.py:1247):**
   ```python
   bragg_full_stage_c[pid] = panel_bragg_scaled.cpu().numpy().astype(np.float32)
   ```
   Converts torch tensor to CPU-resident numpy float32 and populates array.

3. **Return (stage_c.py:1336):**
   ```python
   return stage_result, telemetry_c, status_c, message_c, bragg_full_stage_c, param_deltas_c
   ```
   Returns numpy array as 5th element of tuple.

4. **Unpacking (stage_c.py:1712):**
   ```python
   stage_result, telemetry_c, status_c, message_c, bragg_full, param_deltas_c = self._run_lbfgs(...)
   ```
   Unpacks return value as `bragg_full`.

5. **Artifact Creation (stage_c.py:1726):**
   ```python
   artifacts = StageCArtifacts(bragg_full=bragg_full)
   ```
   Passes numpy array to StageCArtifacts dataclass.

**Root Cause of Task Mismatch:**

The task in `input.md` was based on an outdated understanding of the code. Prior to ARCH-REFACTOR-001 Phase C, the `_run_stage_c_lbfgs` helper was a separate module function. During Phase C (inlining helpers into Stage classes), the helper became `StageC._run_lbfgs()` and the artifact wiring remained intact.

The task instructions assumed `_run_lbfgs` returned a torch tensor that needed conversion, but the code already converts to numpy inside `_run_lbfgs` before returning.

### Changes Made This Loop

Since the artifact wiring was already correct, the only change needed was updating the docstring to document the normative requirement:

**File:** `dbex/refinement/artifacts.py:98-115`

**Change:**
```diff
-    - Replaces engine._stage_c_bragg_full private attribute
+    - Always populated by Stage C; replaces engine._stage_c_bragg_full private attribute

     Normative Requirements:
     - Must be numpy array (CPU-resident for HDF5 writer)
     - Shape must match detector geometry [n_panels, slow_pixels, fast_pixels]
+    - Stage C MUST populate bragg_full unconditionally (not just when terminal)
+    - Cite: docs/spec-db-workflow.md §41 (stage contract + outputs)
```

### Implementation Plan Update

Marked Phase A.3 complete in `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md`:
- [x] A3: Update Stage C wrapper to emit `{"bragg_full": np.ndarray}` via new API

## Conclusion

Phase A.3 was already complete from prior ARCH-STAGE-CONTEXT-001 work. This loop only needed to:
1. Verify the artifact wiring is correct (✓)
2. Update docstring to document normative requirements (✓)
3. Update implementation plan checklist (✓)

No code changes to Stage C were needed because the artifact population was already correctly implemented.
