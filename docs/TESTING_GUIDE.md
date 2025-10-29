# DBEX Testing Guide

This guide standardizes how agents run and author tests for the DiffBragg → `nanobrag_torch` integration work.

## 1. Environments & Flags

### 1.1 Required Environment Variables

**All PyTorch-based tests require:**

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

- **Rationale**: Prevents conflicts when PyTorch loads both MKL and system BLAS libraries. Without this flag, tests may fail with "OMP: Error #15: Initializing libiomp5.so, but found libiomp5.so already initialized."
- **Spec Reference**: `docs/spec-db-runtime.md:18-21`, `docs/spec-db-conformance.md:28`
- **Scope**: Export before any `pytest` invocation that imports torch or dbex modules

**Gradient/gradcheck tests additionally require:**

```bash
export NANOBRAGG_DISABLE_COMPILE=1
```

- **Rationale**: `torch.compile` creates donated buffers that interfere with `torch.autograd.gradcheck` numerical gradient computation. Symptoms include non-deterministic failures or incorrect gradient values.
- **Spec Reference**: `docs/pytorch_runtime_checklist.md:26`, `docs/development/testing_strategy.md:1.6`
- **Scope**: Only required for tests using `torch.autograd.gradcheck` or marked `@pytest.mark.gradcheck`
- **See Also**: `docs/development/testing_strategy.md` §4.1 for full gradient test execution requirements

### 1.2 Installation Requirements

- Prefer editable installs: `pip install -e .` from the repo root to ensure CLI entry points resolve correctly
- Verify environment before running tests:
  ```bash
  python -c "import dbex; import torch; print(f'dbex loaded, torch {torch.__version__}')"
  ```

### 1.3 Quick Reference Commands

**Standard test run (smoke/integration):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/
```

**Gradient tests:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests -k gradcheck
```

**Determinism tests (CPU-only, see §2.7 in testing_strategy.md):**
```bash
CUDA_VISIBLE_DEVICES='' TORCHDYNAMO_DISABLE=1 NANOBRAGG_DISABLE_COMPILE=1 \
  KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_013
```

## 2. Test Taxonomy

| Scope | Selector | Purpose | Status | Notes |
| --- | --- | --- | --- | --- |
| Smoke | `python -m dbex.refine_one --help` | Verifies legacy CLI loads after environment changes. | Active | Run before/after backend refactors. |
| Torch parity | `pytest -v tests -k DB_AT_001` | Validates simple cubic parity (`docs/spec-db-conformance.md:24`). | Planned | Requires golden data; correlation ≥0.99. |
| Determinism | `pytest -v tests -k DB_AT_002` | Bitwise/tolerance equality with locked RNG seeds. | Planned | See `docs/development/testing_strategy.md` §2.7 for environment. |
| Reflection ingestion | `pytest -v tests -k DB_AT_020` | DIALS reflection ingestion + bbox semantics (`docs/spec-db-conformance.md:30`). | Planned | Blocks CLI parity work. |
| Mask semantics | `pytest -v tests -k DB_AT_021` | Trusted-mask polarity per `docs/spec-db-core.md:51`. | Planned | Author targeted fixtures when masks land. |
| Background semantics | `pytest -v tests -k DB_AT_022` | Validates −1 sentinel handling around ROIs. | Planned | Per `docs/spec-db-conformance.md:38`. |
| Calibration | `pytest -v tests -k DB_AT_023` | Ensures ADU vs photons policy behaves per spec. | Planned | Requires adu_per_photon fixtures. |
| Mapping sanity | `pytest -v tests -k DB_AT_024` | Zero-iteration forward pass overlaps data within tolerance. | Planned | Logs metrics for validation. |
| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | Equal-weight source handling and vectorized loops (`docs/pytorch_runtime_checklist.md:31`). | Planned | Currently in `nanoBragg2/tests/`; port to DBEX. |

**Note**: Tests marked "Planned" must be authored before declaring their parent fix-plan items complete. Record TODO entries in `docs/fix_plan.md` with the relevant selector. See also `docs/development/TEST_SUITE_INDEX.md` for synchronized selector registry.

### 2.1 Active Implementation Coverage (module selectors)

Until DB_AT acceptance marks/selectors are fully migrated, use these concrete module selectors to drive implementation loops. Keep this list synchronized with `docs/development/TEST_SUITE_INDEX.md`.

| Module / Area | Selector | Status | Spec Reference | Notes |
| --- | --- | --- | --- | --- |
| Bridge tensors & masks | `pytest -v tests/dbex/test_nanobrag_bridge.py` | Active | `docs/spec-db-core.md:20`, `docs/config_crosswalk.md:86-95` | Verifies [panel, slow, fast], mask polarity, background semantics.
| Config hydration | `pytest -v tests/dbex/test_nanobrag_bridge_configs.py` | Active | `docs/config_crosswalk.md:15-72`, `docs/dxtbx_api.md:17-41` | Detector CUSTOM mapping, beam wavelength/polarization, crystal A*.
| Smoke harness | `pytest -v tests/dbex/test_nanobrag_smoke.py` | Active | `docs/spec-db-workflow.md:24-29`, `docs/dials_api.md:10-28` | Single-experiment flow, stitched Bragg, masked MSE, artifacts.

#### Selector Compliance Check (artifacted)

Run `--collect-only` for each selector and save logs under the current loop’s artifacts directory (see `input.md` Artifacts path):

```bash
ART=plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>
mkdir -p "$ART"
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_bridge.py | tee "$ART/collect_bridge.log"
KMP_DUPLICIATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_bridge_configs.py | tee "$ART/collect_configs.log"
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_nanobrag_smoke.py | tee "$ART/collect_smoke.log"
```

Mark a selector "Active" only when collection > 0. Keep DB_AT entries as "Planned" until marks/selectors are implemented.

#### Status Semantics (enforced)

- Active: Documented selector must collect > 0 tests via `pytest --collect-only`. If collection == 0, either downgrade to Planned (with rationale) or author the missing tests before closing the loop.
- Planned: Selector may collect 0; include a rationale and the initiative slated to add it. Convert to Active once tests exist and collection > 0 with logs artifacted.

## 3. Artifact Policy
- Store `pytest` logs, parity metrics, and trace outputs in a documented location per initiative (e.g., `plans/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/`).
- Reference the artifact path (log, summary, metrics.json) in the fix plan Attempts History entry that triggered the run.

## 4. Reporting Checklist
- Include command, exit code, and runtime.
- Record hardware context (CPU/GPU) and dtype if deviating from defaults.
- For parity tests, capture correlation, MSE, RMSE, max|Δ|, and sum ratios (see `docs/spec-db-tracing.md`).
- If a required selector is missing, file a TODO under the relevant fix-plan item and capture repro notes in the artifact directory.

## 5. Evidence & Skip Policy (strict)
- Attach a `pytest.log` with command, exit code, and counts (passed/failed/skipped). SKIPs MUST be justified: GPU‑only on CPU CI, `@pytest.mark.slow` long‑running, or optional dependency unavailable; all other SKIPs are invalid. If skipped > 0, add a “Skips:” line in Attempts History (with reason per module/test).
- Capture macro (copy/paste):
  `ART=plans/active/<initiative>/reports/$(date -u +%FT%TZ)`
  `mkdir -p "$ART"; echo $(python -V) > "$ART/run_env.txt"; pip show torch >> "$ART/run_env.txt"`
  `CUDA_VISIBLE_DEVICES="" KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/ | tee "$ART/pytest.log"`
- Integration/parity: wrap with `/usr/bin/time -v` → `$ART/runtime.txt`; if runtime exceeds the documented budget, mark the attempt “partial” and attach timing evidence. Append `lscpu | head -n1` and `grep MemTotal /proc/meminfo` to `run_env.txt`.
- Fixtures: store deterministic fixtures under `tests/fixtures/`; include a `dataset_probe.txt` (keys, shapes, dtypes, SHA256) and cite path+checksum in Attempts History.
- Test style: prefer pytest function tests with fixtures (e.g., `tmp_path`); avoid mixing `unittest.TestCase` unless editing legacy code that already uses it.
