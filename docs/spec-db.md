# DBEX + PyTorch Spec — Index (Spec DB)

This index lists the normative specification shards for the DiffBragg/DBEX + PyTorch workflow. The shards together form the contract that implementations SHALL satisfy.

- spec-db-core.md — Core physics, geometry, units, data contracts (reflections/ROIs/masks), inputs/outputs.
- spec-db-runtime.md — PyTorch runtime guardrails (vectorization, device/dtype, compile, env), determinism.
- spec-db-workflow.md — End‑to‑end pipeline: ingestion → background → masking → calibration → simulation → loss → staging.
- spec-db-interfaces.md — CLI/API surface and precedence rules.
- spec-db-conformance.md — Acceptance tests (DB‑AT‑XXX) and parity profiles.
- spec-db-tracing.md — Tracing/instrumentation and parity workflows.
- spec-db-vis.md — Visual diagnostics standards and plot definitions.

References (informative)
- docs/config_crosswalk.md — Mapping between DIALS/dxtbx/simtbx, DiffBragg concepts, and nanobrag_torch configs.
- docs/nanobrag_api.md, docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md — API detail.
- plans/nanobrag_integration_plan.md — Execution plan implementing this spec.
