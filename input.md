# Ralph Input — PERF-WARM-SIM-001 Phase D Validation Unblocking (Engine Delegation Telemetry Key Fix)

## Summary
Fix trivial telemetry key mismatch (5 lines) where engine delegation returns lowercase stage names but tests expect uppercase letters, unblocking PERF-WARM-SIM-001 Phase D validation.

## Mode
none

## Focus
PERF-WARM-SIM-001 — Warm Simulator: Eliminate Per-Iteration Re-Instantiation (Phase D Validation Unblocking)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (PRIMARY blocker, expects telemetry_dict["C"])
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, expects telemetry_dict["A"])

## Artifacts
`plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/`
- `pytest_stage_c_small.log` (test execution log for primary blocker)
- `pytest_stage_a_expansion.log` (regression guard log)
- `summary.md` (Turn Summary with blocker diagnosis and fix validation)

## Do Now

**Context:** Ralph's Phase D implementation (commit 1bdeca3, loop i=236) is **code-complete and correct** (D1-D3 tasks: StageAContext extension, _retarget_stage_a_detectors helper, Stage C warm branch refactoring). Validation is blocked by ARCH-REFINE-FLOW-001 Phase E regression where commit 9bbd1e8 enabled engine delegation (`use_engine_delegation=True`) for all smoke tests but engine delegation returns telemetry keyed by lowercase stage names (`"stage_a"`, `"stage_b"`, `"stage_c"` per dbex/refinement/stage_{a,b,c}.py `_name` attributes) while tests expect uppercase single-letter keys (`"A"`, `"B"`, `"C"` per legacy convention).

**Blocker Scope:**
- **Affected tests:** 5 tests using engine delegation (test_stage_a_expansion line 380, test_stage_a_engine_delegation_telemetry line 854, test_stage_c_detector_microslip line 975, test_stage_b_shell_small/full line 1284)
- **Root cause:** `dbex/nanobrag_refinement.py:4494` constructs `telemetry_out[stage_name]` where `stage_name = s.name` from RefinementStage protocol (lowercase), but tests assert `telemetry_dict["A"]`, `telemetry_dict["C"]`
- **Fix:** Add mapping dict converting lowercase stage names to uppercase single-letter keys at line 4487-4494

**This loop's task:** Apply 5-line telemetry key mapping fix to unblock Phase D validation. DO NOT touch Phase D detector reuse code (dbex/nanobrag_refinement.py:381,647,693-770,3121-3165,3471-3515) — it is correct and must not be modified.

### Step 1: Apply Telemetry Key Mapping Fix

**File:** `dbex/nanobrag_refinement.py`

**Location:** Lines 4487-4494 (engine delegation telemetry enrichment block)

**Current code (lines 4487-4494):**
```python
# Enrich telemetry with engine protocol + stage modes
telemetry_out = {}
for stage_name, telem_obj in engine_telemetry.items():
    # Convert RefinementTelemetry to dict, add new fields, reconstruct
    telem_dict = asdict(telem_obj)
    telem_dict["engine_protocol"] = engine_protocol
    telem_dict["stage_modes"] = stage_modes
    telemetry_out[stage_name] = RefinementTelemetry(**telem_dict)
```

**New code (add 2-line mapping dict + apply at line 4494):**
```python
# Enrich telemetry with engine protocol + stage modes
telemetry_out = {}
# Map stage names to legacy uppercase keys for backward compatibility
stage_name_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}
for stage_name, telem_obj in engine_telemetry.items():
    # Convert RefinementTelemetry to dict, add new fields, reconstruct
    telem_dict = asdict(telem_obj)
    telem_dict["engine_protocol"] = engine_protocol
    telem_dict["stage_modes"] = stage_modes
    legacy_key = stage_name_map.get(stage_name, stage_name)  # Apply mapping, fallback to original
    telemetry_out[legacy_key] = RefinementTelemetry(**telem_dict)
```

**Changes:**
- Add `stage_name_map` dict at line 4489 (after `telemetry_out = {}`)
- Replace line 4494 `telemetry_out[stage_name] = ...` with:
  ```python
  legacy_key = stage_name_map.get(stage_name, stage_name)
  telemetry_out[legacy_key] = RefinementTelemetry(**telem_dict)
  ```

### Step 2: Validate Fix with Primary Blocker + Regression Guard

Run both tests to confirm telemetry key mapping fix unblocks Phase D validation:

```bash
# Primary blocker (Stage C detector microslip smoke, expects telemetry_dict["C"])
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip -v 2>&1 | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/pytest_stage_c_small.log

# Regression guard (Stage A expansion, expects telemetry_dict["A"])
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v 2>&1 | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/pytest_stage_a_expansion.log
```

**Expected outcome:**
- **Path A (SUCCESS):** Both tests PASS → telemetry key mapping fix unblocks Phase D validation → proceed to Step 3
- **Path B (Stage C smoke FAIL with different error):** Debug new failure signature, compare against phase_d_decision.md blocker analysis (KeyError: 'refinement_inputs' was Ralph's incorrect diagnosis; actual blocker was telemetry key mismatch)
- **Path C (regression guard FAIL):** Rollback mapping, investigate side effects, check if Stage A-only mode still uses legacy telemetry structure
- **Path D (compilation FAIL):** Fix syntax error in mapping dict or legacy_key assignment, rerun

### Step 3: Write Turn Summary

After tests PASS (Path A), write summary to artifacts directory:

**File:** `plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/summary.md`

Include:
- Turn Summary block (3-5 sentences): What shipped (telemetry key mapping fix), main problem and resolution (engine delegation lowercase vs test uppercase expectations), next step (Ralph proceeds to Phase D full validation suite next loop)
- Artifacts list (pytest logs, summary.md)
- Validation results (both tests PASSED, telemetry keys "A" and "C" now present)

### Step 4: Commit and Push

**Commit message:**
```
ENGINEER: PERF-WARM-SIM-001 Phase D unblocking — engine delegation telemetry key fix (tests: test_stage_c_detector_microslip, test_stage_a_expansion)

Map lowercase stage names to uppercase keys for backward compatibility.
Ralph's Phase D detector reuse implementation (commit 1bdeca3) unblocked.
```

**Commands:**
```bash
git add dbex/nanobrag_refinement.py plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/
git commit -m "ENGINEER: PERF-WARM-SIM-001 Phase D unblocking — engine delegation telemetry key fix (tests: test_stage_c_detector_microslip, test_stage_a_expansion)

Map lowercase stage names to uppercase keys for backward compatibility.
Ralph's Phase D detector reuse implementation (commit 1bdeca3) unblocked."
git push
```

## How-To Map

### Environment Variables
None required. Tests run with default config (`use_engine_delegation=True` per commit 9bbd1e8).

### File Locations
- **Fix:** `dbex/nanobrag_refinement.py:4487-4494` (engine delegation telemetry enrichment block)
- **Test blockers:** `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (line 975), `test_stage_a_expansion` (line 380)
- **Stage name sources:** `dbex/refinement/stage_{a,b,c}.py` (`_name = "stage_a"/"stage_b"/"stage_c"`)

### Exact Commands
```bash
# Step 1: Apply fix (use Edit tool on dbex/nanobrag_refinement.py:4487-4494)
# (see Do Now Step 1 for exact code replacement)

# Step 2: Validate with pytest
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip -v 2>&1 | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/pytest_stage_c_small.log
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v 2>&1 | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/pytest_stage_a_expansion.log

# Step 3: Write summary.md (use Write tool)
# (see Do Now Step 3 for content template)

# Step 4: Commit and push
git add dbex/nanobrag_refinement.py plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/
git commit -m "ENGINEER: PERF-WARM-SIM-001 Phase D unblocking — engine delegation telemetry key fix (tests: test_stage_c_detector_microslip, test_stage_a_expansion)

Map lowercase stage names to uppercase keys for backward compatibility.
Ralph's Phase D detector reuse implementation (commit 1bdeca3) unblocked."
git push
```

## Pitfalls To Avoid

1. **DO NOT touch Phase D detector reuse code** — Lines 381,647,693-770,3121-3165,3471-3515 are correct and code-complete per phase_d_decision.md. This loop fixes cross-initiative telemetry key regression only.
2. **Preserve backward compatibility** — Use `.get(stage_name, stage_name)` fallback so unknown stage names pass through unchanged (future-proofs for Stage D/E extensions).
3. **DO NOT modify Stage wrapper _name attributes** — `dbex/refinement/stage_{a,b,c}.py` `_name` fields are part of RefinementStage protocol contract (lowercase convention is correct per engine design). Tests must accept both uppercase (legacy) and lowercase (engine) keys via mapping.
4. **Device/dtype neutrality NOT relevant here** — This is a pure Python dict key mapping fix (no tensor ops, no GPU/CPU branches).
5. **Protected Assets (none for this fix)** — Telemetry schema unchanged (RefinementTelemetry dataclass fields unaffected), only dict key labels mapped.
6. **DO NOT disable use_engine_delegation in tests** — Phase E validated engine delegation as the primary path; tests must work with `use_engine_delegation=True` per commit 9bbd1e8.
7. **Environment Freeze** — No package installs. This is code-only fix (5-line mapping dict).

## If Blocked

**Blocker Type A: Stage C smoke still fails with telemetry KeyError after mapping fix**
- **Action:** Read `pytest_stage_c_small.log` for exact error signature
- **Capture:** Full traceback, line number, failing assertion
- **Log:** Create `blocker_stage_c.md` in artifacts directory with error details + analysis (compare against phase_d_decision.md blocker hypothesis)
- **Return:** Commit partial progress (mapping fix only), write blocker summary in `summary.md`, return control to Galph

**Blocker Type B: Regression guard (test_stage_a_expansion) fails after mapping fix**
- **Action:** Read `pytest_stage_a_expansion.log` for error signature
- **Capture:** Check if Stage-A-only mode telemetry structure differs from A→B/A→B→C modes
- **Log:** Create `blocker_stage_a.md` with analysis (check if Stage-A-only mode bypasses engine delegation entirely)
- **Return:** Rollback mapping change, commit original state, write blocker summary, return to Galph

**Blocker Type C: Compilation/import fails after mapping dict addition**
- **Action:** Fix syntax (likely missing comma or indentation error)
- **Retry:** Run compilation check `python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement"`
- **Escalate:** If import fails with circular dependency or module error, document in `blocker_import.md` and return to Galph

**Blocker Type D: Tests pass but telemetry validation reveals schema corruption**
- **Action:** Inspect telemetry dicts (print `telemetry_dict["A"].to_dict()` and `telemetry_dict["C"].to_dict()`)
- **Verify:** All canonical fields present (chi_squared, masked_mse, param_deltas, perf_counters, stage_type, mode, engine_protocol, stage_modes)
- **Log:** If schema fields missing, create `blocker_schema.md` with diff against expected schema
- **Return:** Commit partial progress, write blocker summary, return to Galph

## Findings Applied

- **ARCH-ENGINE-002:** Telemetry packaging pattern with asdict() → enrich → reconstruct RefinementTelemetry (applied in engine delegation code, NOT relevant to this fix but context for understanding line 4491-4494)
- **ARCH-ENGINE-003:** Phase E telemetry enrichment pattern (engine_protocol, stage_modes) — mapping fix preserves enrichment while restoring backward-compatible keys
- **PERF-WARM-013:** Stage C instantiation overhead (addressed by Ralph's Phase D D1-D3 implementation, NOT this loop's scope)
- **POLICY-001:** Environment Freeze — no package installs, code-only fix

## Pointers

- **Engine delegation telemetry construction:** `dbex/nanobrag_refinement.py:4487-4494` (fix location)
- **Test expectations:** `tests/dbex/test_torch_refine_smoke.py:384,859,979-982,1289-1292` (uppercase key assertions)
- **Stage name protocol:** `dbex/refinement/stage.py:23-27` (RefinementStage.name property contract)
- **Phase D detector reuse implementation:** `plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/phase_d_decision.md` (Ralph's code-complete D1-D3 tasks)
- **ARCH-REFINE-FLOW-001 Phase E telemetry enrichment:** `docs/findings.md` ARCH-ENGINE-003 (engine_protocol/stage_modes extension pattern)

## Next Up

After this blocker fix PASSES (both tests PASS):
1. **Phase D full validation suite** (D4 task): Ralph reruns Stage C smokes small+full with `DBEX_SMOKE_TELEMETRY_PATH` rooted at new report directory, captures telemetry JSONs, regenerates stage_c_roi_summary.json, updates TESTING_GUIDE.md/TEST_SUITE_INDEX.md if workflow changed
2. **Phase D closure:** Ralph updates `plans/active/PERF-WARM-SIM-001/implementation.md` Phase D status (D1-D4 COMPLETE), writes phase_d_complete.md decision summary, commits Phase D completion message, returns control to Galph for PERF-WARM-SIM-001 exit criteria review
