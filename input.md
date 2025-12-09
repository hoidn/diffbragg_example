# Ralph Input — Loop i=252

## Summary
Begin ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.1: Create `StageAInputContext` dataclass in `dbex/refinement/context.py`.

## Focus
ARCH-STAGE-CONTEXT-CONSOLIDATION — Stage Context Parameter Consolidation

## Branch
`integration`

## Mapped Tests
- `pytest tests/dbex/test_refinement_context.py -v` (verify module import)
- `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_smoke_small -v --smoke-detector-size=small` (regression guard)

## Artifacts
`plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/`

---

## Do Now

**Focus Item:** ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.1
**Action Type:** Implementation (Dataclass Addition)

### Implement: `dbex/refinement/context.py::StageAInputContext`

Add a new dataclass `StageAInputContext` to consolidate the 13 positional parameters of `_build_stage_a_params`:

1. Open `dbex/refinement/context.py`
2. Add the following dataclass after `StageCContext` (around line 1000):

```python
@dataclass
class StageAInputContext:
    """
    Input parameters for Stage A LBFGS parameter building.

    Consolidates the 13 positional parameters of _build_stage_a_params into
    a single typed context per ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.

    This dataclass contains the inputs needed to BUILD Stage A parameters,
    distinct from StageAContext which contains the OUTPUTS (cached models, simulators).

    Fields sourced from _build_stage_a_params signature:
        crystal: DIALS crystal object
        detector: DIALS detector object
        beam: DIALS beam object
        inputs: DataLoad instance with target data and masks
        baseline_crystal: Reference crystal for parameter initialization
        baseline_detector: Reference detector for parameter initialization
        hkl_grid: Structure factor grid tensor [n_h, n_k, n_l]
        hkl_metadata: Dict with grid dimensions, halo status, etc.
        sigma_floor_sq_cache: Device-keyed cache for sigma_floor² tensors
        device: Target torch device
        dtype: Target torch dtype
    """
    crystal: Any
    detector: Any
    beam: Any
    inputs: Any
    baseline_crystal: Any
    baseline_detector: Any
    hkl_grid: torch.Tensor
    hkl_metadata: Dict[str, Any]
    sigma_floor_sq_cache: Dict[torch.device, torch.Tensor]
    device: torch.device
    dtype: torch.dtype
```

3. Ensure `torch` and `Any` are imported at the module level (should already be present)

### How-To Map

```bash
# Create artifacts directory
mkdir -p plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/

# 1. Edit context.py to add StageAInputContext
# (manual edit — add after StageCContext class)

# 2. Verify import succeeds
python -c "from dbex.refinement.context import StageAInputContext; print('StageAInputContext OK')" 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/import_check.log

# 3. Run context module tests (if any)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_refinement_context.py -v 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/pytest_context.log \
  | tail -20

# 4. Regression guard — ensure Stage A smoke still works
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_smoke_small -v --smoke-detector-size=small 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/pytest_stage_a_smoke.log \
  | tail -30
```

---

## Commit Message Template

```
ARCH-STAGE-CONTEXT-CONSOLIDATION Phase B.1: Add StageAInputContext dataclass

New dataclass in dbex/refinement/context.py consolidates the 13 parameters
of _build_stage_a_params into a typed container. This is prep work for
signature refactoring in Phase C.

- Fields mirror current _build_stage_a_params parameters
- No behavior changes; dataclass is not yet consumed
- Regression guard: Stage A smoke PASSED

Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/

[Claude Code]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **DO** use `from typing import Any` — DIALS objects don't have typed annotations
2. **DO** place the new dataclass near existing context classes (after StageCContext, around line 1000)
3. **DO NOT** change any existing code in `_build_stage_a_params` yet — only add the dataclass
4. **DO NOT** add new imports if they already exist (check first)
5. **DO** apply the `@dataclass` decorator
6. **DO** ensure `torch.Tensor` type hint works (torch should already be imported)
7. **DO NOT** add default values for required fields (crystal, detector, etc.)

---

## If Blocked

If import errors occur:
1. Capture the full traceback
2. Check for circular imports between `context.py` and `stage_a.py`
3. Record in artifacts and return to supervisor

---

## Findings Applied (Mandatory)

- **ARCH-STAGE-CTX-001**: Context dataclasses must be located in `dbex/refinement/context.py`
- **ARCH-STAGE-CTX-002**: Telemetry updates should use dataclass property assignment (future phase)

---

## Pointers

- `dbex/refinement/context.py:904-960` — Existing `StageAContext` pattern to follow
- `dbex/refinement/stage_a.py:100-114` — Current `_build_stage_a_params` signature (source of fields)
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md` — Full plan phases
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T230500Z/signature_analysis.md` — Parameter analysis

---

## Next Up

After Phase B.1 completion:
- B.2: Add `StageBInputContext` dataclass
- B.3: Add `StageCInputContext` dataclass (if needed)
- C.1: Refactor `_build_stage_a_params` signature to use `StageAInputContext`
