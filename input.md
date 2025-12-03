# Input for Ralph (Loop 2025-12-03T050000Z)

## Summary
Thread `oversample` parameter through RefinementConfig and warm simulator context creation to fix 290/292 DetectorConfig instances having wrong default value.

## Mode
none (diagnostics: config lifecycle fix per Phase C plan)

## InitiativeType
diagnostics

## Focus
DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch oversample parameter investigation (Phase C: config lifecycle fix)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity` (will validate oversample=3 preserved across 292 instances, chi²/pixel ≤1e2)
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity` (will validate ROI correlation ≥0.2)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression check for warm context changes)

## Artifacts
`plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/`
- `phase_c_planning.md` (supervisor-side analysis, already created)
- `refinement_config_oversample.patch` (config field addition)
- `stage_a_utils_oversample.patch` (config threading)
- `pytest_db_at_028_debug.log` (debug validation: 292/292 oversample=3)
- `pytest_db_at_028_029_clean.log` (clean validation: both PASS)
- `summary.md` (loop summary)

## Do Now

**Context**: Phase B deep copy fix was insufficient—it prevents mutation WITHIN Detector instances but doesn't address the real problem: 290/292 DetectorConfig instances created with default `oversample=-1` instead of explicit `oversample=3`. Supervisor-side analysis identified 6 call sites in `stage_a_utils.py` where `create_detector_config()` is called without passing the `oversample` parameter.

**Fix Strategy**: Thread `oversample` through `RefinementConfig` (job-level config) → warm simulator context builders → `create_detector_config` calls.

### Task C.1: Add oversample field to RefinementConfig

**File**: `dbex/refinement/config.py`

**Change**: Add new field after line 74 (after `enable_stage_a_warm_cache` field):

```python
# nanobrag_torch oversampling (DIAG-NANOBRAGG-OVERSAMPLE-001 Phase C)
# Oversampling factor for detector simulation (1, 2, 3, ...).
# Default 3 matches calibration metadata standard and prevents auto-selection.
# -1 triggers auto-selection based on detector size (not recommended for reproducibility).
oversample: int = 3
```

**Validation**: Field added, no syntax errors

### Task C.2: Update _build_stage_a_context signature

**File**: `dbex/refinement/stage_a_utils.py`

**Find the function signature** (around line 220-240):
```python
def _build_stage_a_context(
    detector,
    beam,
    hkl_grid,
    hkl_metadata,
    crystal_model,
    beam_config,
    trusted_mask,
    roi_sample_fraction: float = 0.15,
    panel_slices=None,
    device: str = "cpu",
    dtype=torch.float32,
) -> StageAContext:
```

**Add config parameter**:
```python
def _build_stage_a_context(
    detector,
    beam,
    hkl_grid,
    hkl_metadata,
    crystal_model,
    beam_config,
    trusted_mask,
    roi_sample_fraction: float = 0.15,
    panel_slices=None,
    device: str = "cpu",
    dtype=torch.float32,
    config: Optional['RefinementConfig'] = None,  # DIAG-NANOBRAGG-OVERSAMPLE-001
) -> StageAContext:
```

**Add import** at top of file (around line 10-20, after other imports):
```python
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dbex.refinement.config import RefinementConfig
```

**Add default value extraction** at start of function body (after docstring, before any logic):
```python
# Extract oversample from config or use default (DIAG-NANOBRAGG-OVERSAMPLE-001)
oversample_value = 3  # Default fallback
if config is not None:
    oversample_value = config.oversample
```

### Task C.3: Pass oversample to create_detector_config (4 call sites in _build_stage_a_context)

**Call site 1** (around line 286-290, panel-mode simulators):
```python
# OLD:
detector_config = create_detector_config(
    panel=panel,
    beam=beam,
    trusted_mask=trusted_mask[pid]
)

# NEW:
detector_config = create_detector_config(
    panel=panel,
    beam=beam,
    trusted_mask=trusted_mask[pid],
    oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
)
```

**Call site 2** (around line 326-331, ROI-mode simulators):
```python
# OLD:
detector_config = create_detector_config(
    panel=panel,
    beam=beam,
    trusted_mask=trusted_mask[int(pid)],
    roi_bbox=bbox,
)

# NEW:
detector_config = create_detector_config(
    panel=panel,
    beam=beam,
    trusted_mask=trusted_mask[int(pid)],
    roi_bbox=bbox,
    oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
)
```

### Task C.4: Update _compute_panel_loss signature and cold-path calls

**Find the function signature** (around line 400-420):
```python
def _compute_panel_loss(
    # ... existing parameters ...
) -> Tuple[torch.Tensor, torch.Tensor, int, int]:
```

**Add config parameter** (keep existing parameters, just add at end):
```python
def _compute_panel_loss(
    # ... existing parameters ...
    config: Optional['RefinementConfig'] = None,  # DIAG-NANOBRAGG-OVERSAMPLE-001
) -> Tuple[torch.Tensor, torch.Tensor, int, int]:
```

**Add default value extraction** at start of function body:
```python
# Extract oversample from config or use default (DIAG-NANOBRAGG-OVERSAMPLE-001)
oversample_value = 3
if config is not None:
    oversample_value = config.oversample
```

**Call site 3** (around line 480-484, cold-path diagnostic branch):
```python
# OLD:
detector_config = create_detector_config(
    panel=detector[pid],
    beam=beam,
    trusted_mask=panel_trusted_mask
)

# NEW:
detector_config = create_detector_config(
    panel=detector[pid],
    beam=beam,
    trusted_mask=panel_trusted_mask,
    oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
)
```

**Call site 4** (around line 572-576, cold-path fast-path branch):
```python
# OLD:
detector_config = create_detector_config(
    panel=detector[pid],
    beam=beam,
    trusted_mask=panel_trusted_mask
)

# NEW:
detector_config = create_detector_config(
    panel=detector[pid],
    beam=beam,
    trusted_mask=panel_trusted_mask,
    oversample=oversample_value,  # DIAG-NANOBRAGG-OVERSAMPLE-001
)
```

### Task C.5: Update all callers of _build_stage_a_context and _compute_panel_loss

**Find all callers using grep**:
```bash
cd /home/ollie/Documents/diffbragg_example
grep -n "_build_stage_a_context(" dbex/refinement/*.py
grep -n "_compute_panel_loss(" dbex/refinement/*.py
```

**For each caller**: Add `config=config` parameter to the function call.

**Expected callers**:
- `dbex/refinement/stage_a.py` (StageA.run) - should have access to `self.config` or similar
- Possibly `dbex/refinement/stage_a_utils.py` (if _compute_panel_loss calls _build_stage_a_context)

**Pattern**:
```python
# OLD:
stage_a_ctx = _build_stage_a_context(
    detector=detector,
    beam=beam,
    # ... other args ...
)

# NEW:
stage_a_ctx = _build_stage_a_context(
    detector=detector,
    beam=beam,
    # ... other args ...
    config=config,  # DIAG-NANOBRAGG-OVERSAMPLE-001
)
```

### Task C.6: Debug validation (keep nanobrag instrumentation)

**Purpose**: Verify that ALL 292 DetectorConfig instances now have `oversample=3`

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv -s tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/pytest_db_at_028_debug.log 2>&1
```

**Expected debug output pattern** (should see this for ALL 292 runs):
```
[DIAG-OVERSAMPLE] self.detector.config.oversample=3
```

**Should NOT see**:
- `[DIAG-OVERSAMPLE] self.detector.config.oversample=-1`
- `[DIAG-OVERSAMPLE] Entering auto-selection branch`

**Analysis**:
```bash
grep "oversample=3" plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/pytest_db_at_028_debug.log | wc -l
# Expected: 292 (not 2!)

grep "oversample=-1" plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/pytest_db_at_028_debug.log | wc -l
# Expected: 0

grep "Entering auto-selection" plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/pytest_db_at_028_debug.log | wc -l
# Expected: 0
```

**Document findings** in `debug_validation.md`:
- Count of oversample=3 instances (should be 292/292)
- Count of oversample=-1 instances (should be 0)
- Test outcome (PASS or FAIL with chi²/pixel value)

### Task C.7: Remove nanobrag debug instrumentation (if debug validation successful)

**ONLY proceed if Task C.6 showed 292/292 oversample=3**

**File**: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch/src/nanobrag_torch/simulator.py`

Remove all `[DIAG-OVERSAMPLE]` debug print statements added in Phase A (around lines 770-790).

**Rebuild nanobrag_torch**:
```bash
cd /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch
pip install -e . > /home/ollie/Documents/diffbragg_example/plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/nanobragg_rebuild_clean.log 2>&1
```

### Task C.8: Clean validation (WITHOUT debug instrumentation)

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/pytest_db_at_028_029_clean.log 2>&1
```

**Expected**: Both tests PASS
- DB-AT-028: `chi²/pixel initial ≤ 1e2` (baseline was 1.091e+05, ~1091× over bound)
- DB-AT-029: `median ROI correlation before ≥ 0.2` (baseline was -0.037)

**If tests FAIL**: Document failure signature and escalate to Galph. Oversample fix may not be the only issue.

### Task C.9: Regression check

**Command**:
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/pytest_stage_a_expansion.log 2>&1
```

**Expected**: PASS (no regression from threading `config` parameter)

### Task C.10: Create patch files

**For RefinementConfig change**:
```bash
cd /home/ollie/Documents/diffbragg_example
git add dbex/refinement/config.py
git diff --cached dbex/refinement/config.py > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/refinement_config_oversample.patch
git reset HEAD dbex/refinement/config.py
```

**For stage_a_utils changes**:
```bash
git add dbex/refinement/stage_a_utils.py
git diff --cached dbex/refinement/stage_a_utils.py > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/stage_a_utils_oversample.patch
git reset HEAD dbex/refinement/stage_a_utils.py
```

**For any other changed files** (callers):
```bash
git add dbex/refinement/stage_a.py  # If modified
git diff --cached dbex/refinement/stage_a.py > plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/stage_a_caller_oversample.patch
git reset HEAD dbex/refinement/stage_a.py
```

### Task C.11: Update docs/findings.md

Find the `[DIAG-OVERSAMPLE-001]` entry and update it with Phase C resolution details (see Pointers section for template).

### Task C.12: Write loop summary

Create `summary.md` documenting Phase C implementation complete, validation results, and unblocked initiatives.

## How-To Map

### Step-by-step execution order:

1. **Add oversample field** to RefinementConfig (Task C.1)
2. **Update _build_stage_a_context signature** and add oversample extraction (Task C.2)
3. **Pass oversample to 4 create_detector_config calls** in _build_stage_a_context (Task C.3)
4. **Update _compute_panel_loss signature** and pass oversample to 2 cold-path calls (Task C.4)
5. **Find and update all callers** of _build_stage_a_context and _compute_panel_loss (Task C.5)
6. **Debug validation** with nanobrag instrumentation (Task C.6), analyze counts
7. **Remove nanobrag debug prints** if validation successful (Task C.7)
8. **Clean validation** both DB-AT-028/029 (Task C.8)
9. **Regression check** Stage A expansion (Task C.9)
10. **Create patch files** for all changed files (Task C.10)
11. **Update findings.md** with Phase C resolution (Task C.11)
12. **Write summary.md** (Task C.12)

## Pitfalls To Avoid

1. **Do NOT skip Task C.5 (caller updates)** — threading `config` parameter through call chain is critical
2. **Do NOT proceed to Task C.7 if Task C.6 shows <292 oversample=3** — escalate to Galph if counts don't match
3. **Do NOT assume tests will PASS** — oversample may not be the only issue; document failure signature if C.8 fails
4. **Do NOT forget TYPE_CHECKING import** — `RefinementConfig` forward reference needed for type hints
5. **Do NOT mix up Optional parameter placement** — add `config` parameter at END of existing parameter lists
6. **Do NOT skip patch file creation (Task C.10)** — Environment Freeze compliance requirement
7. **Do NOT skip regression check (Task C.9)** — must verify no breakage from signature changes

## If Blocked

See detailed blockers handling in the original input.md section. Key points:
- If callers hard to find: use grep, document any that can't be updated
- If debug validation <292: document pattern, escalate, DO NOT proceed to clean validation
- If clean validation fails: compare to baseline, document progress, escalate
- If regression fails: check error type, verify imports, escalate

## Findings Applied

- **phase_c_planning.md**: Supervisor callchain analysis, 6 call sites identified
- **Phase B summary.md**: Deep copy insufficient, 2/292 vs 290/292 pattern
- **Phase A root_cause_analysis.md**: Original hypothesis was wrong

## Pointers

**Implementation Files**:
- `dbex/refinement/config.py:74` (add oversample field after enable_stage_a_warm_cache)
- `dbex/refinement/stage_a_utils.py:220-240` (_build_stage_a_context signature)
- `dbex/refinement/stage_a_utils.py:286-290, 326-331` (4 call sites in _build_stage_a_context)
- `dbex/refinement/stage_a_utils.py:400-420` (_compute_panel_loss signature)
- `dbex/refinement/stage_a_utils.py:480-484, 572-576` (2 cold-path call sites)

**Test / Acceptance**:
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity`
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity`
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

## Next Up

**If successful**: Mark DIAG-NANOBRAGG-OVERSAMPLE-001 done, unblock ARCH-SIM-CONSTRUCTION-001 and ARCH-REFACTOR-001 Phase D.3
**If requires iteration**: Document progress, consider spec_change if tests fundamentally incompatible
