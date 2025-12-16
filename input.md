# Ralph Input — Loop i=255

## Summary
Create enforcement test for Stage context dataclasses to validate required fields and signature contracts.

## Focus
ARCH-STAGE-CONTEXT-CONSOLIDATION — Stage Context Parameter Consolidation (Phase E)

## Branch
`integration`

## Mapped Tests
- `pytest tests/architecture/test_stage_context_contracts.py -v` (NEW — create and run)
- `pytest tests/dbex/test_refinement_context.py -v` (regression guard — 6 tests)

## Artifacts
`plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T080000Z/`

---

## Do Now

**Focus Item:** ARCH-STAGE-CONTEXT-CONSOLIDATION Phase E
**Action Type:** Implementation (Enforcement Test)

### Implement: `tests/architecture/test_stage_context_contracts.py`

Create an enforcement test that validates:
1. **E.1** Context dataclasses have required fields
2. **E.2** Stage helper signatures use typed context parameters
3. **E.3** No telemetry dict mutations in stage modules

#### Test File Structure

```python
"""Stage context contracts enforcement test.

ARCH-STAGE-CONTEXT-CONSOLIDATION Exit Criterion 3: Validates that Stage A/B/C
helper signatures use typed context parameters and that telemetry updates flow
through typed dataclasses, not dict mutations.

Cross-reference: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md
Cross-reference: dbex/refinement/context.py (StageAInputContext, StageBInputContext)

Architecture Context:
- Stage A uses StageAInputContext for _build_stage_a_params
- Stage B uses StageBInputContext for _build_stage_b_params
- Stage C uses RefinementSharedContext for _build_stage_c_params (already clean)
- No telemetry dict mutations allowed in stage modules

Maintenance:
- Update EXPECTED_CONTEXT_FIELDS if context dataclasses change
- Run: pytest -vv tests/architecture/test_stage_context_contracts.py
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Set, Dict

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent


class TestStageContextFields:
    """E.1: Validate context dataclasses have required fields."""

    def test_stage_a_input_context_has_required_fields(self):
        """StageAInputContext must have all 13 fields from original signature."""
        from dbex.refinement.context import StageAInputContext

        required_fields = {
            'input_data', 'crystal', 'hkl_grid', 'detector', 'beam',
            'n_panels', 'sampled_panel_ids', 'panel_slices', 'sim_factory',
            'hkl_metadata', 'sigma_floor_sq_cache', 'device', 'dtype'
        }

        # Get dataclass fields
        import dataclasses
        actual_fields = {f.name for f in dataclasses.fields(StageAInputContext)}

        missing = required_fields - actual_fields
        assert not missing, f"StageAInputContext missing required fields: {missing}"

    def test_stage_b_input_context_has_required_fields(self):
        """StageBInputContext must have all 16 fields from original signature."""
        from dbex.refinement.context import StageBInputContext

        required_fields = {
            'device', 'dtype', 'stage_a_ctx', 'canonical_baseline',
            'n_panels', 'sampled_panel_ids', 'sigma_floor_sq_cache',
            'use_stage_a_roi_mode', 'crystal', 'hkl_metadata', 'hkl_grid',
            'detector', 'beam', 'inputs', 'panel_slices', 'context'
        }

        import dataclasses
        actual_fields = {f.name for f in dataclasses.fields(StageBInputContext)}

        missing = required_fields - actual_fields
        assert not missing, f"StageBInputContext missing required fields: {missing}"


class TestStageHelperSignatures:
    """E.2: Validate stage helper signatures use typed context parameters."""

    def test_stage_a_build_params_uses_typed_context(self):
        """_build_stage_a_params must accept (self, config, input_ctx) only."""
        from dbex.refinement.stage_a import StageA

        sig = inspect.signature(StageA._build_stage_a_params)
        params = list(sig.parameters.keys())

        # Should have exactly 3 parameters: self, config, input_ctx
        assert len(params) == 3, f"Expected 3 params (self, config, input_ctx), got {len(params)}: {params}"
        assert params[0] == 'self'
        assert params[1] == 'config'
        assert params[2] == 'input_ctx'

    def test_stage_b_build_params_uses_typed_context(self):
        """_build_stage_b_params must accept (self, config, input_ctx) only."""
        from dbex.refinement.stage_b import StageB

        sig = inspect.signature(StageB._build_stage_b_params)
        params = list(sig.parameters.keys())

        # Should have exactly 3 parameters: self, config, input_ctx
        assert len(params) == 3, f"Expected 3 params (self, config, input_ctx), got {len(params)}: {params}"
        assert params[0] == 'self'
        assert params[1] == 'config'
        assert params[2] == 'input_ctx'

    def test_stage_c_build_params_uses_shared_context(self):
        """_build_stage_c_params must use shared_context as first param after self."""
        from dbex.refinement.stage_c import StageC

        sig = inspect.signature(StageC._build_stage_c_params)
        params = list(sig.parameters.keys())

        # Stage C has 5 params: self, shared_context, stage_a_ctx, stage_a_telemetry, sampled_panel_ids
        assert len(params) <= 5, f"Expected ≤5 params, got {len(params)}: {params}"
        assert params[0] == 'self'
        assert params[1] == 'shared_context'


class TestNoTelemetryDictMutations:
    """E.3: Validate no telemetry dict mutations in stage modules."""

    # Pattern to detect dict item assignment: var['key'] = value
    DICT_MUTATION_PATTERN = re.compile(r"telemetry\[['\"].*['\"]\]\s*=(?!=)")

    @pytest.mark.parametrize("stage_file", [
        "dbex/refinement/stage_a.py",
        "dbex/refinement/stage_b.py",
        "dbex/refinement/stage_c.py",
    ])
    def test_no_telemetry_dict_mutations(self, stage_file: str):
        """Stage modules must not have telemetry['key'] = value patterns."""
        file_path = REPO_ROOT / stage_file
        if not file_path.exists():
            pytest.skip(f"File not found: {stage_file}")

        content = file_path.read_text()
        matches = self.DICT_MUTATION_PATTERN.findall(content)

        assert not matches, (
            f"{stage_file} contains telemetry dict mutations. "
            f"Use typed dataclass setters instead.\n"
            f"Found patterns: {matches[:5]}"  # Show first 5 for brevity
        )
```

### How-To Map

```bash
# Create artifacts directory
mkdir -p plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T080000Z/

# 1. Create the test file
# Use Write tool to create tests/architecture/test_stage_context_contracts.py

# 2. Run the new enforcement test
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/architecture/test_stage_context_contracts.py -v 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T080000Z/pytest_contracts.log \
  | tail -30

# 3. Run context module tests (regression guard)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_refinement_context.py -v 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T080000Z/pytest_context.log \
  | tail -15

# 4. Verify total test count (enforcement + context = 6 + 6 = ~12 tests)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/architecture/test_stage_context_contracts.py tests/dbex/test_refinement_context.py --collect-only 2>&1 \
  | tee plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T080000Z/pytest_collect.log \
  | tail -10
```

---

## Commit Message Template

```
ARCH-STAGE-CONTEXT-CONSOLIDATION Phase E: Add enforcement test

Create tests/architecture/test_stage_context_contracts.py with 3 test classes:
- TestStageContextFields: validates StageAInputContext (13 fields), StageBInputContext (16 fields)
- TestStageHelperSignatures: validates _build_stage_*_params use typed context
- TestNoTelemetryDictMutations: scans stage modules for dict mutation patterns

Exit Criterion 3 satisfied: enforcement test validates context immutability guarantees.

Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-09T080000Z/

[Claude Code]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **DO** use `inspect.signature()` to validate function signatures
2. **DO** use `dataclasses.fields()` to extract dataclass field names
3. **DO** use regex pattern matching for dict mutation detection
4. **DO NOT** import torch or GPU-dependent modules in the test (CPU-only introspection)
5. **DO NOT** actually run Stage A/B/C — only inspect signatures and source code
6. **DO** follow the pattern from `test_telemetry_surfaces.py` for architecture tests
7. **DO** include docstrings with cross-references to the implementation plan
8. **DO NOT** add more than 150 LOC for this test file
9. **DO** use `pytest.mark.parametrize` for the dict mutation scan (3 files)
10. **DO** name the test file `test_stage_context_contracts.py` (not `test_context_contracts.py`)

---

## If Blocked

If import errors occur:
1. Capture the full traceback
2. Check if StageAInputContext/StageBInputContext are correctly exported from context.py
3. If imports fail, add conditional pytest.skip() for missing classes
4. Record in artifacts and return to supervisor

---

## Findings Applied (Mandatory)

- **ARCH-STAGE-CTX-001**: Context dataclasses must be located in `dbex/refinement/context.py` — test validates field presence
- **ARCH-STAGE-CTX-002**: Telemetry updates should use dataclass property assignment — test scans for violations

---

## Pointers

- `tests/architecture/test_telemetry_surfaces.py` — Pattern reference for architecture tests
- `dbex/refinement/context.py:1033-1121` — StageAInputContext and StageBInputContext definitions
- `dbex/refinement/stage_a.py:100-104` — Stage A signature to validate
- `dbex/refinement/stage_b.py:93-97` — Stage B signature to validate
- `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md` — Full plan phases

---

## Next Up

After Phase E completion:
- Mark ARCH-STAGE-CONTEXT-CONSOLIDATION as **done** in fix_plan.md
- Update implementation.md checkboxes
- Author closure summary.md
- Consider archive timing (low urgency — tech debt cleanup)
