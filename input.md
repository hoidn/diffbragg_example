# Phase E: Orchestration Hooks & Mode Wiring (ARCH-REFINE-FLOW-001)

## Summary
Implement engine delegation hooks in run_nanobrag_refinement + CLI flags for stage control, validate engine-based protocol as default path, complete Phase E with all exit criteria met.

## Mode
**none** (production code + validation)

## Focus
**ARCH-REFINE-FLOW-001** — Protocol-based Refinement Engine (Phase E: Orchestration Hooks & Mode Wiring)

## Branch
`integration`

## Mapped Tests
**Active selectors (validation):**
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (Stage A engine path)
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (Stage B engine path, small detector)
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (Stage C engine path, small detector)
- `pytest -v tests/dbex/test_mapping_consistency.py::test_db_at_024_mapping_fidelity` (DB-AT-024 mapping parity, zero-iteration path unaffected by engine delegation)

**Note:** All 4 selectors must PASS with engine delegation enabled. Small detector tests validate engine path correctness; DB-AT-024 confirms zero-iteration forward model unchanged.

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/`
- `phase_e_decision.md` (4-path decision synthesis: A=all PASS → Phase E COMPLETE, B/C/D=smoke/CLI/DB-AT-024 failures)
- `phase_e_metrics.json` (4 test statuses, engine_protocol strings, stage_modes dicts per run)
- `pytest_stage_a_engine.log`, `pytest_stage_b_engine.log`, `pytest_stage_c_engine.log`, `pytest_db_at_024_engine.log`
- `summary.md` (Turn Summary block per end-of-loop hygiene)

## Do Now

**Objective:** Complete Phase E (Orchestration Hooks & Mode Wiring) in a single loop by implementing engine delegation logic, CLI flags, telemetry tagging, and validating all smoke tests + DB-AT-024 pass with the engine-based protocol.

**Context:** Phase D COMPLETE (commit 3c856ef, all Stage A/B/C wrappers production-ready, telemetry schema validated, regression guards clean). Phase E integrates the engine delegation layer so future stage variants (per-reflection Stage B, alternative sequences) can be configured via CLI/config flags without editing inline code.

### Step-by-Step Protocol (12 steps)

#### **E1: Add engine telemetry fields to RefinementTelemetry**

1. Open `dbex/nanobrag_refinement.py` and locate the RefinementTelemetry dataclass (line ~392)
2. Add two new Optional fields AFTER existing fields (maintain backward compatibility):
   ```python
   engine_protocol: Optional[str] = None  # e.g., "A→B→C", "A-only", "A→B"
   stage_modes: Optional[Dict[str, str]] = None  # e.g., {"B": "shell", "C": "detector_offsets"}
   ```
3. Save file

#### **E2: Update run_nanobrag_refinement signature with use_engine_delegation flag**

4. Locate `run_nanobrag_refinement` function definition (line ~3706)
5. Add new parameter to signature BEFORE the closing `)`:
   ```python
   use_engine_delegation: bool = False
   ```
6. Update docstring to document the new parameter:
   ```
   use_engine_delegation: bool, default False
       When True, delegates to RefinementEngine with Stage wrapper classes.
       When False (default), uses inline helper paths for backward compatibility.
   ```
7. Save file

#### **E3: Implement engine delegation branch in run_nanobrag_refinement**

8. Locate the end of Stage A execution (after line ~4200, before Stage B inline check)
9. Insert engine delegation branch BEFORE the existing `if config.enable_stage_b:` check:
   ```python
   # === ENGINE DELEGATION PATH (Phase E) ===
   if use_engine_delegation:
       # Lazy imports to avoid circular dependencies
       from dbex.refinement.engine import RefinementEngine
       from dbex.refinement.stage_a import StageA
       from dbex.refinement.stage_b import StageB
       from dbex.refinement.stage_c import StageC

       # Construct stage list based on config flags
       stages = []
       stages.append(StageA())  # Stage A always runs

       if config.enable_stage_b:
           # Guard: Stage B requires baseline_detector
           if baseline_detector is None:
               raise ValueError(
                   "Stage B via engine requires baseline_detector parameter. "
                   "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
               )
           stages.append(StageB())

       if config.enable_stage_c:
           # Guard: Stage C requires baseline_detector
           if baseline_detector is None:
               raise ValueError(
                   "Stage C via engine requires baseline_detector parameter. "
                   "Pass the baseline dxtbx Detector object to run_nanobrag_refinement()."
               )
           stages.append(StageC())

       # Build engine protocol string for telemetry
       stage_names = [s.name for s in stages]
       engine_protocol = "→".join(stage_names)  # e.g., "A→B→C", "A", "A→B"

       # Build stage_modes dict for telemetry
       stage_modes = {}
       if config.enable_stage_b:
           stage_modes["B"] = "shell"  # Currently only shell mode; per-reflection deferred to TORCH-REFINE-004
       if config.enable_stage_c:
           stage_modes["C"] = "detector_offsets"

       # Prepare RefinementInputs for engine
       engine_inputs = {
           "target": inputs.target,
           "loss_mask": inputs.loss_mask,
           "panel_slices": inputs.panel_slices,
           "trusted_mask": inputs.trusted_mask,
           "detector": detector,
           "beam": beam,
           "crystal": crystal,
           "hkl_grid": hkl_grid,
           "hkl_metadata": hkl_metadata,
           "baseline_crystal": baseline_crystal,
           "baseline_detector": baseline_detector,
       }

       # Execute engine
       engine = RefinementEngine(stages=stages, config=config)
       engine_telemetry = engine.run(inputs=engine_inputs, telemetry_sink=None)

       # Extract final Bragg from last stage telemetry
       last_stage_name = stage_names[-1]
       final_telemetry_dict = engine_telemetry[last_stage_name]
       final_bragg = final_telemetry_dict["final_bragg"]

       # Enrich telemetry with engine protocol + stage modes
       telemetry_out = {}
       for stage_name, telem_dict in engine_telemetry.items():
           # Add engine fields to each stage's telemetry
           telem_dict["engine_protocol"] = engine_protocol
           telem_dict["stage_modes"] = stage_modes
           telemetry_out[stage_name] = RefinementTelemetry(**telem_dict)

       return final_bragg, telemetry_out

   # === INLINE HELPER PATH (backward compatibility) ===
   # (existing Stage B/C inline code continues below)
   ```
10. Ensure proper indentation (4 spaces per level, no tabs)
11. Save file

#### **E4: Add CLI flags to refine_one.py**

12. Open `dbex/refine_one.py`
13. Locate the argument parser setup (search for `argparse.ArgumentParser`)
14. Add three new optional arguments AFTER existing refinement args:
    ```python
    parser.add_argument(
        "--use-engine-delegation",
        action="store_true",
        default=False,
        help="Use RefinementEngine with Stage wrapper classes instead of inline helpers"
    )
    parser.add_argument(
        "--enable-stage-b",
        action="store_true",
        default=False,
        help="Enable Stage B Fhkl shell modifiers (requires --use-engine-delegation)"
    )
    parser.add_argument(
        "--enable-stage-c",
        action="store_true",
        default=False,
        help="Enable Stage C detector distance refinement (requires --use-engine-delegation)"
    )
    ```
15. Locate RefinementConfig instantiation (search for `RefinementConfig(`)
16. Update config construction to pass CLI flags:
    ```python
    config = RefinementConfig(
        # ... existing parameters ...
        enable_stage_b=args.enable_stage_b,
        enable_stage_c=args.enable_stage_c,
    )
    ```
17. Locate `run_nanobrag_refinement` call site
18. Add `use_engine_delegation` parameter to the call:
    ```python
    final_bragg, telemetry = run_nanobrag_refinement(
        # ... existing parameters ...
        use_engine_delegation=args.use_engine_delegation
    )
    ```
19. Save file

#### **E5: Run Stage A smoke with engine delegation**

20. Execute Stage A smoke test:
    ```bash
    pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_a_engine.log 2>&1
    echo "Stage A exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_a_engine.log
    ```
21. Check exit code: `grep "exit code" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_a_engine.log`
22. If exit code ≠ 0, STOP and log blocker in decision.md (Path B: engine delegation smoke failure)

#### **E6: Run Stage B smoke (small detector) with engine delegation**

23. Update test_stage_b_shell_modifiers to enable engine delegation:
    - Locate the test in `tests/dbex/test_torch_refine_smoke.py` (line ~876)
    - Find the `run_nanobrag_refinement` call
    - Add `use_engine_delegation=True` parameter
24. Execute Stage B smoke test:
    ```bash
    pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_b_engine.log 2>&1
    echo "Stage B exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_b_engine.log
    ```
25. Check exit code
26. If exit code ≠ 0, STOP and log blocker (Path B)

#### **E7: Run Stage C smoke (small detector) with engine delegation**

27. Update test_stage_c_detector_microslip to enable engine delegation:
    - Locate the test (line ~780)
    - Add `use_engine_delegation=True` parameter to run_nanobrag_refinement call
28. Execute Stage C smoke test:
    ```bash
    pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_c_engine.log 2>&1
    echo "Stage C exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_stage_c_engine.log
    ```
29. Check exit code
30. If exit code ≠ 0, STOP and log blocker (Path B)

#### **E8: Run DB-AT-024 mapping parity check**

31. Execute DB-AT-024 test (zero-iteration forward model, does NOT use engine):
    ```bash
    pytest -v tests/dbex/test_mapping_consistency.py::test_db_at_024_mapping_fidelity > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_db_at_024_engine.log 2>&1
    echo "DB-AT-024 exit code: $?" >> plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/pytest_db_at_024_engine.log
    ```
32. Check exit code
33. If exit code ≠ 0, STOP and log blocker (Path D: DB-AT-024 regression)

#### **E9: Generate phase_e_metrics.json**

34. Create metrics JSON using Python one-liner:
    ```bash
    python3 -c "
import json
from pathlib import Path

artifacts = Path('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z')

def get_exit_code(log_path):
    content = Path(log_path).read_text()
    for line in content.split('\\n'):
        if 'exit code:' in line.lower():
            return int(line.split(':')[-1].strip())
    return -1

metrics = {
    'stage_a_engine_exit_code': get_exit_code(artifacts / 'pytest_stage_a_engine.log'),
    'stage_b_engine_exit_code': get_exit_code(artifacts / 'pytest_stage_b_engine.log'),
    'stage_c_engine_exit_code': get_exit_code(artifacts / 'pytest_stage_c_engine.log'),
    'db_at_024_exit_code': get_exit_code(artifacts / 'pytest_db_at_024_engine.log'),
    'all_tests_passed': all([
        get_exit_code(artifacts / 'pytest_stage_a_engine.log') == 0,
        get_exit_code(artifacts / 'pytest_stage_b_engine.log') == 0,
        get_exit_code(artifacts / 'pytest_stage_c_engine.log') == 0,
        get_exit_code(artifacts / 'pytest_db_at_024_engine.log') == 0,
    ]),
    'engine_protocol_examples': {
        'stage_a_only': 'A',
        'stage_a_b': 'A→B',
        'stage_a_b_c': 'A→B→C'
    },
    'stage_modes': {
        'B': 'shell',
        'C': 'detector_offsets'
    }
}

with open(artifacts / 'phase_e_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print('Metrics written to phase_e_metrics.json')
" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/metrics_generation.log
    ```

#### **E10: Synthesize decision.md with 4-path template**

35. Write decision synthesis to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/phase_e_decision.md`:
    - Load phase_e_metrics.json
    - If `all_tests_passed == true`: **Path A** (all PASS → Phase E COMPLETE, ARCH-REFINE-FLOW-001 ready for Tier 2 closure)
    - If Stage A/B/C smoke failure: **Path B** (debug engine delegation, compare inline vs engine telemetry, check StageA/B/C.run() wiring)
    - If CLI flag parsing failure: **Path C** (verify argparse integration, RefinementConfig hydration, use_engine_delegation propagation)
    - If DB-AT-024 regression: **Path D** (rollback engine delegation changes, escalate to Galph with blocker report)
    - Include confidence level (HIGH ~95% if Path A, MEDIUM ~60% if Path B/C/D)
    - Document next actions per path

#### **E11: Update implementation.md Phase E checklist**

36. Open `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
37. Locate Phase E section (line ~274)
38. Mark all E1-E5 tasks as complete:
    ```markdown
    - [x] E1: Expose stage registry/config knobs ✓ COMPLETE (2025-11-23T160000Z)
    - [x] E2: Update CLI/config surfaces ✓ COMPLETE
    - [x] E3: Add telemetry fields (engine_protocol, stage_modes) ✓ COMPLETE
    - [x] E4: Update architecture docs ✓ DEFERRED (docs-only cleanup for next loop if Path A)
    - [x] E5: Run combined smoke suite + DB-AT selectors ✓ COMPLETE
    ```
39. Add Phase E completion timestamp and status:
    ```markdown
    **Phase E Status: ✓ COMPLETE (2025-11-23T160000Z)** [if Path A]
    ```
40. Save file

#### **E12: Write summary.md with Turn Summary block**

41. Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T160000Z/summary.md` with:
    - **Turn Summary** (3-5 sentences):
      - What shipped (engine delegation logic, CLI flags, telemetry tagging)
      - Main problem and resolution (engine path validation, backward compatibility preserved)
      - Next step (Phase E complete if Path A, debug/escalate if Path B/C/D)
    - **Artifacts:** (point to this directory + key files)

#### **E13: Commit and push**

42. Stage all changes:
    ```bash
    git add -A
    ```
43. Commit with message:
    ```bash
    git commit -m "ARCH-REFINE-FLOW-001 Phase E: Orchestration Hooks + Engine Delegation — tests: Stage A/B/C+DB-AT-024 [PASS/FAIL per decision.md]"
    ```
44. Push to remote:
    ```bash
    git push
    ```

## How-To Map

### Engine Delegation Logic Wiring
```python
# Insert at dbex/nanobrag_refinement.py line ~4200 BEFORE existing Stage B check
if use_engine_delegation:
    from dbex.refinement.engine import RefinementEngine
    from dbex.refinement.stage_a import StageA
    from dbex.refinement.stage_b import StageB
    from dbex.refinement.stage_c import StageC

    stages = [StageA()]
    if config.enable_stage_b:
        if baseline_detector is None:
            raise ValueError("Stage B requires baseline_detector")
        stages.append(StageB())
    if config.enable_stage_c:
        if baseline_detector is None:
            raise ValueError("Stage C requires baseline_detector")
        stages.append(StageC())

    engine_protocol = "→".join([s.name for s in stages])
    stage_modes = {}
    if config.enable_stage_b: stage_modes["B"] = "shell"
    if config.enable_stage_c: stage_modes["C"] = "detector_offsets"

    engine_inputs = {
        "target": inputs.target, "loss_mask": inputs.loss_mask,
        "panel_slices": inputs.panel_slices, "trusted_mask": inputs.trusted_mask,
        "detector": detector, "beam": beam, "crystal": crystal,
        "hkl_grid": hkl_grid, "hkl_metadata": hkl_metadata,
        "baseline_crystal": baseline_crystal, "baseline_detector": baseline_detector
    }

    engine = RefinementEngine(stages=stages, config=config)
    engine_telemetry = engine.run(inputs=engine_inputs, telemetry_sink=None)

    last_stage_name = [s.name for s in stages][-1]
    final_bragg = engine_telemetry[last_stage_name]["final_bragg"]

    telemetry_out = {}
    for stage_name, telem_dict in engine_telemetry.items():
        telem_dict["engine_protocol"] = engine_protocol
        telem_dict["stage_modes"] = stage_modes
        telemetry_out[stage_name] = RefinementTelemetry(**telem_dict)

    return final_bragg, telemetry_out
```

### CLI Integration (refine_one.py)
```python
# Add to argparse setup:
parser.add_argument("--use-engine-delegation", action="store_true", default=False,
                    help="Use RefinementEngine with Stage wrappers")
parser.add_argument("--enable-stage-b", action="store_true", default=False,
                    help="Enable Stage B shell modifiers")
parser.add_argument("--enable-stage-c", action="store_true", default=False,
                    help="Enable Stage C detector refinement")

# Update RefinementConfig:
config = RefinementConfig(
    # ... existing ...
    enable_stage_b=args.enable_stage_b,
    enable_stage_c=args.enable_stage_c
)

# Update run_nanobrag_refinement call:
final_bragg, telemetry = run_nanobrag_refinement(
    # ... existing ...
    use_engine_delegation=args.use_engine_delegation
)
```

### Test Updates (inline only, no new test files)
```python
# In tests/dbex/test_torch_refine_smoke.py
# Locate each test's run_nanobrag_refinement call and add:
final_bragg, telemetry = run_nanobrag_refinement(
    # ... existing parameters ...
    use_engine_delegation=True  # ADD THIS LINE
)
```

### Validation Commands
```bash
# Stage A smoke
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > pytest_stage_a_engine.log 2>&1

# Stage B smoke (small detector)
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers > pytest_stage_b_engine.log 2>&1

# Stage C smoke (small detector)
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip > pytest_stage_c_engine.log 2>&1

# DB-AT-024 mapping parity (zero-iteration, engine-independent)
pytest -v tests/dbex/test_mapping_consistency.py::test_db_at_024_mapping_fidelity > pytest_db_at_024_engine.log 2>&1
```

## Pitfalls To Avoid

1. **Lazy Imports:** Stage wrapper classes (StageA/StageB/StageC) MUST be imported inside the `if use_engine_delegation:` branch to avoid circular dependencies. Do NOT import at module level.

2. **Backward Compatibility:** `use_engine_delegation=False` is the default. Existing tests and CLI workflows must continue working without changes (inline helper paths preserved).

3. **Telemetry Structure:** Engine telemetry dicts MUST contain exact same keys as inline path (chi_squared, masked_mse, param_deltas, final_bragg). Wrapper classes already implement this per Phase D validation.

4. **Baseline Detector Guards:** StageB and StageC wrappers require `baseline_detector` input (NOT optional). Raise clear ValueError if None when stage enabled.

5. **DB-AT-024 Independence:** Zero-iteration mapping test (`test_db_at_024_mapping_fidelity`) does NOT use refinement engine. It validates forward model only. Do NOT add engine delegation to this test.

6. **Engine Protocol String:** Format must be `"A→B→C"` (arrow character U+2192, not "->"). Use `"→".join(stage_names)` for correct formatting.

7. **Stage Modes Dict:** Keys are uppercase stage letters ("A", "B", "C"). Values are lowercase mode strings ("shell", "detector_offsets", "per_reflection" future).

8. **Test Updates In-Place:** Do NOT create new test files. Update existing smoke tests (`test_stage_a_expansion`, `test_stage_b_shell_modifiers`, `test_stage_c_detector_microslip`) by adding `use_engine_delegation=True` parameter to their `run_nanobrag_refinement` calls.

9. **RefinementConfig Defaults:** `enable_stage_b` and `enable_stage_c` remain `False` by default (lines 301/310 in nanobrag_refinement.py). Only change when user passes CLI flags.

10. **Indentation:** Python code uses 4 spaces per indent level (NO tabs). Verify indentation with `python3 -m py_compile` before running tests.

## If Blocked

**Scenario 1: Engine delegation smoke test fails (Path B)**
- Capture full error traceback in `phase_e_decision.md`
- Compare inline vs engine telemetry side-by-side (extract from pytest logs)
- Check StageA/B/C.run() return structure matches RefinementTelemetry schema
- Verify lazy imports resolve correctly
- Log blocker with hypothesis (telemetry packaging, stage wiring, imports)
- Set decision path to B and commit blocker artifacts

**Scenario 2: CLI flag parsing fails (Path C)**
- Verify argparse.ArgumentParser setup in refine_one.py
- Check args.use_engine_delegation propagates to run_nanobrag_refinement call
- Confirm RefinementConfig accepts enable_stage_b/enable_stage_c parameters
- Test CLI manually: `python -m dbex.refine_one --help` (should show new flags)
- Log blocker with error message + stack trace
- Set decision path to C

**Scenario 3: DB-AT-024 regression (Path D)**
- Confirm DB-AT-024 test does NOT call engine (zero-iteration mapping only)
- If test passes without engine changes, proceed with Path A
- If test fails, check if any shared code (nanobrag_bridge, data_load) was modified
- Rollback engine delegation changes if necessary
- Escalate to Galph with blocker report (include pytest log, error signature)
- Set decision path to D

**Scenario 4: Compilation error (unlisted)**
- Run `python3 -m py_compile dbex/nanobrag_refinement.py`
- Fix syntax errors (indentation, missing colons, unclosed brackets)
- Re-run py_compile until clean
- Restart from Step E5

## Findings Applied

**Mandatory (cite these in decision.md):**

- **ARCH-ENGINE-002** (Stage wrapper pattern): Adhering to lazy imports inside run() method, telemetry packaging via asdict→enrich→reconstruct pattern, protocol interface compliance.

- **REFINE-007/REFINE-007-EXT** (Stage C detector gates): Engine path preserves ≥80% offset reduction OR ≤±0.05mm final, ≤0.05% χ² regression gates validated in Phase D.

- **REFINE-008** (Stage B shell gates): Engine path preserves ≤1e-6 χ² regression, ±1% modifier deltas gates validated in Phase D.

- **POLICY-001** (Environment Freeze): Code-only integration, no package installs, no env modifications. Engine delegation is pure Python refactoring.

- **TESTING-003** (Registry sync): Test registry updates (TESTING_GUIDE.md, TEST_SUITE_INDEX.md) deferred to docs-only loop after Phase E validation (per implementation.md:278 "E4: Update docs... annotations").

- **GRADIENT-003** (CPU fallback deferred): Stage B full detector uses CUDA-only path (CPU fallback HKL grid transfer bug documented, Phase C2.5 decision Path C). Engine delegation does not change device routing logic.

**Optional (relevant context):**

- **PERF-WARM-001/006/011/012** (Warm cache patterns): Engine path reuses StageAContext warm cache per Phase B/C/D wrapper implementations.

- **PHYSICS-LOSS-001/002** (Variance-weighted loss): Engine path preserves dual metrics (chi_squared + masked_mse) per Stage A/B/C wrapper telemetry packaging.

- **CONFORMANCE-001** (DB-AT environment flags): DB-AT-024 requires `KMP_DUPLICATE_LIB_OK=TRUE` env flag (already set in test harness).

## Pointers

**Spec/Arch Docs:**
- `docs/spec-db-workflow.md:33` (Engine Contract: ordered stages, no hardcoded A→B→C)
- `docs/spec-db-tracing.md` §2 (Telemetry aggregation requirements)
- `docs/architecture/pytorch_design.md` (Phase E section deferred to E4 docs-only update)
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:274-283` (Phase E tasks E1-E5)

**Fix Plan:**
- `docs/fix_plan.md` [ARCH-REFINE-FLOW-001] row (line ~185)
- Tier 2 roadmap (line ~26-29): "Break monolithic run_nanobrag_refinement into maintainable Protocol Engine"

**Findings:**
- `docs/findings.md` row 70 (ARCH-ENGINE-002: Stage wrapper pattern)
- `docs/findings.md` row 71 (REFINE-007-EXT: Stage C validation methodology)

**Test Registry:**
- `docs/TESTING_GUIDE.md` §2.1 (Active selectors, will be updated in E4 docs-only loop)
- `docs/development/TEST_SUITE_INDEX.md` (Stage smoke + DB-AT-024 entries)

**Phase D Evidence:**
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/phase_d3_d5_decision.md` (All Phase D validation gates PASSED)
- `dbex/refinement/stage_a.py`, `dbex/refinement/stage_b.py`, `dbex/refinement/stage_c.py` (Wrapper implementations)
- `dbex/refinement/engine.py` (Engine skeleton, Phase A nucleus TDD)

## Next Up (Optional)

**If Path A (all tests PASS):**
1. **Phase E docs-only cleanup** (E4): Update `docs/architecture/pytorch_design.md` with engine delegation section, `docs/TESTING_GUIDE.md` Phase E completion note, `docs/spec-db-workflow.md` annotations.
2. **ARCH-REFINE-FLOW-001 closure**: Mark initiative as `done` in `docs/fix_plan.md`, archive all Phase A-E artifacts, update Execution Roadmap Tier 2 status.
3. **Tier 3 readiness**: Unblock TORCH-REFINE-004 (Stage B per-reflection mode) per `docs/fix_plan.md:33` guardrail ("Deferred until ARCH-REFINE-FLOW-001 Phase E complete").

**If Path B/C/D (failures):**
- Debug engine delegation logic, compare inline vs engine telemetry, fix wiring/imports.
- Escalate to Galph with comprehensive blocker report (error signatures, hypotheses, attempted fixes).
- Do NOT proceed to docs updates until all 4 tests pass.

## Doc Sync Plan
**Deferred to next loop (E4 docs-only cleanup) per FSM implementation floor rule.**

After Path A confirmation (all 4 tests PASS), next Galph loop will delegate docs-only tasks:
- Update `docs/architecture/pytorch_design.md` (Engine Delegation section with phase summary + usage examples)
- Update `docs/TESTING_GUIDE.md` §2.1 (Phase E completion note: "Engine delegation validated 2025-11-23T160000Z")
- Update `docs/spec-db-workflow.md` (Annotations linking to Phase E artifacts)
- Archive `pytest --collect-only` logs for updated selectors (if any test signatures changed)
- Update `docs/development/TEST_SUITE_INDEX.md` (no new tests, but document engine delegation parameter availability)

**Rationale:** Docs updates are non-blocking hygiene; code validation must complete first. Splitting into separate loop maintains implementation floor discipline (max 1 docs-only loop per focus) and enables clean Path A verification before final documentation.
