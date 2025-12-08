# Input — Loop i=206 (Ralph)

## Summary
Implement SPEC-INTERP-TRICUBIC-001 Phase B: Wire `interpolation=True` as the canonical default per updated specs.

## Focus
SPEC-INTERP-TRICUBIC-001 — Global Tricubic Interpolation Default (Phase B: Implementation)

## Branch
integration

## Mapped Tests
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_convergence --smoke-detector-size=small` — Verify Stage A still converges with tricubic
- `pytest -v tests/architecture/test_nanobrag_partiality.py` — Partiality tests (2 tests, expect PASS)

## Artifacts
`plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/`

---

## Context

**SPEC-INTERP-TRICUBIC-001 Phase A is COMPLETE.** The specs have been updated:
- `docs/spec-db-core.md:98-102` — All stages SHALL use tricubic (`interpolation=True`) with ±1 halo
- `docs/spec-db-workflow.md:52-59` — All stages: `interpolation=True` REQUIRED
- `docs/spec-db-conformance.md` — DB-AT-025 updated to require tricubic for all stages

**Root cause of cell gradient failures (ARCH-GRADIENT-FLOW-001):**
Stage A was using nearest-neighbor HKL lookup (`interpolation=False`), which uses `torch.round()` — zero gradient by construction. Cell parameter gradients require tricubic interpolation to flow through query coordinates.

**Implementation needed:** Change the default from `False` to `True` and update any tests that explicitly set `False` for legacy parity testing.

---

## Do Now

**Implement: `dbex/refinement/config.py::RefinementConfig.enable_hkl_interpolation`**

### B1: Change default to `True`

Edit `dbex/refinement/config.py:40`:
```python
# OLD:
enable_hkl_interpolation: bool = False

# NEW:
enable_hkl_interpolation: bool = True
```

### B2: Update test files that hard-code `False`

Search for tests with `enable_hkl_interpolation=False` and update them:

1. `tests/dbex/test_stage_a_smoke_parity.py:266` — This test explicitly sets `False` for DB-AT-028/029 legacy parity. **UPDATE**: Add a comment noting this is legacy mode for parity testing, not canonical behavior:
   ```python
   enable_hkl_interpolation=False,  # Legacy: nearest-neighbor for DiffBragg parity (non-canonical)
   ```

2. `tests/dbex/test_stage_a_smoke_parity.py:745` — Same pattern, add legacy comment.

3. `tests/dbex/test_stage_a_smoke_parity.py:201` — Docstring mentions nearest-neighbor. **UPDATE** docstring to note this is legacy mode.

### B3: Run validation tests

```bash
# Verify Stage A still works with tricubic
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_convergence --smoke-detector-size=small

# Verify partiality tests pass
pytest -v tests/architecture/test_nanobrag_partiality.py
```

### B4: Archive artifacts

Create `plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/summary.md` with:
- Config change applied
- Test results
- Any issues encountered

---

## How-To Map

### Change config default
```bash
# The edit is at line 40 of config.py
# Change: enable_hkl_interpolation: bool = False
# To: enable_hkl_interpolation: bool = True
```

### Run tests
```bash
cd /home/ollie/Documents/diffbragg_example

# Stage A smoke (should pass with new default)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_convergence --smoke-detector-size=small 2>&1 | tee plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/pytest_stage_a.log

# Partiality tests
pytest -v tests/architecture/test_nanobrag_partiality.py 2>&1 | tee plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/pytest_partiality.log
```

---

## Pitfalls To Avoid

1. **DO NOT** change the Stage B halo requirement — Stage B still requires `has_halo=True` in hkl_metadata
2. **DO NOT** remove explicit `False` settings in legacy parity tests — just add clarifying comments
3. **Environment Freeze:** No package installs
4. **DO NOT** modify nanobrag_torch — only DBEX config and tests
5. **Device/dtype neutrality:** The change is config-only, no tensor operations affected

---

## If Blocked

If Stage A smoke test fails with tricubic:
1. Capture full error in artifacts
2. Check if HKL grid has halo (`hkl_metadata["has_halo"]`)
3. Document in summary.md and mark Phase B blocked

---

## Findings Applied

- **GRADIENT-001** (Crystal overrides for gradient preservation): Phase B maintains override pattern compatibility
- **REFINE-005** (Stage B interpolation requirement): Stage B already requires tricubic; this aligns Stage A
- **TESTING-003** (Canonical selectors): Using documented selectors from TESTING_GUIDE.md

---

## Pointers

- SPEC-INTERP-TRICUBIC-001 implementation.md: `plans/active/SPEC-INTERP-TRICUBIC-001/implementation.md`
- Config file: `dbex/refinement/config.py:40`
- Spec reference: `docs/spec-db-core.md:98-102`
- Related initiative: ARCH-GRADIENT-FLOW-001 (cell gradient enablement — unblocked by this work)

---

## Next Up (optional)

After Phase B completes:
- Phase C: Run DB-AT-010 gradcheck to verify cell parameter gradients now flow
- Update ARCH-GRADIENT-FLOW-001 status from blocked_pending_upstream to in_progress
