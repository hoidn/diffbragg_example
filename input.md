# Ralph Input — Loop i=254

## Summary
Refactor `_build_stage_b_params` signature to use single `StageBInputContext` parameter instead of 16 positional args.

## Focus
ARCH-STAGE-CONTEXT-CONSOLIDATION — Stage Context Parameter Consolidation (Phase C.2)

## Branch
`integration`

## Mapped Tests
- `pytest tests/dbex/test_refinement_context.py -v` (verify context module import)
- `pytest tests/dbex/test_torch_refine_smoke.py --collect-only` (Stage smoke regression guard — collection only)

## Artifacts
`plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/`

---

## Do Now

**Focus Item:** ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.2
**Action Type:** Implementation (Signature Refactoring)

### Implement: `dbex/refinement/stage_b.py::_build_stage_b_params`

Refactor the signature from 16 positional parameters to a single typed context:

#### Step 1: Update the function signature (stage_b.py:93-111)

**FROM:**
```python
def _build_stage_b_params(
    self,
    device: torch.device,
    dtype: torch.dtype,
    stage_a_ctx: Optional[Dict[str, Any]],
    canonical_baseline: Dict[str, Any],
    n_panels: int,
    sampled_panel_ids: List[int],
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor],
    use_stage_a_roi_mode: bool,
    crystal,
    hkl_metadata: Dict[str, Any],
    hkl_grid: torch.Tensor,
    detector,
    beam,
    inputs,
    panel_slices: List[Tuple[slice, slice]],
    context: Optional[Any] = None,
) -> Dict[str, Any]:
```

**TO:**
```python
def _build_stage_b_params(
    self,
    config: 'RefinementConfig',
    input_ctx: 'StageBInputContext'
) -> Dict[str, Any]:
```

#### Step 2: Add import and unpack in function body

At the top of `_build_stage_b_params` (after the docstring, around line 145+), add:

```python
from dbex.refinement.context import StageBInputContext

# ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.2: Unpack input context
device = input_ctx.device
dtype = input_ctx.dtype
stage_a_ctx = input_ctx.stage_a_ctx
canonical_baseline = input_ctx.canonical_baseline
n_panels = input_ctx.n_panels
sampled_panel_ids = input_ctx.sampled_panel_ids
sigma_floor_sq_cache = input_ctx.sigma_floor_sq_cache
use_stage_a_roi_mode = input_ctx.use_stage_a_roi_mode
crystal = input_ctx.crystal
hkl_metadata = input_ctx.hkl_metadata
hkl_grid = input_ctx.hkl_grid
detector = input_ctx.detector
beam = input_ctx.beam
inputs = input_ctx.inputs
panel_slices = input_ctx.panel_slices
context = input_ctx.context
```

#### Step 3: Update the call site (stage_b.py:1383-1402)

**FROM:**
```python
param_values = self._build_stage_b_params(
    device=device,
    dtype=dtype,
    stage_a_ctx=stage_a_ctx,
    canonical_baseline=canonical_baseline,
    n_panels=n_panels,
    sampled_panel_ids=sampled_panel_ids,
    sigma_floor_sq_cache=sigma_floor_sq_cache,
    use_stage_a_roi_mode=use_stage_a_roi_mode,
    crystal=crystal,
    hkl_metadata=hkl_metadata,
    hkl_grid=hkl_grid,
    detector=detector,
    beam=beam,
    inputs=refinement_inputs,
    panel_slices=refinement_inputs.panel_slices,
    context=ctx,  # ARCH-REFINE-001 Phase B.3: Thread context for asu_map reuse
)
```

**TO:**
```python
# ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.2: Construct typed input context
from dbex.refinement.context import StageBInputContext
input_ctx = StageBInputContext(
    device=device,
    dtype=dtype,
    stage_a_ctx=stage_a_ctx,
    canonical_baseline=canonical_baseline,
    n_panels=n_panels,
    sampled_panel_ids=sampled_panel_ids,
    sigma_floor_sq_cache=sigma_floor_sq_cache,
    use_stage_a_roi_mode=use_stage_a_roi_mode,
    crystal=crystal,
    hkl_metadata=hkl_metadata,
    hkl_grid=hkl_grid,
    detector=detector,
    beam=beam,
    inputs=refinement_inputs,
    panel_slices=refinement_inputs.panel_slices,
    context=ctx,
)
param_values = self._build_stage_b_params(
    config=self._config,
    input_ctx=input_ctx
)
```

### How-To Map

```bash
# Create artifacts directory
mkdir -p plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/

# 1. Edit stage_b.py:93-111 (signature)
# 2. Edit stage_b.py:145+ (add unpacking code after docstring)
# 3. Edit stage_b.py:1383-1402 (call site)

# 4. Verify import succeeds
python -c "from dbex.refinement.context import StageBInputContext; print('StageBInputContext OK')" 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/import_check.log

# 5. Run context module tests
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_refinement_context.py -v 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/pytest_context.log \
  | tail -20

# 6. Stage smoke tests (collection only to verify no import errors)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py --collect-only 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/pytest_smoke_collect.log \
  | tail -10
```

---

## Commit Message Template

```
ARCH-STAGE-CONTEXT-CONSOLIDATION Phase C.2: Refactor _build_stage_b_params signature

Signature change from 16 positional parameters to single typed context:
- `_build_stage_b_params(self, config, input_ctx: StageBInputContext)`
- Call site in `run()` constructs StageBInputContext before calling
- Function body unpacks context for backwards compatibility

Follows same pattern as Phase C.1 (Stage A). This reduces parameter
count and enables typed validation.
No behavior changes; existing tests pass.

Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T070707Z/

[Claude Code]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **DO** keep `config` as a separate parameter (matching Phase C.1 pattern)
2. **DO** add the import `from dbex.refinement.context import StageBInputContext` at both locations
3. **DO** unpack ALL 16 fields from input_ctx at the top of the function body
4. **DO NOT** change any logic in the function body — only add unpacking statements
5. **DO NOT** change the return type or return values
6. **DO NOT** change any other function signatures in this loop
7. **DO** use keyword arguments in the `StageBInputContext(...)` constructor
8. **DO** preserve the comment `# ARCH-REFINE-001 Phase B.3: Thread context for asu_map reuse` (incorporated into input_ctx construction)
9. **DO** verify `inputs=refinement_inputs` (not `inputs=inputs`) at the call site
10. **DO** verify `panel_slices=refinement_inputs.panel_slices` at the call site

---

## If Blocked

If import errors occur:
1. Capture the full traceback
2. Check for circular import issues (context.py importing stage_b.py)
3. If circular, use local import inside the function (already suggested above)
4. Record in artifacts and return to supervisor

---

## Findings Applied (Mandatory)

- **ARCH-STAGE-CTX-001**: Context dataclasses must be located in `dbex/refinement/context.py` — using existing StageBInputContext
- **ARCH-STAGE-CTX-002**: Telemetry updates should use dataclass property assignment (future phase D)

---

## Pointers

- `dbex/refinement/context.py:1074-1121` — `StageBInputContext` dataclass definition
- `dbex/refinement/stage_b.py:93-111` — Current signature to refactor
- `dbex/refinement/stage_b.py:1383-1402` — Call site to update
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md` — Full plan phases
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T010000Z/summary.md` — Phase C.1 reference

---

## Next Up

After Phase C.2 completion:
- C.3: Skip (Stage C already has clean signature with `shared_context`)
- C.4: Update any remaining call sites in StageB.run
- Phase D: Eliminate dict mutations (telemetry updates)
- Phase E: Add enforcement test
