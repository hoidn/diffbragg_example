# Acceptance Suite Regression Monitoring Cadence

## Purpose

Detect acceptance test regressions in the DB-AT suite, including:
- Gradcheck failures (loss/gradient correctness)
- Bbox/mask semantic drift
- Data ingestion/transformation contract violations
- Determinism regressions

## Frequency

- **Primary:** Monthly (1st week of each month)
- **On-demand:** After significant refactors, merge from upstream, or ARCH-level changes

## Scope

### Active Test Selectors

| Selector | Test Count | Description |
|----------|------------|-------------|
| DB-AT-002 | 2 | Forward determinism (same/diff seed) |
| DB-AT-020 | 2 | Reflection ingestion (bbox, panel alignment) |
| DB-AT-021 | 3 | Mask semantics (polarity, loss mask, precedence) |
| DB-AT-022 | 3 | Background semantics (sentinel, guard, ROI coverage) |
| DB-AT-023 | 4 | Calibration policy (photon conversion, ADU mode, guards, consistency) |
| DB-AT-024 | 1 | Mapping consistency (requires DBAT024_ARTIFACT_DIR) |

### Blocked/Pending Selectors

| Selector | Status | Blocker |
|----------|--------|---------|
| DB-AT-010 | blocked_pending_upstream | ARCH-GRADIENT-FLOW-001 (Jacobian mismatch in nanobrag_torch) |

## Canonical Command

```bash
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Full regression sweep (14 tests expected PASS + DB-AT-024 skip if artifact dir unset)
pytest -v tests --smoke-detector-size=full \
    -k "DB_AT_002 or DB_AT_020 or DB_AT_021 or DB_AT_022 or DB_AT_023 or DB_AT_024" \
    2>&1 | tee reports/<YYYY-MM-DD>/regression_sweeps/sweep_<YYYY_MM_DD>.log
```

### Environment Flags

| Flag | Purpose |
|------|---------|
| `KMP_DUPLICATE_LIB_OK=TRUE` | Prevents Intel MKL conflicts with multiple OpenMP runtimes |
| `NANOBRAGG_DISABLE_COMPILE=1` | Uses precompiled nanobrag_torch kernels |
| `--smoke-detector-size=full` | Required per docs/spec-db-workflow.md (Stage Smoke Dataset Policy) |

### Optional: DB-AT-024 Artifact Dir

To enable DB-AT-024 mapping consistency test:
```bash
export DBAT024_ARTIFACT_DIR=/path/to/artifact/output
```

## Artifact Location

```
plans/active/DB-AT-SUITE-CARE-001/reports/<ISO8601-timestamp>/regression_sweeps/
    sweep_<YYYY_MM_DD>.log
```

## Pass Criteria

| Outcome | Action |
|---------|--------|
| All tests PASS | Green — no action needed |
| Expected skip (DB-AT-024 artifact dir) | Green — documented expected behavior |
| Expected xfail (documented) | Green — check xfail reason still valid |
| Unexpected FAIL | Red — create bug report, escalate |
| New ERROR | Red — investigate test infrastructure issue |

## Failure Protocol

1. **Document failure signature** — capture pytest output, stack trace, assertion message
2. **Check known blockers** — compare against `docs/fix_plan.md` and `problems.md`
3. **Create bug report** — if new regression:
   - Add entry to `problems.md` with selector, file:line, and error signature
   - Link to relevant plan if applicable
   - Set priority based on severity (gradcheck fail = P0, semantic drift = P1)
4. **Escalate** — if blocker for active work, tag supervisor in next loop input

## Baseline

Established 2025-12-07:
- **Result:** 14 PASSED, 1 SKIPPED
- **Skip reason:** DB-AT-024 `DBAT024_ARTIFACT_DIR` not set (expected)
- **Log:** `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T213000Z/regression_sweeps/sweep_2025_12_07.log`

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2025-12-07 | Ralph (Loop i=172) | Initial cadence document (Phase D.1) |
