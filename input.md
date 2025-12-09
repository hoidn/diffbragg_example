# Ralph Input — Loop i=239

## Summary
Integrate upstream mosaic gradient fix (commit `1df032c2`) and verify DB-AT-010 gradcheck passes.

## Focus
ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (Phase B.10)

## Branch
`integration`

## Mapped Tests
`tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` (5 tests)

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T223000Z/`

---

## Do Now (Implementation)

**Focus Item:** ARCH-GRADIENT-FLOW-001 — Phase B.10

**Action Type:** Implementation + Verification

### Tasks

**B.10.1 — Verify upstream fix is available:**

```bash
# Check nanobrag_torch is at commit 1df032c2 or later
cd ~/Documents/nanoBragg && git log --oneline -5

# Verify the fix is in place (deterministic seeding)
grep -n "torch.Generator" src/nanobrag_torch/models/crystal.py | head -5
```

**B.10.2 — Update DBEX config factories to set mosaic_seed:**

The upstream response recommends setting `mosaic_seed` for reproducible gradcheck. Check if DBEX config_factories.py needs modification:

```python
# In dbex/config_factories.py, CrystalConfig construction should include:
# mosaic_seed=42  # or configurable via experiment metadata
```

If already handled (e.g., via passthrough), document the path. If not, add `mosaic_seed` parameter threading.

**B.10.3 — Run DB-AT-010 gradcheck verification:**

```bash
cd /home/ollie/Documents/diffbragg_example
mkdir -p plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T223000Z

# Run gradcheck tests with canonical flags
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck -v \
  2>&1 | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T223000Z/gradcheck_post_mosaic_fix.log
```

**Expected outcome:** 5/5 tests PASS (crystal_cell_a, crystal_cell_b, crystal_cell_c, detector_distance, beam_wavelength).

**B.10.4 — Document results:**

If PASS:
1. Update `docs/fix_plan.md` ARCH-GRADIENT-FLOW-001 entry to reflect "Phase B.10 complete"
2. Create `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T223000Z/summary.md` with test results

If FAIL:
1. Capture error signature in summary.md
2. Check if `mosaic_seed` is being passed correctly to CrystalConfig
3. Report blockers

---

## Environment

- nanobrag_torch source: `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`
- DBEX source: `/home/ollie/Documents/diffbragg_example`
- Required flags: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- Upstream fix commit: `1df032c2`

---

## Pitfalls To Avoid

1. **DO NOT** modify nanobrag_torch source — the fix is already applied upstream
2. **DO** ensure `NANOBRAGG_DISABLE_COMPILE=1` is set (torch.compile interferes with gradcheck)
3. **DO** use `KMP_DUPLICATE_LIB_OK=TRUE` to avoid Intel MKL conflicts
4. **DO NOT** run with `--smoke-detector-size` flag for gradcheck (use default)
5. **DO** check if `mosaic_seed` needs explicit threading through DBEX config
6. **DO NOT** add new probe scripts — verify with existing test infrastructure
7. **DO** archive the pytest log to the artifacts directory
8. **DO NOT** modify the gradcheck tolerances (eps=1e-6, atol=1e-5, rtol=0.05)

---

## If Blocked

If gradcheck still fails after upstream fix:

1. Capture the error signature (which parameter, ratio, expected vs actual)
2. Check if the test is using real experiment metadata that sets `mosaic_spread_deg > 0`
3. Verify `mosaic_seed` is being passed to CrystalConfig
4. If mosaic_seed not threaded, document as blocker and specify the required change
5. Update `galph_memory.md` with block rationale

---

## Findings Applied (Mandatory)

- **GRADIENT-003**: Mosaic code path confirmed as root cause (Phase B.9); upstream fix now available
  - Adherence: This verification tests the upstream fix integration
- **RUNTIME-001**: NANOBRAGG_DISABLE_COMPILE=1 required for gradcheck
  - Adherence: Included in test command
- **TESTING-003**: TEST_SUITE_INDEX.md update required when DB-AT-010 status changes
  - Adherence: Will update if tests pass (deferred to Phase B.4)

---

## Pointers

- `inbox/mosaic-gradient-fix-response-2025-12-08.md` — Upstream fix details
- `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md:56-84` — Phase B task definitions
- `tests/dbex/test_gradients.py` — DB-AT-010 test file
- `dbex/config_factories.py` — CrystalConfig construction (mosaic_seed threading)
- `docs/fix_plan.md:22-27` — ARCH-GRADIENT-FLOW-001 ledger entry

---

## Next Up (optional)

If Phase B.10 succeeds:
- **B.3** — Author enforcement test (`tests/architecture/test_gradient_contracts.py`)
- **B.4** — Documentation updates (findings.md, architecture.md, TEST_SUITE_INDEX.md)

If time permits after ARCH-GRADIENT-FLOW-001:
- **PERF-GPU-MEM-001 Phase C** — Test `pixel_batch_size=128` on 24GB GPU
