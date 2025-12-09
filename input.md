# Ralph Input — Loop i=252

## Summary
Continue ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.2: Create `StageBInputContext` dataclass in `dbex/refinement/context.py`.

## Focus
ARCH-STAGE-CONTEXT-CONSOLIDATION — Stage Context Parameter Consolidation

## Branch
`integration`

## Mapped Tests
- `pytest tests/dbex/test_refinement_context.py -v` (verify module import)
- `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers -v --smoke-detector-size=small` (regression guard)

## Artifacts
`plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T000000Z/`

---

## Do Now

**Focus Item:** ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.2
**Action Type:** Implementation (Dataclass Addition)

### Implement: `dbex/refinement/context.py::StageBInputContext`

Add a new dataclass `StageBInputContext` to consolidate the 16 positional parameters of `_build_stage_b_params` (see `stage_b.py:93-111`):

1. Open `dbex/refinement/context.py`
2. Add the following dataclass **after** `StageAInputContext` (around line 1072):

```python
@dataclass
class StageBInputContext:
    """
    Input parameters for Stage B shell modifier parameter building.

    Consolidates the 16 positional parameters of _build_stage_b_params into
    a single typed context per ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.

    This dataclass contains the inputs needed to BUILD Stage B parameters,
    distinct from StageBContext which contains the OUTPUTS (shell modifiers, telemetry).

    Fields sourced from _build_stage_b_params signature (stage_b.py:93-111):
        device: Target torch device
        dtype: Target torch dtype
        stage_a_ctx: Optional Stage A context dict or StageAContext
        canonical_baseline: Baseline calibration dictionary
        n_panels: Number of detector panels
        sampled_panel_ids: List of panel IDs being processed
        sigma_floor_sq_cache: Device-keyed cache for sigma_floor² tensors
        use_stage_a_roi_mode: Whether to use ROI mode from Stage A
        crystal: DIALS crystal object
        hkl_metadata: Dict with grid dimensions, halo status, etc.
        hkl_grid: Structure factor grid tensor [n_h, n_k, n_l]
        detector: DIALS detector object
        beam: DIALS beam object
        inputs: DataLoad instance with target data and masks
        panel_slices: List of (row_slice, col_slice) tuples for panel extraction
        context: Optional RefinementContext with pre-computed maps

    IDL Contract Reference:
        docs/architecture/dbex/refinement/context.idl.md
        ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.2
    """
    device: torch.device
    dtype: torch.dtype
    stage_a_ctx: Optional[Dict[str, Any]]
    canonical_baseline: Dict[str, Any]
    n_panels: int
    sampled_panel_ids: List[int]
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor]
    use_stage_a_roi_mode: bool
    crystal: Any
    hkl_metadata: Dict[str, Any]
    hkl_grid: torch.Tensor
    detector: Any
    beam: Any
    inputs: Any
    panel_slices: List[Tuple[slice, slice]]
    context: Optional[Any] = None
```

3. Ensure required imports exist at module level:
   - `from typing import Optional, List, Tuple` (verify these are imported)

### How-To Map

```bash
# Create artifacts directory
mkdir -p plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T000000Z/

# 1. Edit context.py to add StageBInputContext after StageAInputContext

# 2. Verify import succeeds
python -c "from dbex.refinement.context import StageBInputContext; print('StageBInputContext OK')" 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T000000Z/import_check.log

# 3. Run context module tests
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_refinement_context.py -v 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T000000Z/pytest_context.log \
  | tail -20

# 4. Regression guard — ensure Stage B shell modifiers test collects
# NOTE: Full execution may OOM on small GPU; collection-only is acceptable
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --collect-only 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T000000Z/pytest_stage_b_collect.log \
  | tail -10
```

---

## Commit Message Template

```
ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.2: Add StageBInputContext dataclass

New dataclass in dbex/refinement/context.py consolidates the 16 parameters
of _build_stage_b_params into a typed container. This continues prep work
for signature refactoring in Phase C.

- Fields mirror current _build_stage_b_params parameters
- No behavior changes; dataclass is not yet consumed
- Regression guard: context tests PASSED, Stage B collects

Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T000000Z/

[Claude Code]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **DO** place the new dataclass immediately after `StageAInputContext` (around line 1072)
2. **DO** include `Optional` in type hints for `stage_a_ctx` and `context` fields
3. **DO** use `List[Tuple[slice, slice]]` for panel_slices (verify import of `Tuple` and `slice`)
4. **DO NOT** change any existing code in `_build_stage_b_params` yet — only add the dataclass
5. **DO NOT** add default values except for `context: Optional[Any] = None` (matches original signature)
6. **DO** apply the `@dataclass` decorator
7. **DO** verify `Optional`, `List`, `Tuple` are imported from `typing`

---

## If Blocked

If import errors occur:
1. Capture the full traceback
2. Check for missing typing imports (Optional, List, Tuple)
3. Verify slice is a builtin (no import needed)
4. Record in artifacts and return to supervisor

---

## Findings Applied (Mandatory)

- **ARCH-STAGE-CTX-001**: Context dataclasses must be located in `dbex/refinement/context.py`
- **ARCH-STAGE-CTX-002**: Telemetry updates should use dataclass property assignment (future phase)

---

## Pointers

- `dbex/refinement/context.py:1032-1071` — Existing `StageAInputContext` pattern to follow
- `dbex/refinement/stage_b.py:93-111` — Current `_build_stage_b_params` signature (source of fields)
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md` — Full plan phases
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T230500Z/signature_analysis.md` — Parameter analysis

---

## Next Up

After Phase B.2 completion:
- B.3: Add `StageCInputContext` dataclass (if needed — verify Stage C params first)
- C.1: Refactor `_build_stage_a_params` signature to use `StageAInputContext`
