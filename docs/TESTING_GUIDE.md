# DBEX Testing Guide

This guide standardizes how agents run and author tests for the DiffBragg → `nanobrag_torch` integration work.

## 1. Environments & Flags
- Always export `KMP_DUPLICATE_LIB_OK=TRUE` before importing torch (`docs/spec-db-conformance.md:28`).
- Gradient checks MUST set `NANOBRAGG_DISABLE_COMPILE=1` to bypass `torch.compile` (`docs/pytorch_runtime_checklist.md:26`).
- Prefer editable installs: `pip install -e .` from the repo root to ensure CLI entry points resolve.

## 2. Test Taxonomy

| Scope | Selector | Purpose | Notes |
| --- | --- | --- | --- |
| Smoke | `python -m dbex.refine_one --help` | Verifies legacy CLI loads after environment changes. | Run before/after backend refactors.
| Torch smoke (planned) | `pytest -v tests -k DB_AT_001` | Validates simple cubic parity once torch backend harness exists. | Use `KMP_DUPLICATE_LIB_OK=TRUE`.
| Workflow ingestion | `pytest -v tests -k DB_AT_020` | Ensures DIALS reflection ingestion + bbox semantics stay aligned. | Blocks CLI parity work.
| Mask semantics | `pytest -v tests -k DB_AT_021` | Guards trusted-mask polarity per `docs/spec-db-core.md:51`. | Author targeted fixtures when masks land.
| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | Protects equal-weight source handling and vectorized loops. | CPU required; GPU optional.

Tests marked “planned” must be authored before declaring their parent fix-plan items complete. Until then, record TODO entries in `docs/fix_plan.md` with the relevant selector.

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
