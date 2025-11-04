# DB-AT-002 Planning Notes — 2025-11-04T043700Z

## Problem Statement
DB-AT-002 determinism selector is still marked `Planned` in `docs/TESTING_GUIDE.md:65` and lacks a production harness. With FORWARD-EQUIV-002 complete and canonical tensors available, we need a pytest module that exercises same-seed reproducibility and different-seed independence using nanobrag_torch, persisting determinism metrics under this initiative.

## Key References
- `docs/development/testing_strategy.md` §2.7 (determinism workflow, env guards, metrics thresholds)
- `docs/TESTING_GUIDE.md:65` & `docs/development/TEST_SUITE_INDEX.md:21` (selector metadata, artifact expectations)
- `docs/pytorch_runtime_checklist.md:45-52` (runtime guardrails for determinism, environment flags)
- Canonical tensors + manifest: `plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/`

## Plan Highlights
1. **Reuse parity loader utilities** to generate simulator outputs with explicit RNG seed parameters so same/different seed runs can be compared deterministically.
2. **Metrics schema**: record `array_equal`, correlation, max abs diff, differing pixel percentage for both scenarios; serialize into `metrics_same_seed.json` / `metrics_diff_seed.json`.
3. **Environment enforcement**: module-level guard ensures CPU-only execution before importing torch (per testing_strategy §2.7.5) to avoid CUDA determinism pitfalls.
4. **Artifacts**: log commands + metrics under `plans/active/DB-AT-002/reports/<timestamp>/determinism/`, capture env fingerprint to support reproducibility.

## Next Steps
- Author Do Now covering Phase A checks and sampler harness scaffolding for same-seed flow.
- Ensure `docs/fix_plan.md` tracks this initiative with `in_progress` status and updated dependencies (FORWARD-EQUIV-002, NANOBRAG-BACKEND-002, TORCH-RUNTIME-002).

