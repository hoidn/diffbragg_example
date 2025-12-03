# Process Noise Audit — ARCH-LAZY-IMPORTS-001 Phase C

**Date**: 2025-12-05T000500Z
**Scope**: 8 modules (geometry/physics/Stage helpers and wrappers)
**Initiative**: ARCH-LAZY-IMPORTS-001 (architecture)
**Mode**: Docs

---

## Summary

Completed sweep of 8 target modules to replace historical ticket/process references with normative spec/finding citations per ARCH-LAZY-IMPORTS-001 Phase C requirements.

**Result**: Clean — all 8 scoped modules now free of low-value process noise.

---

## Modules Scanned

1. `dbex/geometry/crystallography.py`
2. `dbex/physics/forward.py`
3. `dbex/physics/loss.py`
4. `dbex/refinement/stage_a_utils.py`
5. `dbex/refinement/hkl_utils.py`
6. `dbex/refinement/stage_a.py`
7. `dbex/refinement/stage_b.py`
8. `dbex/refinement/stage_c.py`

---

## Audit Results

### Pre-Cleanup (Raw Audit)

Command:
```bash
rg -n "TODO|FIXME|JIRA|Issue #|ticket|meeting notes|sprint" \
  dbex/geometry/crystallography.py \
  dbex/physics/forward.py \
  dbex/physics/loss.py \
  dbex/refinement/stage_a_utils.py \
  dbex/refinement/hkl_utils.py \
  dbex/refinement/stage_a.py \
  dbex/refinement/stage_b.py \
  dbex/refinement/stage_c.py
```

**Hits**: 1 instance

- `dbex/refinement/stage_a.py:1308` — "TODO‑PHYSICS" reference in loss variance comment

### Post-Cleanup Verification

Command:
```bash
rg -n "TODO|FIXME|JIRA|Issue #|ticket" dbex/{geometry,physics,refinement}/*.py
```

**Hits**: 1 instance (out-of-scope module)

- `dbex/refinement/helpers.py:365` — "TODO: Implement Bragg stitching logic"
  **Status**: Not in the scoped 8-module list for this Phase C loop; flagged for future triage under a separate initiative.

**Result**: All 8 scoped modules are clean.

---

## Changes Made

### `dbex/refinement/stage_a.py:1305-1309`

**Before**:
```python
# NOTE: In the current Stage A implementation, `bragg_scaled` plays the role
# of I_model in the variance term while `target_subset` is background-subtracted
# I_obs. Spec-DB core defines I_model as Bragg+background on raw data; see
# docs/config_crosswalk.md "I_model" mapping and TODO‑PHYSICS for planned
# reconciliation.
```

**After**:
```python
# NOTE: In the current Stage A implementation, `bragg_scaled` plays the role
# of I_model in the variance term while `target_subset` is background-subtracted
# I_obs. This is explicitly non-conformant with docs/spec-db-core.md §Loss Definition
# (canonical I_model = Bragg + background on raw data) and docs/config_crosswalk.md
# "Non-conformant implementation note" (lines 153-155). Reconciliation is planned.
```

**Rationale**:
Replaced vague "TODO‑PHYSICS" reference with precise normative spec citations:
- `docs/spec-db-core.md` §Loss Definition (lines 110-126): defines canonical `I_model = Bragg + background` on raw data
- `docs/config_crosswalk.md` lines 153-155: explicitly documents the current implementation as "non-conformant"

---

## Metrics

- **Modules scanned**: 8
- **Comments/docstrings updated**: 1
- **Process noise references replaced**: 1 (TODO‑PHYSICS → spec citations)
- **References unmappable to spec**: 0
- **Net LOC change**: 0 (comment-only edit, same line count)
- **Out-of-scope issues flagged**: 1 (`helpers.py:365`)

---

## Findings

### Spec/Finding Citations Used

- `docs/spec-db-core.md` §Loss Definition (lines 110-126)
  Canonical variance formula `V = I_model + sigma_readout^2` where `I_model = Bragg + background`

- `docs/config_crosswalk.md` lines 153-155
  Explicit non-conformance note for current torch Stage A implementation using Bragg-only on background-subtracted targets

### Unmappable References

None in the 8 scoped modules.

### Out-of-Scope Items

- `dbex/refinement/helpers.py:365` — "TODO: Implement Bragg stitching logic"
  **Action**: Not addressed in this loop (not in scoped module list). Recommend future triage to determine if this is a valid spec-gap TODO or obsolete process noise.

---

## Validation

Post-cleanup grep confirms no low-value process noise (JIRA, ticket IDs, meeting notes, sprint references) remains in the 8 scoped modules.

**Command**:
```bash
rg -n "TODO|FIXME|JIRA|Issue #|ticket" dbex/{geometry,physics,refinement}/*.py
```

**Result**: Only hit is `helpers.py:365` (out of scope for this loop).

---

## Artifacts

All artifacts saved to: `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-05T000500Z/`

- `process_noise_raw.txt` — Raw audit output (1 hit)
- `remaining_noise.txt` — Post-cleanup verification (1 out-of-scope hit)
- `process_noise_audit.md` — This summary

---

## Next Actions

1. **Phase C complete**: All 8 scoped modules cleaned; exit criterion 2 (docstring/spec citation hygiene) now satisfied for the geometry/physics/Stage module set.

2. **Future triage**: `helpers.py:365` TODO is not in Phase C scope but should be evaluated in a future docs/cleanup loop to determine if it describes a spec gap or is obsolete.

3. **Exit criteria check**:
   - Criterion 1 (eager imports at module scope): Already satisfied by Phase B.3 (2025-12-04T010500Z)
   - Criterion 2 (spec/finding citations over process noise): **Satisfied** by this loop for the 8 scoped modules
   - Criterion 3 (import hygiene selector coverage + docs updates): Pending supervisor decision on selector authoring
   - Criterion 4 (problems ledger link): Pending supervisor sign-off

---

## Compliance

- **Initiative type**: architecture — documentation changes only, no semantic behavior changes
- **Spec precedence**: All citations verified against normative spec text
- **Search-first**: Confirmed spec-db-core.md and config_crosswalk.md contain the canonical I_model definitions before editing
- **Environment freeze**: No package changes (docs-only loop)
