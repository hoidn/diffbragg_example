# Ralph Input — Loop i=243

## Summary
Tier 4 focus: Scope SUPERVISOR initiative (agent meta-documentation) or run acceptance test verification now that OOM is resolved.

## Focus
SUPERVISOR — Supervisor Agent Documentation & Roadmap (Tier 4)

## Branch
`integration`

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py` — Stage A/B/C smoke suite (verify OOM fix holds)
- `tests/architecture/test_nanobrag_partiality.py` — Physics parity validation

## Artifacts
`plans/active/SUPERVISOR/reports/2025-12-09T020000Z/`

---

## Do Now (Debug + Verification)

**Focus Item:** SUPERVISOR — Tier 4 Scoping + Portfolio Verification

**Action Type:** Debug (verify OOM fix) + Planning (Tier 4 scoping)

### Background

Portfolio status as of Loop i=242:
- **PERF-GPU-MEM-001:** DONE — `pixel_batch_size=32` threading complete
- **ARCH-GRADIENT-FLOW-001:** DONE — 6/6 gradcheck tests PASS
- **DB-AT-SUITE-CARE-001:** DONE — D.1-D.4 complete
- **Tier 0-3:** All blocked or done
- **Tier 4:** Multiple pending (SUPERVISOR, HARDEN-SUBMODULE-ROBUSTNESS, ORCH-* items)

### Tasks

**V.1 — Verify Stage A/B/C smoke suite passes with OOM fix:**

```bash
mkdir -p plans/active/SUPERVISOR/reports/2025-12-09T020000Z

# Run Stage A smoke with pixel batching (already wired in test)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  --smoke-detector-size=small -v \
  2>&1 | tee plans/active/SUPERVISOR/reports/2025-12-09T020000Z/stage_a_smoke.log
```

If Stage A passes, run additional smokes:

```bash
# Stage B smoke (if exists and is mapped)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest tests/dbex/test_torch_refine_smoke.py -k "stage_b" --smoke-detector-size=small -v \
  2>&1 | tee plans/active/SUPERVISOR/reports/2025-12-09T020000Z/stage_b_smoke.log

# Partiality parity (physics validation)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest tests/architecture/test_nanobrag_partiality.py -v \
  2>&1 | tee plans/active/SUPERVISOR/reports/2025-12-09T020000Z/partiality.log
```

**V.2 — Document portfolio health:**

Create `plans/active/SUPERVISOR/reports/2025-12-09T020000Z/portfolio_health.md` with:
1. Tier 0-4 status summary
2. Test pass/fail counts
3. Blockers and their dependencies
4. Next actionable items

**V.3 — SUPERVISOR initiative scoping (if time permits):**

Review `plans/active/SUPERVISOR/` directory (if exists) or create scoping document:
- What documentation needs updating?
- What agent roadmap items are outstanding?
- Exit criteria for SUPERVISOR initiative

---

## Environment

- nanobrag_torch source: `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`
- DBEX source: `/home/ollie/Documents/diffbragg_example`
- Required flags: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- GPU: 24GB (OOM fix validated with pixel_batch_size=32)

---

## Pitfalls To Avoid

1. **DO** use `KMP_DUPLICATE_LIB_OK=TRUE` to avoid Intel MKL conflicts
2. **DO** archive all pytest logs to the artifacts directory
3. **DO NOT** make production code changes — this is verification + scoping only
4. **DO** document any failures clearly with error signatures
5. **DO** update `galph_memory.md` with verification results

---

## If Blocked

If smoke tests fail:
1. Capture the full error output
2. Determine if it's OOM-related or a different issue
3. Document in artifacts and report to supervisor

---

## Findings Applied (Mandatory)

- **RUNTIME-001**: NANOBRAGG_DISABLE_COMPILE=1 required for stable GPU execution
  - Adherence: Included in test commands
- **GRADIENT-004**: Use MSE loss path for gradcheck validation
  - Adherence: Test fixtures already configured per ARCH-GRADIENT-FLOW-001

---

## Pointers

- `docs/fix_plan.md:117-123` — Tier 4 initiatives
- `plans/active/PERF-GPU-MEM-001/reports/2025-12-09T000000Z/summary.md` — OOM fix validation
- `galph_memory.md:1-15` — Loop i=242 portfolio cleanup

---

## Next Up (optional)

If all verification passes:
- Proceed with SUPERVISOR scoping or ORCH-ROBUST-001 scoping
- Consider running full detector smoke if memory allows

If verification blocked:
- Document failures and return to supervisor for triage
