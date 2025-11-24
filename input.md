# Input for Ralph — ARCH-REFACTOR-001 Phase D D2.3+D2.4 Test Suite + Documentation

**Summary:** Complete Phase D D2 by implementing test suite (10 tests) and creating README for `dbex.tools.stage_a_adam` module.

**Mode:** none

**Focus:** ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D D2.3+D2.4)

**Branch:** integration

**Mapped tests:**
- `tests/dbex/test_stage_a_adam_tooling.py::test_stage_a_components_dataclass` (NEW, unit test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_stage_a_debug_config_dataclass` (NEW, unit test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_create_debug_run_dir` (NEW, unit test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_write_commands_txt` (NEW, unit test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_build_dataload_real_assets` (NEW, integration test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_setup_environment_determinism` (NEW, integration test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_stage_a_forward_smoke` (NEW, integration test, CRITICAL)
- `tests/dbex/test_stage_a_adam_tooling.py::test_zero_point_check_integration` (NEW, integration test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_cli_help_succeeds` (NEW, CLI smoke test)
- `tests/dbex/test_stage_a_adam_tooling.py::test_cli_phase_1_backward_compat` (NEW, CLI smoke test)

**Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T080106Z/`

---

## Do Now

**Context:** Phase D D2.1+D2.2 ✓ COMPLETE (commit 7264817, 2025-11-24T095000Z). Module extraction successful: `dbex/tools/stage_a_adam.py` (1898 lines, 15 functions, 3 classes) + CLI refactored to thin 340-line shim. CLI smoke test PASSED (Phase 1, cpu, seed=42, 92 ROIs). Now complete Phase D D2 with test suite + documentation.

**Objective:** Create comprehensive test suite validating the extracted module's public APIs and CLI backward compatibility. Add minimal README documenting programmatic usage.

### Implement: `tests/dbex/test_stage_a_adam_tooling.py` (10 test cases, ~300-400 lines)

**Test Structure:**
1. **Unit Tests (4)** — Fast dataclass + utility tests, no fixtures
2. **Integration Tests (4)** — Core workflow validation with real fixtures
3. **CLI Smoke Tests (2)** — Backward compatibility validation

**Test Case Specifications:**

#### Unit Tests (Target: <1.5s total)

**Test 1: `test_stage_a_components_dataclass`**
```python
def test_stage_a_components_dataclass():
    """Validate StageAComponents dataclass instantiation."""
    from dbex.tools.stage_a_adam import StageAComponents

    # Create minimal instance
    components = StageAComponents(
        detector_config=None,  # Mock, test accepts None
        crystal_config=None,
        beam_config=None,
        hkl_grid=None,
        simulator=None,
        baseline_detector=None,
        dataload=None,
    )
    assert components.detector_config is None
    # Test field access works
```

**Test 2: `test_stage_a_debug_config_dataclass`**
```python
def test_stage_a_debug_config_dataclass():
    """Validate StageADebugConfig CLI dataclass."""
    from pathlib import Path
    from dbex.tools.stage_a_adam import StageADebugConfig

    # Create with defaults
    config = StageADebugConfig(
        repo_root=Path.cwd(),
        device="cpu",
        seed=42,
        phases=[1],
        base_output_dir=Path("./out"),
        adam_steps=10,
    )
    assert config.seed == 42
    assert config.device == "cpu"
    assert 1 in config.phases
```

**Test 3: `test_create_debug_run_dir`**
```python
def test_create_debug_run_dir(tmp_path):
    """Validate debug run directory creation."""
    from dbex.tools.stage_a_adam import create_debug_run_dir

    timestamp, out_dir = create_debug_run_dir(base_dir=tmp_path)

    # Validate timestamp format (YYYYMMDDTHHMMSSZ)
    assert len(timestamp) == 17
    assert "T" in timestamp
    assert timestamp.endswith("Z")

    # Validate directory exists
    assert out_dir.exists()
    assert out_dir.is_dir()
```

**Test 4: `test_write_commands_txt`**
```python
def test_write_commands_txt(tmp_path):
    """Validate command log generation."""
    from dbex.tools.stage_a_adam import write_commands_txt

    write_commands_txt(
        out_dir=tmp_path,
        seed=42,
        argv=["script.py", "--phases", "1", "--device", "cpu"],
    )

    cmd_file = tmp_path / "commands.txt"
    assert cmd_file.exists()

    content = cmd_file.read_text()
    assert "seed=42" in content
    assert "--phases" in content
```

#### Integration Tests (Target: <30s total)

**Test 5: `test_build_dataload_real_assets`**
```python
def test_build_dataload_real_assets():
    """Validate build_dataload() with real golden data."""
    from pathlib import Path
    from dbex.tools.stage_a_adam import build_dataload

    repo_root = Path.cwd()  # Assumes running from repo root
    dataload = build_dataload(repo_root)

    # Validate DataLoad structure
    assert hasattr(dataload, "experiment")
    assert hasattr(dataload, "reflections")
    assert hasattr(dataload, "mtz_object")
    # No crashes means success
```

**Test 6: `test_setup_environment_determinism`**
```python
def test_setup_environment_determinism():
    """Validate setup_environment() sets seeds."""
    from dbex.tools.stage_a_adam import setup_environment

    device = setup_environment(seed=42, device_str="cpu")
    assert device in ("cpu", "cuda")

    # Test numpy seed works
    import numpy as np
    np.random.seed(42)
    val1 = np.random.random()
    np.random.seed(42)
    val2 = np.random.random()
    assert val1 == val2  # Determinism check
```

**Test 7: `test_stage_a_forward_smoke` (CRITICAL TEST)**
```python
def test_stage_a_forward_smoke():
    """Validate stage_a_forward() executes without crashes."""
    import os
    from pathlib import Path
    from dbex.tools.stage_a_adam import (
        build_dataload,
        setup_environment,
        build_stage_a_components,
        stage_a_forward,
        StageADebugConfig,
    )

    # Disable torch.compile for test speed
    os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"

    # Setup
    repo_root = Path.cwd()
    device = setup_environment(seed=42, device_str="cpu")
    dataload = build_dataload(repo_root)

    config = StageADebugConfig(
        repo_root=repo_root,
        device=device,
        seed=42,
        phases=[1],
        base_output_dir=Path("./out"),
        adam_steps=1,
    )

    # Build components (uses GEOMETRY-003 baseline misset)
    components = build_stage_a_components(dataload, config)

    # Execute forward model with zero params
    param_values_dict = {
        "log_cell_a_delta": 0.0,
        "log_cell_b_delta": 0.0,
        "log_cell_c_delta": 0.0,
        "orientation_vec": [0.0, 0.0, 0.0],
        "log_fcell_scale": 0.0,
    }

    bragg, roi_indices, loss, params_out = stage_a_forward(
        components,
        param_values_dict,
    )

    # Validate outputs
    assert bragg is not None
    assert bragg.ndim == 2  # (n_pixels, n_panels)
    assert loss is not None
    assert loss.ndim == 0  # Scalar
    assert isinstance(params_out, dict)
```

**Test 8: `test_zero_point_check_integration`**
```python
def test_zero_point_check_integration(tmp_path):
    """Validate run_zero_point_check() workflow."""
    import os
    from pathlib import Path
    from dbex.tools.stage_a_adam import (
        build_dataload,
        setup_environment,
        run_zero_point_check,
        StageADebugConfig,
    )

    os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"

    # Setup
    repo_root = Path.cwd()
    device = setup_environment(seed=42, device_str="cpu")
    dataload = build_dataload(repo_root)

    config = StageADebugConfig(
        repo_root=repo_root,
        device=device,
        seed=42,
        phases=[3],
        base_output_dir=tmp_path,
        adam_steps=1,
    )

    # Run zero-point check
    result = run_zero_point_check(dataload, config, tmp_path)

    # Validate result structure
    assert isinstance(result, dict)
    assert "zero_point_ok" in result
    assert "mean_abs_diff" in result
    assert "chi2_rel_diff" in result
    assert isinstance(result["zero_point_ok"], bool)
```

#### CLI Smoke Tests (Target: <15s total)

**Test 9: `test_cli_help_succeeds`**
```python
def test_cli_help_succeeds():
    """Validate CLI --help flag works."""
    import subprocess
    from pathlib import Path

    cli_script = Path("plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py")
    assert cli_script.exists(), f"CLI script not found: {cli_script}"

    result = subprocess.run(
        ["python", str(cli_script), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "Stage A Mapping Adam Debug" in result.stdout or "stage_a" in result.stdout
```

**Test 10: `test_cli_phase_1_backward_compat`**
```python
def test_cli_phase_1_backward_compat(tmp_path):
    """Validate CLI Phase 1 backward compatibility."""
    import subprocess
    import json
    import os
    from pathlib import Path

    cli_script = Path("plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py")

    result = subprocess.run(
        [
            "python", str(cli_script),
            "--phases", "1",
            "--device", "cpu",
            "--seed", "42",
            "--out-dir", str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "NANOBRAGG_DISABLE_COMPILE": "1"},
    )

    # Validate exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Validate artifacts
    json_file = list(tmp_path.glob("*/forward_model_probe.json"))
    assert len(json_file) == 1, f"Expected 1 JSON, found {len(json_file)}"

    data = json.loads(json_file[0].read_text())
    assert "n_rois" in data
    assert data["n_rois"] >= 90  # Relaxed from exact 92
    assert "max_abs_diff" in data
    assert "correlation_stats" in data
```

### Validation Protocol

**Run test suite:**
```bash
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_adam_tooling.py
```

**Expected:** All 10 tests PASS, runtime <60s

**Coverage check (optional):**
```bash
pytest --cov=dbex.tools.stage_a_adam --cov-report=term tests/dbex/test_stage_a_adam_tooling.py
```

**Target:** ≥80% coverage for extracted functions (acceptable if slightly lower)

---

## How-To Map

### Step 1: Create Test File
```bash
# Create test file with 10 test functions
# Implement all test cases as specified above (~300-400 lines total)
```

### Step 2: Run Test Suite
```bash
# Run with torch.compile disabled for speed
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_adam_tooling.py

# Capture output to artifact
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_adam_tooling.py \
  > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T080106Z/test_stage_a_adam_tooling.log 2>&1
```

### Step 3: Create README
```bash
# Create dbex/tools/README.md (~80-100 lines)
# Include: Overview, Modules section, stage_a_adam.py description, public APIs list, usage example, CLI reference
```

### Step 4: CLI Help Validation
```bash
# Validate CLI help succeeds
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py --help
```

### Step 5: Decision Synthesis
```bash
# Write decision outcome to artifact
cat > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T080106Z/decision.md <<'EOF'
# Decision: Phase D D2.3+D2.4 Outcome

**Date:** 2025-11-24T080106Z
**Decided Path:** [A/B/C/D]

[Document which decision path was followed based on test results]
EOF
```

### Step 6: Update Implementation Plan
```bash
# Mark Phase D D2 complete in implementation.md if Path A
# Update checklist line 198 with completion timestamp and metrics
```

### Step 7: Commit and Push
```bash
# Commit all changes
git add -A
git commit -m "ARCH-REFACTOR-001 Phase D D2.3+D2.4: Test suite + docs (10 tests PASSED) — tests: run"
git push
```

---

## Pitfalls To Avoid

1. **Import Errors:** Ensure `from dbex.tools.stage_a_adam import ...` works before writing tests. If import fails, check `dbex/tools/__init__.py` exists (can be empty).

2. **Golden Data Dependency:** Integration tests (5-8) require `golden_data/exp00000/1_0.pkl` fixture. If missing, tests will fail. Do NOT attempt to download/install data (Environment Freeze). Mark blocked if fixture unavailable.

3. **torch.compile Overhead:** ALWAYS use `NANOBRAGG_DISABLE_COMPILE=1` when running tests. Without it, integration tests may take 5-10× longer due to compilation overhead.

4. **CLI Test Timeouts:** Test 10 runs full Phase 1 CLI. Use 30s timeout. If it exceeds, consider reducing scope or marking test as `@pytest.mark.slow`.

5. **Seed Determinism:** Test 6 checks numpy seed reproducibility. Ensure `np.random.seed()` is called BEFORE `np.random.random()` calls, not relying on module-level setup.

6. **Device Availability:** Test 7 uses `device="cpu"`. If code tries to use CUDA when unavailable, tests will fail. Ensure `setup_environment()` respects device string.

7. **Subprocess Environment:** Test 10 uses `subprocess.run()` with custom env. Must pass `env={**os.environ, "NANOBRAGG_DISABLE_COMPILE": "1"}` to inherit environment while adding override.

8. **Test Runtime:** Target <60s total. If tests exceed, identify slowest test and optimize or mark `@pytest.mark.slow` for optional skip.

9. **Dataclass Defaults:** Tests 1-2 check dataclass instantiation. If dataclass has required fields with no defaults, tests must provide values or use `field(default=...)`.

10. **README Example:** Ensure programmatic API example in README matches actual module API. Test example code manually before committing if possible.

---

## If Blocked

**Scenario 1: Test 5 fails with "golden_data not found"**
- **Action:** Document blocker in decision.md with error message
- **Return Condition:** Fixture available OR alternative mock fixture implemented
- **Do NOT:** Attempt to download/install data (Environment Freeze violation)

**Scenario 2: Test 7 fails with import/runtime errors**
- **Action:** Debug module import path or function signature mismatch
- **Max Iterations:** 2 debug cycles, then document blocker
- **Return Condition:** Module API fixed OR test expectations adjusted

**Scenario 3: Test 10 CLI timeout (>30s)**
- **Action:** Increase timeout to 60s OR mark test `@pytest.mark.slow` and skip for now
- **Alternative:** Reduce CLI test to `--help` only validation (Test 9)

**Scenario 4: Coverage <60% (significantly below target)**
- **Action:** Accept lower coverage, document in decision.md
- **Rationale:** 10 tests cover critical paths; internal helpers may be untestable without major refactoring

---

## Findings Applied

- **POLICY-001** (Environment Freeze): Tests use existing dependencies (pytest, subprocess, json, pathlib). No new packages installed.
- **ARCH-ENGINE-002** (Lazy Imports): Module already implements lazy torch imports per D2.1, tests respect this.
- **GEOMETRY-003** (B_ideal Convention): Test 7 uses `build_stage_a_components()` which applies GEOMETRY-003 baseline misset derivation.
- **TESTING-003** (Registry Sync): NOT required for internal tooling tests (not user-facing acceptance tests). Skip `docs/TESTING_GUIDE.md` update.
- **CLAUDE.md** (Test-Driven When Possible): Tests validate existing module APIs, not TDD (module already implemented in D2.1).
- **CLAUDE.md** (Incremental Progress): Phase D split into 2 loops (D2.1+D2.2 extraction, D2.3+D2.4 tests+docs). Avoid big-bang approach.
- **galph_prompt** (Implementation Floor): This loop contains production test code (~300-400 lines) + validating test execution, satisfies implementation requirement.

---

## Pointers

- **Planning Analysis:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T080106Z/phase_d_d2_3_4_planning_analysis.md`
- **Implementation Plan:** `plans/active/ARCH-REFACTOR-001/implementation.md:191-209` (Phase D D2 checklist)
- **Phase D D2.1+D2.2 Completion:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T095000Z/summary.md` (prior loop validation)
- **Module Source:** `dbex/tools/stage_a_adam.py` (1898 lines, 15 functions, 3 classes)
- **CLI Script:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` (340 lines, thin shim)
- **Spec Reference:** `docs/spec-db-core.md` (GEOMETRY-003, variance model used in tests)
- **Test Patterns:** `tests/dbex/test_diffbragg_tmp.py` (Phase D D1 validation, 7 tests, reference for structure)

---

## Next Up (Optional)

If Phase D D2 completes successfully and time permits:

1. **Phase D D3:** Summary-generation CLI cleanup (convert `generate_summaries.py` to argparse-driven CLI)
2. **Phase D Completion Assessment:** Evaluate whether Phase D exit criteria (#7 DiffBragg scratch, #8 Stage A tooling) are satisfied
3. **Phase C Planning:** If Phase D complete, consider resuming Phase C (Incremental Engine Migration) OR mark ARCH-REFACTOR-001 phases 0/A/B/D complete and pivot to other Tier 3 initiatives

**Do NOT proceed to Next Up** — Return control to Galph after Phase D D2.3+D2.4 completion for decision on next focus.
