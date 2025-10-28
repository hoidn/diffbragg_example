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
- Store `pytest` logs, parity metrics, and trace outputs under `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/`.
- Reference the artifact path (log, summary, metrics.json) in the fix plan Attempts History entry that triggered the run.

## 4. Reporting Checklist
- Include command, exit code, and runtime.
- Record hardware context (CPU/GPU) and dtype if deviating from defaults.
- For parity tests, capture correlation, MSE, RMSE, max|Δ|, and sum ratios (see `docs/spec-db-tracing.md`).
- If a required selector is missing, file a TODO under the relevant fix-plan item and capture repro notes in the artifact directory.

