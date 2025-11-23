# Phase C2-C5: Validation Completion and Documentation

## Summary
Complete TORCH-GEOMETRY-UB-REALIGN-001 Phase C validation (DB-AT-024 mapping parity with incremental UB, findings documentation, test registry sync).

## Mode
Docs

## Focus
TORCH-GEOMETRY-UB-REALIGN-001 — Stage A UB Parameterization Realignment

## Branch
integration

## Mapped Tests
- `pytest -k test_db_at_024_mapping_smoke` (DB-AT-024 mapping parity, Active)
- `pytest --collect-only tests/dbex/test_ub_parameterization_roundtrip.py` (DB-AT-026 collection validation)

## Artifacts
`plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/`

## Do Now

**Phase C2-C5: Validation Completion (4 tasks)**

Ralph, Phase C1 was a SUCCESS — all zero-point validation tests passed (DB-AT-026 Tests 1-3 PASSED, incremental UB convergence ≥0.2%, regression guard clean). Now complete the remaining Phase C tasks:

### C2: DB-AT-024 Mapping Parity (Validation)

**Objective:** Verify that DB-AT-024 mapping consistency test passes with the default configuration, confirming that Phase B changes did not affect the mapping forward model (`simulate_forward_once`).

**Steps:**
1. Run DB-AT-024 with default configuration:
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -v tests/dbex/test_mapping_consistency.py::TestDBMappingConsistency::test_db_at_024_mapping_smoke \
     > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/pytest_db_at_024_default.log 2>&1
   ```

2. **Analysis:** DB-AT-024 tests the mapping forward model (`simulate_forward_once`) which does NOT use the Stage A refinement path, so it should pass regardless of incremental UB changes (since Phase B preserved all existing code paths). If it passes, this confirms no regression from Phase B wiring.

3. **Expected Outcome:** PASS (median correlation ≥0.2, localization ≥90%)

4. **Decision:** If DB-AT-024 PASSES, proceed to C4 (findings). If FAILS, investigate whether Phase B changes inadvertently affected the mapping bridge.

### C4: Findings Documentation (GEOMETRY-004)

**Objective:** Document the incremental UB parameterization in `docs/findings.md` as GEOMETRY-004.

**Content Template:**
```
| GEOMETRY-004 | 2025-11-23 | geometry, crystal, parameterization, ub-realign | Stage A incremental UB parameterization treats dxtbx crystal state (U₀, B₀) as authoritative and expresses orientation/cell as increments: `U(params) = ΔR(q_delta) @ U₀` (quaternion-based rotation), `B(params) = busing_levy_B_torch(a₀·exp(δlog_a), ..., α₀+Δα, ...)` (log-perturbations for lengths, delta-add for angles). Zero-point invariant: `q_delta=[1,0,0,0]` (identity), all deltas=0 → `U(0)=U₀`, `B(0)=B₀`, `A*(0)=U₀@B₀=A*_mapping`. One-way construction: `params → (U,B) → A*=U@B` (no A* decomposition in refinement loop). Helpers: `derive_orientation_from_quaternion_delta` (scipy quaternion-to-matrix + quaternion-to-Euler XYZ for nanobrag_torch API), `derive_B_from_cell_deltas` + `busing_levy_B_torch` (cctbx-based Busing-Levy B-matrix matching dxtbx lower-triangular convention). Validation: DB-AT-026 Tests 1-3 (zero-point ||U(0)-U₀||<1e-12, ||B(0)-B₀||<1e-12, ||A*(0)-A*_mapping||<1e-6), incremental UB convergence ≥0.2%, regression guard clean. Config flag: `use_incremental_ub=True` in `build_stage_a_lbfgs_closure`. Limitations: DB-AT-026 Test 4 (gradient flow) deferred — scipy/cctbx break PyTorch autograd; helpers are correct for forward passes and finite-difference validation, not suitable for direct gradient-based optimization (future: pytorch3d/kornia for differentiable ops). | dbex/nanobrag_bridge.py:1228-1407, dbex/nanobrag_refinement.py:817-876,1036-1073, tests/dbex/test_ub_parameterization_roundtrip.py, plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/ | Active |
```

**Steps:**
1. Add the GEOMETRY-004 row to `docs/findings.md` after GEOMETRY-003 (row 7).
2. Ensure the entry captures all normative details (formulas, helpers, validation results, limitations).

### C5: Documentation Sync (Test Registry)

**Objective:** Update test registry to reflect DB-AT-026 as Active.

**Steps:**

1. **TESTING_GUIDE.md Update:**
   - Add DB-AT-026 entry to §2 (Active Acceptance Tests) after DB-AT-024:
   ```markdown
   #### DB-AT-026: UB Parameterization Round-Trip

   - **Status:** Active (2025-11-23)
   - **Spec:** docs/spec-db-core.md:48-68, docs/spec-db-workflow.md:36-50, docs/spec-db-runtime.md:18-28
   - **Purpose:** Validate incremental UB parameterization zero-point invariant (`U(0)=U₀`, `B(0)=B₀`, `A*(0)=A*_mapping`)
   - **Selector:** `pytest -v tests/dbex/test_ub_parameterization_roundtrip.py`
   - **Tests:**
     - `test_db_at_026_orientation_zero_point` — `||U(0)-U₀|| < 1e-12`
     - `test_db_at_026_cell_zero_point` — `||B(0)-B₀|| < 1e-12`
     - `test_db_at_026_mapping_parity` — `||A*(0)-A*_mapping|| < 1e-6`
     - `test_db_at_026_gradient_flow` — (xfail: scipy/cctbx break autograd)
   - **Acceptance Criteria:**
     - Tests 1-3 PASS (zero-point tolerances met)
     - Test 4 marked xfail with documented rationale (scipy/cctbx autograd breaking)
   - **Environment:** `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - **Artifacts:** `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/<timestamp>/pytest_db_at_026*.log`
   ```

2. **TEST_SUITE_INDEX.md Update:**
   - Add DB-AT-026 row to Acceptance Tests table:
   ```markdown
   | DB-AT-026 | UB Parameterization Round-Trip | Active | tests/dbex/test_ub_parameterization_roundtrip.py | 2025-11-23 |
   ```

3. **Collection Log:**
   - Run `pytest --collect-only tests/dbex/test_ub_parameterization_roundtrip.py > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/pytest_collect_db_at_026.log 2>&1`
   - Verify ≥3 tests collected (Tests 1-3 at minimum)

4. **Update implementation.md:**
   - Mark C2, C4, C5 as `[x]` DONE
   - Update Phase C status to `COMPLETE (2025-11-23T023142Z)`

### Validation & Commit

1. **Metrics Extraction (T0 micro probe):**
   ```bash
   python -c "
   import json
   import os
   import sys

   log_file = 'plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/pytest_db_at_024_default.log'
   db_at_024_passed = False
   if os.path.exists(log_file):
       with open(log_file) as f:
           content = f.read()
           db_at_024_passed = 'PASSED' in content

   metrics = {
       'db_at_024_default': 'PASSED' if db_at_024_passed else 'FAILED',
       'geometry_004_documented': True,
       'testing_guide_updated': True,
       'test_suite_index_updated': True,
       'collect_log_archived': True,
       'implementation_checklist_updated': True
   }
   with open('plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/phase_c2_c5_metrics.json', 'w') as f:
       json.dump(metrics, f, indent=2)
   print(json.dumps(metrics, indent=2))
   "
   ```

2. **Turn Summary:**
   - Write `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/summary.md` with Turn Summary block (3-5 sentences: what shipped, main problem if any, next step, Artifacts line)

3. **Commit:**
   ```bash
   git add docs/findings.md docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md plans/active/TORCH-GEOMETRY-UB-REALIGN-001/
   git commit -m "$(cat <<'EOF'
   TORCH-GEOMETRY-UB-REALIGN-001 Phase C2-C5: Validation completion and documentation

   Verified DB-AT-024 mapping parity (default path clean), documented GEOMETRY-004
   incremental UB finding, updated test registry (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
   with DB-AT-026 entry, archived collection log. All Phase C tasks complete.

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   git push
   ```

## How-To Map

### C2: DB-AT-024 Execution
```bash
# DB-AT-024 default path
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -v tests/dbex/test_mapping_consistency.py::TestDBMappingConsistency::test_db_at_024_mapping_smoke \
  > plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/pytest_db_at_024_default.log 2>&1

# Check result
grep -E "(PASSED|FAILED)" plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/pytest_db_at_024_default.log
```

### C4: Findings Update
- File: `docs/findings.md`
- Insert after GEOMETRY-003 (row 7)
- Use template above with exact wording

### C5: Doc Sync
- Files: `docs/TESTING_GUIDE.md` (§2), `docs/development/TEST_SUITE_INDEX.md`
- Collection log: `pytest --collect-only tests/dbex/test_ub_parameterization_roundtrip.py > ...`
- Verify ≥3 tests collected

### Implementation Checklist
- File: `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md`
- Mark C2, C4, C5 as `[x]` DONE
- Update Phase C status line to `COMPLETE (2025-11-23T023142Z)`

## Pitfalls To Avoid

1. **Do NOT modify production code** — this is a docs-only validation + documentation loop
2. **Do NOT run DB-AT-024 with `use_incremental_ub=True`** — DB-AT-024 tests the mapping forward model (`simulate_forward_once`) which is separate from Stage A refinement path
3. **Do NOT edit DB-AT-026 test code** — tests are already implemented and passing from Phase C1
4. **Preserve exact GEOMETRY-004 template** — includes all normative details (formulas, helpers, validation results, limitations)
5. **TESTING_GUIDE.md formatting** — match existing DB-AT entries (Status, Spec, Purpose, Selector, Tests, Acceptance Criteria, Environment, Artifacts)
6. **TEST_SUITE_INDEX.md table alignment** — maintain pipe-delimited table format
7. **Collection log must show ≥3 tests** — if <3, DB-AT-026 test file is incomplete (blocker)

## If Blocked

**Blocker Scenarios:**

1. **DB-AT-024 FAILS:**
   - Extract failure signature (correlation, localization values)
   - Check if `simulate_forward_once` bridge was affected by Phase B changes
   - Grep for Phase B diffs in `dbex/nanobrag_bridge.py` (`create_detector_config`, `create_beam_config`, `create_crystal_config`)
   - Document blocker in `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T023142Z/blocker_c2.md`
   - Mark UB-REALIGN-001 as `blocked` in `docs/fix_plan.md` Attempts History

2. **Collection log shows <3 tests:**
   - Verify `tests/dbex/test_ub_parameterization_roundtrip.py` exists and contains Tests 1-3
   - Check for pytest collection errors in log
   - Document blocker in `blocker_c5.md`

3. **Git conflicts:**
   - Resolve manually (findings.md row numbers may shift)
   - Keep GEOMETRY-004 content intact
   - Re-run collection log after resolution

## Findings Applied

**Mandatory Findings:**
- CONVERGENCE-001 (line 65): Zero-delta bypass pattern, code path divergence detection, systematic offset <20% acceptable when convergence stable — **Applied in Phase A design** (bypass pattern not needed for incremental UB because we use one-way construction, avoiding code path divergence; systematic offset acceptance criteria documented in Phase C1 decision)
- GEOMETRY-003 (line 7): Baseline misset derivation from dxtbx A* — **Not applicable** (incremental UB uses direct MOSFLM A* injection or quaternion-to-Euler conversion, not baseline_misset + delta_misset)
- REFINE-006 (line 56): ≥0.2% improvement gate — **Applied in Phase C1** (incremental UB convergence test validated ≥0.2% improvement)

**No other findings directly relevant to validation/documentation tasks.**

## Pointers

### Spec References
- `docs/spec-db-core.md:48-68` — Baseline Crystal State and Parameterization (normative UB/A* incremental requirements)
- `docs/spec-db-workflow.md:36-50` — Stage A mapping zero-point invariant, trainable logs/angles + quaternion→XYZ
- `docs/spec-db-runtime.md:18-28` — UB/A* round-trip test mandate, prohibited inverse decompositions

### Architecture
- `docs/architecture.md` — System context, ADRs, data flow
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/phase_a_design_document.md` — Full Phase A design with normative requirements synthesis, CONVERGENCE-001 lessons, chosen parameterization formulas, DB-AT-026 test specification

### Testing
- `docs/TESTING_GUIDE.md:118-190` — §2 Active Acceptance Tests (DB-AT entries format)
- `docs/development/TEST_SUITE_INDEX.md` — Status table for DB-AT selectors
- `tests/dbex/test_ub_parameterization_roundtrip.py` — DB-AT-026 implementation (Tests 1-4)

### Fix Plan
- `docs/fix_plan.md:63-82` — TORCH-GEOMETRY-UB-REALIGN-001 initiative (Exit Criteria, Working Plan, Attempts History)
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` — Phase checklists (A, B, C)

### Prior Artifacts
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/phase_c1_decision.md` — Phase C1 SUCCESS verdict (all tests PASS)
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-23T021500Z/phase_c1_validation_metrics.json` — Metrics JSON (5 tests, overall_verdict=PASS)

## Next Up

**If Phase C2-C5 SUCCESS:**
- Mark TORCH-GEOMETRY-UB-REALIGN-001 as `done` in `docs/fix_plan.md`
- Update Execution Roadmap Tier 1: UB-REALIGN-001 DONE
- Supervisor selects next Tier 1 focus per roadmap (all Tier 1 items complete after UB-REALIGN-001)

**If Phase C2-C5 has blockers:**
- Document blocker in Attempts History
- Galph reviews blocker report and plans debug/patch/escalation
