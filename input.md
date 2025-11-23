# Phase D3-D5: StageC Wrapper Validation & Documentation Sync

## Summary
Validate Phase D2 StageC wrapper preserves canonical telemetry schema, REFINE-007 gates, and mapping parity; update test registry and mark Phase D COMPLETE.

## Mode
Docs

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase D3-D5: StageC wrapper validation)

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (small + full detector)
- `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` (collect-only + pytest)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/`

## Do Now

**Objective**: Validate StageC wrapper (Phase D2, commit 71d5e0d) against canonical telemetry schema and acceptance gates, execute DB-AT-024 mapping parity check, update test registry, mark Phase D COMPLETE.

**Tasks (9 steps)**:

### 1. Review Phase D2 Evidence
- Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/decision.md` (Ralph's Phase D2 completion)
- Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/metrics.json` (4 tests PASSED)
- Review commit 71d5e0d diff (StageC wrapper class + RefinementTelemetry dataclass extensions)

### 2. Validate Telemetry Schema (Phase D3)
**Goal**: Confirm StageC wrapper preserves canonical Stage A metadata + detector offset reduction stats per implementation.md:242.

**Evidence required**:
- Read one of Ralph's Phase D2 pytest logs (small or full detector) and extract telemetry JSON emitted by StageC.run()
- Verify telemetry contains **ALL** canonical RefinementTelemetry fields from spec-db-core.md telemetry schema:
  - Stage A baseline fields: `chi_squared_initial`, `chi_squared_final`, `masked_mse_initial`, `masked_mse_final`, `param_deltas` (log_scale, cell a/b/c, angles, misset)
  - Stage C-specific fields: `detector_offset_reduction_min`, `detector_offset_final_abs_max`, `param_deltas_c` (distance_offset_raw per panel)
  - Unified fields (Phase A4): `stage_type="C"`, `mode="detector_offsets"`
  - Perf counters: `cache_mode`, `roi_mode`, `forward_time_ms`, etc.
- Write `phase_d3_telemetry_validation.md` documenting field presence (checklist format)
- **Acceptance criterion**: All canonical fields present in telemetry, no missing Stage A metadata

### 3. Rerun Stage C Smoke Tests (Phase D4)
**Goal**: Archive fresh pytest logs + telemetry proving REFINE-007 gates succeed post-refactor.

**Commands**:
```bash
# Small detector (CUDA-only, ROI mode)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/telemetry_stage_c_small.json \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/pytest_stage_c_small.log

# Full detector (CUDA-only, panel mode per GRADIENT-003 CPU deferral)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/telemetry_stage_c_full.json \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --smoke-detector-size=full \
  | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/pytest_stage_c_full.log
```

**REFINE-007 gate validation** (extract from telemetry JSON):
- **Small detector**: `detector_offset_reduction_min >= 0.80` OR `detector_offset_final_abs_max <= 0.05` (mm)
- **Full detector**: Same threshold + `chi_squared_regression <= 0.0005` (≤0.05% relative to Stage A)
- Write `phase_d4_refine007_validation.json` with extracted metrics:
  ```json
  {
    "small_detector": {
      "detector_offset_reduction_min": <value>,
      "detector_offset_final_abs_max": <value>,
      "passed": true/false
    },
    "full_detector": {
      "detector_offset_reduction_min": <value>,
      "detector_offset_final_abs_max": <value>,
      "chi_squared_regression": <value>,
      "passed": true/false
    }
  }
  ```

**Acceptance criterion**: Both tests PASS, both gates satisfied per REFINE-007

### 4. Execute DB-AT-024 Mapping Parity Check (Phase D5)
**Goal**: Confirm StageC refactor did not regress zero-iteration mapping forward model.

**Commands**:
```bash
# Collect-only
pytest --collect-only -q tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/pytest_collect_db_at_024.log 2>&1

# Full test execution
KMP_DUPLICATE_LIB_OK=TRUE \
DBEX_SMOKE_DETECTOR_SIZE=full \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
  | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/pytest_db_at_024.log
```

**Acceptance criterion**: DB-AT-024 PASSED (median corr ≥0.2, localization ≥90%)

### 5. Update Test Registry (TESTING_GUIDE.md + TEST_SUITE_INDEX.md)
**Goal**: Document StageC wrapper in test registry per TESTING-003.

**Edits required**:
1. **docs/TESTING_GUIDE.md §2** (Test Selector Table):
   - Find the `test_torch_refine_smoke.py` row (currently mentions Stage A/B/C smokes with GRADIENT-003 CPU limitation note)
   - Update to reflect Phase D completion: "Stage C wrapper (dbex/refinement/stage_c.py) implemented 2025-11-23, validates RefinementStage protocol compliance and telemetry schema preservation"
   - Ensure GRADIENT-003 CPU limitation note remains (full detector CUDA-only)

2. **docs/development/TEST_SUITE_INDEX.md**:
   - Add row for StageC wrapper test if not already present:
     ```markdown
     | ARCH-REFINE-FLOW-001: StageC Wrapper | `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (engine contract), `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (smoke) | active | `docs/spec-db-workflow.md:33`, `plans/active/ARCH-REFINE-FLOW-001/implementation.md` | StageC class validates RefinementStage protocol, telemetry schema (stage_type/mode), REFINE-007 gates. First added 2025-11-23. |
     ```

**Acceptance criterion**: Both docs updated, registry entries cite correct selectors + artifacts path

### 6. Update docs/findings.md
**Goal**: Document StageC wrapper lessons per Phase D2 decision.md recommendations.

**New findings to add** (if not already present from Ralph's Phase D2 commit):
1. **ARCH-ENGINE-002** (extension of ARCH-ENGINE-001): StageC wrapper pattern mirrors StageB (lazy imports, Stage A param reconstruction from telemetry, helper calls with exact dict structures, baseline_detector requirement, telemetry packaging via asdict → enrich → reconstruct)
2. **REFINE-007 (extension)**: Stage C wrapper requires `baseline_detector` input (NOT optional), raises ValueError if missing, per spec-db-workflow.md:75

**Acceptance criterion**: findings.md updated with 1-2 new rows documenting Phase D lessons

### 7. Mark Phase D COMPLETE in implementation.md
**Goal**: Update checklist status.

**Edits**:
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md` lines 241-244:
  - `- [x] D2: Plug Stage C into the engine` ✓ COMPLETE (2025-11-23T141817Z, commit 71d5e0d)
  - `- [x] D3: Ensure Stage C telemetry keeps canonical Stage A metadata` ✓ COMPLETE (2025-11-23T151440Z, phase_d3_telemetry_validation.md)
  - `- [x] D4: Rerun Stage C smoke tests` ✓ COMPLETE (2025-11-23T151440Z, small+full PASS, REFINE-007 gates satisfied)
  - `- [x] D5: Execute DB-AT selectors` ✓ COMPLETE (2025-11-23T151440Z, DB-AT-024 PASSED)

**Acceptance criterion**: All Phase D checklist rows marked complete with timestamps

### 8. Write Decision Synthesis
**Goal**: Document validation outcomes with 4-path decision tree.

**Create `phase_d3_d5_decision.md`**:
```markdown
# Phase D3-D5 Validation Decision

## Validation Results
- **D3 (telemetry schema)**: PASS/FAIL
- **D4 (Stage C smokes + REFINE-007)**: PASS/FAIL (small + full)
- **D5 (DB-AT-024 parity)**: PASS/FAIL
- **Registry sync**: PASS/FAIL (TESTING_GUIDE.md + TEST_SUITE_INDEX.md updated)

## Decision Path
- **Path A (all PASS)**: Phase D COMPLETE → Next: Phase E orchestration hooks (Galph planning)
- **Path B (telemetry FAIL)**: StageC wrapper missing canonical fields → debug telemetry packaging logic
- **Path C (REFINE-007 FAIL)**: Detector offset gates violated → debug StageC helper wiring
- **Path D (DB-AT-024 FAIL)**: Mapping parity regression → debug zero-iteration forward model

## Confidence
HIGH/MEDIUM/LOW (~X%)

## Next Actions
<per chosen path>
```

### 9. Write summary.md + Commit
**Goal**: Archive loop artifacts and commit docs updates.

**Create `summary.md`**:
```markdown
### Turn Summary
Validated StageC wrapper (Phase D2) preserves canonical telemetry schema, REFINE-007 gates satisfied (small+full detector), DB-AT-024 mapping parity PASSED; no regressions detected.
Updated test registry (TESTING_GUIDE.md, TEST_SUITE_INDEX.md) with StageC wrapper documentation and findings.md with Phase D lessons; marked Phase D COMPLETE.
Next: Galph plans Phase E orchestration hooks (expose stage enablement flags in RefinementEngine/CLI, add engine_protocol telemetry, update architecture docs).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/ (pytest logs, telemetry JSONs, validation reports, decision.md)
```

**Commit message**:
```
ARCH-REFINE-FLOW-001 Phase D3-D5: Validate StageC wrapper + mark Phase D COMPLETE — tests: small+full+DB-AT-024 PASS
```

**Acceptance criterion**: All artifacts archived, git committed + pushed, clean working tree

## How-To Map

### Stage C Smoke Test Execution
```bash
# Small detector
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_TELEMETRY_PATH=<artifacts_path>/telemetry_stage_c_small.json \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --smoke-detector-size=small | tee <artifacts_path>/pytest_stage_c_small.log

# Full detector
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_TELEMETRY_PATH=<artifacts_path>/telemetry_stage_c_full.json \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  --smoke-detector-size=full | tee <artifacts_path>/pytest_stage_c_full.log
```

### DB-AT-024 Execution
```bash
# Collect-only
pytest --collect-only -q tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
  > <artifacts_path>/pytest_collect_db_at_024.log 2>&1

# Full execution
KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=full \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke \
  | tee <artifacts_path>/pytest_db_at_024.log
```

### Telemetry Schema Validation (D3)
1. Extract telemetry JSON from one Phase D2 pytest log OR run fresh Stage C smoke
2. Parse JSON and verify presence of ALL canonical fields:
   - RefinementTelemetry base: `chi_squared_initial`, `chi_squared_final`, `masked_mse_initial`, `masked_mse_final`, `improvement`, `status`, `param_deltas`
   - Stage C-specific: `detector_offset_reduction_min`, `detector_offset_final_abs_max`, `param_deltas_c`
   - Phase A4 extensions: `stage_type`, `mode`
   - Perf counters: `cache_mode`, `roi_mode`, `forward_time_ms.*`, `closure_evals`, `validation_runs`
3. Write checklist to `phase_d3_telemetry_validation.md`

### REFINE-007 Gate Validation (D4)
Extract from telemetry JSON (after Step 3 runs):
```python
import json
with open('telemetry_stage_c_small.json') as f:
    tel = json.load(f)
print(f"detector_offset_reduction_min: {tel.get('detector_offset_reduction_min')}")
print(f"detector_offset_final_abs_max: {tel.get('detector_offset_final_abs_max')}")
# Gate: reduction >= 0.80 OR final_abs_max <= 0.05
```
Write gate pass/fail to `phase_d4_refine007_validation.json`

## Pitfalls To Avoid

1. **Do NOT run tests without environment flags**: All Stage C smokes require `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
2. **Do NOT skip telemetry capture**: Set `DBEX_SMOKE_TELEMETRY_PATH` for both small+full runs to archive telemetry artifacts
3. **Do NOT modify production code**: This is a docs-only validation loop (Mode: Docs), only update docs/findings/implementation.md
4. **Do NOT forget full detector env flag**: DB-AT-024 requires `DBEX_SMOKE_DETECTOR_SIZE=full` per TESTING_GUIDE.md §1.1
5. **Do NOT skip collect-only for DB-AT-024**: Archive collection log to prove selector exists and collects 1 test
6. **CPU fallback NOT supported**: Full detector runs CUDA-only per GRADIENT-003 (HKL grid CPU transfer corruption deferred)
7. **Telemetry schema must be complete**: If ANY canonical field is missing from StageC telemetry, mark D3 FAIL and debug packaging logic
8. **REFINE-007 gates are strict**: Both detector offset reduction AND chi² regression must pass (≥80% reduction OR ≤±0.05mm final, AND ≤0.05% χ² regression)
9. **Registry sync is mandatory**: TESTING-003 requires TESTING_GUIDE.md + TEST_SUITE_INDEX.md updates after new tests are validated
10. **Archive ALL artifacts**: pytest logs, telemetry JSONs, validation reports, decision.md all go to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/`

## If Blocked

**Telemetry schema validation FAIL** (D3):
- Identify missing fields from checklist
- Review `dbex/refinement/stage_c.py` telemetry packaging logic (lines ~350-408 in Phase D2 commit 71d5e0d)
- Check if RefinementTelemetry dataclass is missing fields (should have been extended in Phase A4)
- Log blocker in `phase_d3_d5_decision.md` Path B, escalate to Galph next loop

**REFINE-007 gate FAIL** (D4):
- Extract actual telemetry values (detector_offset_reduction_min, detector_offset_final_abs_max, chi_squared_regression)
- Compare to thresholds (≥0.80 reduction OR ≤0.05mm final, ≤0.05% chi² regression)
- Review StageC helper wiring (did Phase D2 correctly call _build_stage_c_params / _build_stage_c_lbfgs_closure / _run_stage_c_lbfgs?)
- Log blocker in `phase_d3_d5_decision.md` Path C, escalate to Galph

**DB-AT-024 FAIL** (D5):
- Check pytest log for specific failure (correlation/localization thresholds)
- Verify Phase D2 changes did not modify `simulate_forward_once` or zero-iteration mapping path
- DB-AT-024 tests zero-iteration forward model, NOT refinement, so StageC wrapper should not affect it
- Log blocker in `phase_d3_d5_decision.md` Path D, escalate to Galph

**Test collection FAIL**:
- Verify selector path is correct: `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`
- Run `pytest --collect-only -q tests/dbex/test_mapping_consistency.py` to check if test exists
- Log import errors or missing test to decision.md, escalate

**Git commit conflicts**:
- Run `git status` to inspect conflicts
- Resolve (keep upstream for code, merge docs/findings/implementation.md updates)
- `git add` resolved files, `git rebase --continue` (with timeout 30)
- Log resolution decisions in summary.md

## Findings Applied

**Mandatory findings adherence**:

1. **REFINE-007** (Stage C gate: ≥80% offset reduction OR ≤±0.05mm final, ≤0.05% χ² regression) — Validate Phase D4 against this gate, extract telemetry metrics, write validation JSON
2. **TESTING-003** (Test registry sync: update TESTING_GUIDE.md + TEST_SUITE_INDEX.md after validation, archive collect-only logs) — Step 5 implements this
3. **GRADIENT-003** (CPU fallback deferred: HKL grid CPU transfer corruption, full detector CUDA-only) — Do NOT attempt CPU runs, skip CPU tests per Phase C2.5 deferral decision
4. **POLICY-001** (Environment Freeze: no package installs, code-only or docs-only changes) — This is a docs-only validation loop, no production code edits
5. **PHYSICS-LOSS-001/002** (Variance-weighted loss dual metrics + sigma_floor telemetry) — Verify telemetry schema includes chi_squared and masked_mse fields (Step 2)
6. **PERF-WARM-006** (Stage C warm cache: reuse Stage A detector configs/masks) — Not directly validated this loop, but telemetry schema includes cache_mode/roi_mode
7. **CONFORMANCE-001** (DB-AT environment flags: KMP_DUPLICATE_LIB_OK=TRUE, DBEX_SMOKE_DETECTOR_SIZE=full) — Step 4 uses correct env flags
8. **RUNTIME-001** (NANOBRAGG_DISABLE_COMPILE=1 for gradient tests) — Stage C smokes are LBFGS refinement tests, flag required

**No relevant findings from knowledge base** that contradict this validation plan.

## Pointers

- **Spec References**:
  - `docs/spec-db-workflow.md:73-89` (Stage C detector offset refinement, REFINE-007 gate definition)
  - `docs/spec-db-core.md:57-68` (Variance-weighted chi-squared telemetry schema, sigma_floor guard)
  - `docs/spec-db-runtime.md:26` (Environment flags for pytest)
  - `docs/spec-db-conformance.md:28` (DB-AT selector environment requirements)

- **Architecture**:
  - `plans/active/ARCH-REFINE-FLOW-001/implementation.md:241-244` (Phase D checklist, exit criteria)
  - `docs/architecture/pytorch_design.md` (RefinementStage protocol, telemetry aggregation)

- **Testing**:
  - `docs/TESTING_GUIDE.md:12-60` (Stage smoke dataset policy, environment flags, telemetry capture)
  - `docs/development/TEST_SUITE_INDEX.md:12` (Stage A/B/C smoke registry row)
  - `docs/development/testing_strategy.md:169-174` (Test registry sync requirements per TESTING-003)

- **Findings**:
  - `docs/findings.md` row 58 (REFINE-007: Stage C gate definition)
  - `docs/findings.md` row 69 (GRADIENT-003: CPU fallback deferred)
  - `docs/findings.md` row 42 (TESTING-003: Registry sync protocol)

- **Phase D Evidence**:
  - `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/decision.md` (Ralph's Phase D2 completion, all 4 tests PASSED)
  - `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/summary.md` (Turn Summary block with artifacts path)

- **Fix Plan**:
  - `docs/fix_plan.md` ARCH-REFINE-FLOW-001 row (Status: in_progress, Phase D1b complete per galph_memory.md, Phase D2-D5 pending)

## Next Up (optional)

If all Phase D3-D5 validation gates PASS and you finish early, you may **read-only preview** Phase E requirements (DO NOT implement):

1. Read `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase E section (lines 251-260)
2. Note Phase E objectives: Expose stage registry/config knobs in RefinementEngine, update CLI to accept enablement flags, add engine_protocol telemetry
3. Identify which files will need production code changes in Phase E: `dbex/refinement/engine.py`, `dbex/nanobrag_refinement.py`, `dbex/refine_one.py`, config dataclasses
4. Write 1-2 sentence note in `phase_d3_d5_decision.md` about Phase E preview (e.g., "Phase E will require production code changes to RefinementEngine for stage enablement flags; estimated 2-3 loops for E1-E5")

**DO NOT**:
- Author Phase E implementation code
- Modify engine.py or refine_one.py
- Create Phase E Do Now (Galph will do this next loop)
- Extend this loop beyond Phase D3-D5 validation scope

## Doc Sync Plan (Conditional)

**NOT APPLICABLE** — No new tests added this loop (validation-only). Test registry updates (Step 5) document existing StageC wrapper selector, but no pytest --collect-only artifacts required since selectors already exist and were validated in Phase D2.

If you DO run `pytest --collect-only` for DB-AT-024 in Step 4, archive the log to artifacts/ but do NOT update registry again (it's already documented).

## Mapped Tests Guardrail

**All selectors collect >0 tests** (verified Phase D2):
- `test_stage_c_detector_microslip`: 1 test (small detector), 1 test (full detector) — 2 total
- `TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`: 1 test

No new tests authored this loop, so guardrail satisfied by Phase D2 evidence.

## Normative Math/Physics

**REFINE-007 Gate Definition** (do NOT paraphrase):
- See `docs/spec-db-workflow.md:73-89` (Stage C detector offset refinement)
- Acceptance criteria:
  1. `detector_offset_reduction >= 0.80` (≥80% reduction from initial injected offset)
     OR `detector_offset_final_abs_max <= 0.05` (mm) (final offset within ±0.05mm tolerance)
  2. `chi_squared_regression <= 0.0005` (≤0.05% relative to Stage A final chi²)

**Variance-Weighted Chi-Squared** (telemetry schema):
- See `docs/spec-db-core.md:57-68` (Loss Function Definition)
- Normative formula: `χ² = Σ_pixels ((I_model - I_obs)² / V)` where `V = max(I_model + σ_readout², σ_floor²)`
- Telemetry MUST report BOTH `chi_squared` (variance-weighted) AND `masked_mse` (legacy compatibility)

Do NOT create pseudo-code implementations; Ralph should read the spec directly if unclear.
