# Ralph Input — Loop i=253

## Summary
Refactor `_build_stage_a_params` signature to use single `StageAInputContext` parameter instead of 13 positional args.

## Focus
ARCH-STAGE-CONTEXT-CONSOLIDATION — Stage Context Parameter Consolidation (Phase C.1)

## Branch
`integration`

## Mapped Tests
- `pytest tests/dbex/test_refinement_context.py -v` (verify module import)
- `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_smoke -v --smoke-detector-size=small` (Stage A regression guard)

## Artifacts
`plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/`

---

## Do Now

**Focus Item:** ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.1
**Action Type:** Implementation (Signature Refactoring)

### Implement: `dbex/refinement/stage_a.py::_build_stage_a_params`

Refactor the signature from 13 positional parameters to a single typed context:

#### Step 1: Update the function signature (stage_a.py:100-114)

**FROM:**
```python
def _build_stage_a_params(
    self,
    crystal,
    detector,
    inputs,
    config: 'RefinementConfig',
    device,
    dtype,
    hkl_grid,
    hkl_metadata,
    sigma_floor_sq_cache,
    baseline_crystal,
    baseline_detector,
    beam
):
```

**TO:**
```python
def _build_stage_a_params(
    self,
    config: 'RefinementConfig',
    input_ctx: 'StageAInputContext'
):
```

#### Step 2: Add import and unpack in function body

At the top of `_build_stage_a_params` (after the existing imports around line 126-128), add:

```python
from dbex.refinement.context import StageAInputContext

# Unpack input context for backwards compatibility with existing function body
crystal = input_ctx.crystal
detector = input_ctx.detector
beam = input_ctx.beam
inputs = input_ctx.inputs
baseline_crystal = input_ctx.baseline_crystal
baseline_detector = input_ctx.baseline_detector
hkl_grid = input_ctx.hkl_grid
hkl_metadata = input_ctx.hkl_metadata
sigma_floor_sq_cache = input_ctx.sigma_floor_sq_cache
device = input_ctx.device
dtype = input_ctx.dtype
```

#### Step 3: Update the call site (stage_a.py:1803-1816)

**FROM:**
```python
helper1_result = self._build_stage_a_params(
    crystal=crystal,
    detector=detector,
    inputs=refinement_inputs,
    config=self._config,
    device=device,
    dtype=dtype,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    sigma_floor_sq_cache=sigma_floor_sq_cache,
    baseline_crystal=baseline_crystal,
    baseline_detector=baseline_detector,
    beam=beam
)
```

**TO:**
```python
# ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.1: Construct typed input context
from dbex.refinement.context import StageAInputContext
input_ctx = StageAInputContext(
    crystal=crystal,
    detector=detector,
    beam=beam,
    inputs=refinement_inputs,
    baseline_crystal=baseline_crystal,
    baseline_detector=baseline_detector,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    sigma_floor_sq_cache=sigma_floor_sq_cache,
    device=device,
    dtype=dtype,
)
helper1_result = self._build_stage_a_params(
    config=self._config,
    input_ctx=input_ctx
)
```

### How-To Map

```bash
# Create artifacts directory
mkdir -p plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/

# 1. Edit stage_a.py:100-114 (signature)
# 2. Edit stage_a.py:126+ (add unpacking code)
# 3. Edit stage_a.py:1803-1816 (call site)

# 4. Verify import succeeds
python -c "from dbex.refinement.context import StageAInputContext; print('StageAInputContext OK')" 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/import_check.log

# 5. Run context module tests
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_refinement_context.py -v 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/pytest_context.log \
  | tail -20

# 6. Stage A smoke test (collection only to verify no import errors)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_smoke --collect-only 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/pytest_stage_a_collect.log \
  | tail -10
```

---

## Commit Message Template

```
ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.1: Refactor _build_stage_a_params signature

Signature change from 13 positional parameters to single typed context:
- `_build_stage_a_params(self, config, input_ctx: StageAInputContext)`
- Call site in `run()` constructs StageAInputContext before calling
- Function body unpacks context for backwards compatibility

This reduces parameter count and enables typed validation.
No behavior changes; existing tests pass.

Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/

[Claude Code]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **DO** keep `config` as a separate parameter (it's already typed and commonly overridden)
2. **DO** add the import `from dbex.refinement.context import StageAInputContext` at both locations
3. **DO** unpack ALL 11 fields from input_ctx at the top of the function body
4. **DO NOT** change any logic in the function body — only add unpacking statements
5. **DO NOT** change the return type or return values
6. **DO NOT** change any other function signatures in this loop
7. **DO** use keyword arguments in the `StageAInputContext(...)` constructor
8. **DO** verify `inputs=refinement_inputs` (not `inputs=inputs`) at the call site

---

## If Blocked

If import errors occur:
1. Capture the full traceback
2. Check for circular import issues (context.py importing stage_a.py)
3. If circular, use local import inside the function (already suggested above)
4. Record in artifacts and return to supervisor

---

## Findings Applied (Mandatory)

- **ARCH-STAGE-CTX-001**: Context dataclasses must be located in `dbex/refinement/context.py` — using existing StageAInputContext
- **ARCH-STAGE-CTX-002**: Telemetry updates should use dataclass property assignment (future phase D)

---

## Pointers

- `dbex/refinement/context.py:1033-1071` — `StageAInputContext` dataclass definition
- `dbex/refinement/stage_a.py:100-114` — Current signature to refactor
- `dbex/refinement/stage_a.py:1803-1816` — Call site to update
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md` — Full plan phases

---

## Next Up

After Phase C.1 completion:
- C.2: Refactor `_build_stage_b_params` signature to use `StageBInputContext`
- C.3: Skip (Stage C already has clean signature)
- C.4: Update call sites in StageA.run, StageB.run
