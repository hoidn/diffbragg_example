# Input — Loop i=207 (Ralph)

## Summary
Execute SPEC-INTERP-TRICUBIC-001 Phase C: Run DB-AT-010 gradcheck to verify cell parameter gradients flow with tricubic interpolation.

## Focus
SPEC-INTERP-TRICUBIC-001 — Global Tricubic Interpolation Default (Phase C: Validation)

## Branch
integration

## Mapped Tests
- `pytest -v tests -k DB_AT_010 --smoke-detector-size=full` — DB-AT-010 gradcheck suite (5 tests)

## Artifacts
`plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/`

---

## Context

**SPEC-INTERP-TRICUBIC-001 Phase B is COMPLETE.** Config default changed to `enable_hkl_interpolation=True`, enabling tricubic interpolation globally per spec-db-core.md.

**Prior evidence (Phase B validation):**
- Partiality tests: 2/2 PASS
- Stage A smoke: Tricubic working (99.79% HKL hit rate)
- Config change confirmed at `dbex/refinement/config.py:42`

**Expected outcome for Phase C:**
With tricubic interpolation enabled, cell parameter gradients should flow through the HKL lookup path. The previous DB-AT-010 failures were due to `torch.round()` in nearest-neighbor mode having zero gradient. Tricubic interpolation uses `polin3()` which has non-zero gradients w.r.t. query coordinates.

**Risk:** The upstream `nanobrag_torch` gradient magnitude issue (5000-127000x mismatch) may still cause test failures even though gradients are now flowing. If tests fail with non-zero but incorrect magnitude, document this and mark Phase C as partial success (graph connectivity achieved, magnitude correctness requires upstream fix).

---

## Do Now

**Execute: DB-AT-010 gradcheck validation**

### C1: Run DB-AT-010 gradcheck suite

```bash
cd /home/ollie/Documents/diffbragg_example

# Run DB-AT-010 full suite with canonical flags
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k DB_AT_010 --smoke-detector-size=full 2>&1 | tee plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/pytest_db_at_010.log
```

### C2: Analyze results

**If 5/5 PASS:**
- Document in summary.md: Cell parameter gradients now flow with tricubic interpolation
- Mark SPEC-INTERP-TRICUBIC-001 as done
- Update ARCH-GRADIENT-FLOW-001 status to unblocked

**If tests FAIL with GradcheckError (magnitude mismatch):**
- Check if analytical gradients are non-zero (indicates graph connectivity restored)
- If non-zero but wrong magnitude: Document partial success — tricubic enables gradient flow but upstream magnitude issue persists
- Update fix_plan.md accordingly

**If tests FAIL with disconnected graph error:**
- Document failure signature
- Tricubic interpolation may not be sufficient; investigate further

### C3: Update implementation.md Phase C checkboxes

Edit `plans/active/SPEC-INTERP-TRICUBIC-001/implementation.md`:
- [ ] C1: Run DB-AT-010 gradcheck → [x] (with result)
- [ ] C2: Stage A telemetry check → [DEFERRED] (OOM on full reconstruction)
- [ ] C3: Full DB-AT suite → [DEFERRED] (not required for this initiative)
- [ ] C4: Update TESTING_GUIDE.md → [x] if tests pass
- [ ] C5: Create INTERP-001 finding → [x] if tests pass

### C4: Author summary.md

Create `plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/summary.md` with:
- Test results (5/5 PASS or failure signature)
- Analysis of gradient flow status
- Next steps (close initiative or document blockers)

---

## How-To Map

### Run gradcheck tests
```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z

# Full DB-AT-010 suite
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k DB_AT_010 --smoke-detector-size=full 2>&1 | tee plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/pytest_db_at_010.log
```

### Inspect failure details if tests fail
```bash
# Extract failure message
grep -A 10 "GradcheckError\|FAILED" plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/pytest_db_at_010.log

# Check for non-zero analytical gradients (partial success indicator)
grep "analytical\|numerical\|Jacobian" plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T140000Z/pytest_db_at_010.log
```

---

## Pitfalls To Avoid

1. **DO NOT** skip the canonical environment flags (`KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`)
2. **DO NOT** interpret magnitude mismatch as total failure — if analytical gradients are non-zero, tricubic is working
3. **Environment Freeze:** No package installs
4. **DO NOT** modify nanobrag_torch — only DBEX files
5. **DO NOT** adjust gradcheck tolerances without explicit rationale

---

## If Blocked

If tests fail and block initiative closure:
1. Capture full pytest output in artifacts
2. Document failure signature in summary.md
3. Update SPEC-INTERP-TRICUBIC-001 to "partial" status with findings
4. Cross-reference ARCH-GRADIENT-FLOW-001 blocked_pending_upstream status

---

## Findings Applied

- **RUNTIME-001** (Runtime execution guardrails): Using canonical `NANOBRAGG_DISABLE_COMPILE=1` flag
- **GRADIENT-001** (Crystal overrides for gradient preservation): Tests use override pattern
- **TESTING-003** (Canonical selectors): Using documented DB-AT-010 selector

---

## Pointers

- SPEC-INTERP-TRICUBIC-001 implementation.md: `plans/active/SPEC-INTERP-TRICUBIC-001/implementation.md`
- Prior Phase B artifacts: `plans/active/SPEC-INTERP-TRICUBIC-001/reports/2025-12-08T130000Z/`
- ARCH-GRADIENT-FLOW-001 implementation.md: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md`
- DB-AT-010 test file: `tests/dbex/test_gradients.py`

---

## Next Up (optional)

If Phase C PASSES:
- Close SPEC-INTERP-TRICUBIC-001 (mark done in fix_plan.md)
- Update ARCH-GRADIENT-FLOW-001 status (advance to Phase B.2+)
- Update TEST_SUITE_INDEX.md with DB-AT-010 status change

If Phase C shows partial success (non-zero but incorrect magnitude):
- Document finding GRADIENT-003 in findings.md
- ARCH-GRADIENT-FLOW-001 remains blocked_pending_upstream
