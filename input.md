# ARCH-REFINE-FLOW-001 Phase B: Stage A Extraction

## Summary
Extract Stage A implementation onto the RefinementEngine by wrapping the current LBFGS closure logic into a StageA class that implements the RefinementStage protocol, and delegate run_nanobrag_refinement Stage A path to the engine.

## Mode
none — Stage A extraction (production code refactor + validation)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B: Stage A Extraction)

## Branch
integration

## Mapped Tests
- **Stage A Smoke (Small Detector):** `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- **Stage A Smoke (Full Detector):** `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- **DB-AT-010 Gradcheck:** `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_gradcheck.py::test_stage_a_autograd`
- **DB-AT-024 Mapping:** `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_forward_equivalence.py::test_torch_nanobrag_mapping`
- **ARCH-ENGINE-001 TDD Nucleus:** `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage`

## Artifacts
Base directory: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/`

Files to create:
- `baseline/` subdirectory for pre-refactor artifacts
- `phase_b_implementation_summary.md`
- `pytest_stage_a_small.log`, `pytest_stage_a_full.log`
- `pytest_db_at_010.log`, `pytest_db_at_024.log`, `pytest_arch_engine_001.log`
- `phase_b_decision.json`
- `telemetry_stage_a_small.json`, `telemetry_stage_a_full.json`
- `summary.md`


## Do Now

**Phase B Objective:** Extract Stage A onto engine, preserve exact behavior (no drift, no regressions).

### Step-by-Step Protocol

#### 1. Context Priming
Read before implementation:
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/phase_a_implementation_summary.md`
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase B section
- `dbex/nanobrag_refinement.py` lines ~600-1200 (existing Stage A)

#### 2. B0: Record Baseline
```bash
mkdir -p plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline

# Collect-only
pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/pytest_collect.log 2>&1

# Small baseline
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/pytest_small.log 2>&1

# Full baseline
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/pytest_full.log 2>&1
```

#### 3. B1: Implement StageA Class
Create `dbex/refinement/stage_a.py`:
- Implement RefinementStage protocol (name, configure, run)
- Reuse existing `build_stage_a_lbfgs_closure` and `run_lbfgs_optimization`
- Return telemetry dict with stage_type="stage_a", mode field
- Use lazy imports for dbex.nanobrag_refinement
- Preserve: warm-cache, ROI sampling, incremental_ub, variance telemetry

#### 4. B2: Wire StageA into Engine
Update `dbex/nanobrag_refinement.py::run_nanobrag_refinement`:
- Replace Stage A inline code with:
  ```python
  from dbex.refinement import RefinementEngine
  from dbex.refinement.stage_a import StageA
  stage_a = StageA()
  engine = RefinementEngine(stages=[stage_a], config=config)
  telemetry_dict = engine.run(inputs=inputs, telemetry_sink=telemetry_sink)
  ```
- Preserve Stage B/C inline code unchanged
- Preserve telemetry propagation to Stage B/C

#### 5. B3: Validate Smoke Tests
```bash
# Small
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/telemetry_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/pytest_small.log 2>&1

# Full
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/telemetry_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/pytest_full.log 2>&1
```

Compare telemetry: chi² drift <0.01%, perf counters match, schema extensions present.

#### 6. B4: Run DB-AT Selectors
```bash
# Gradcheck
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_gradcheck.py::test_stage_a_autograd > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/pytest_db_at_010.log 2>&1

# Mapping
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full pytest -vv tests/dbex/test_forward_equivalence.py::test_torch_nanobrag_mapping > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/pytest_db_at_024.log 2>&1

# Regression
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/pytest_arch_engine_001.log 2>&1
```

All 5 tests MUST PASS.

#### 7. Extract Metrics & Decision
Create `phase_b_decision.json`:
- Decision Path A: All tests PASS, drift <0.01% → Phase C next
- Decision Path C: Any test FAIL or drift >1% → Debug blocker
- Decision Path D: ARCH-ENGINE-001 FAIL → Escalate (Phase A regression)

#### 8. Update Implementation Checklist
Mark `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase B tasks [x] complete.

#### 9. Write Phase B Summary
Create `phase_b_implementation_summary.md` with code changes, metrics, next steps.

#### 10. Write Turn Summary
Create `summary.md` (3-5 sentences, artifacts path).

#### 11. Commit & Push
```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase B: Stage A Extraction

StageA class wraps existing LBFGS closure, engine delegates Stage A.
All validation PASSED: smoke (small/full), DB-AT-010, DB-AT-024, ARCH-ENGINE-001.
Telemetry drift <0.01%, perf counters match, schema extensions present.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

## Pitfalls To Avoid
1. DO NOT duplicate LBFGS closure — reuse existing functions
2. DO NOT refactor Stage B/C — preserve inline code
3. DO NOT break telemetry propagation to downstream stages
4. DO NOT introduce numerical drift >0.01%
5. DO NOT break warm-cache, ROI sampling, incremental_ub
6. DO NOT use circular imports — lazy imports only
7. DO NOT skip baseline artifacts
8. DO NOT commit without all 5 tests PASSING

## Findings Applied
- REFINE-005/006 (Stage A gates), PERF-WARM-SIM-001 (warm cache), GEOMETRY-004 (incremental UB), PHYSICS-LOSS-001 (variance loss), POLICY-001 (Environment Freeze), ARCH-REFINE-FLOW-001 Phase A (protocol contract)

## Pointers
- `docs/spec-db-workflow.md:33,35-62` (Engine contract, Stage A)
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md` (Phase B plan)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/` (Phase A artifacts)
- `docs/fix_plan.md:181-196` (ARCH-REFINE-FLOW-001 status)

