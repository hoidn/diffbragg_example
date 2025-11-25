# DBEX + PyTorch Spec — Index (Spec DB)

This index lists the normative specification shards for the DiffBragg/DBEX + PyTorch workflow. The shards together form the contract that implementations SHALL satisfy.

- spec-db-core.md — Core physics, geometry, units, data contracts (reflections/ROIs/masks), inputs/outputs.
- spec-db-runtime.md — PyTorch runtime guardrails (vectorization, device/dtype, compile, env), determinism.
- spec-db-workflow.md — End‑to‑end pipeline: ingestion → background → masking → calibration → simulation → loss → staging.
- spec-db-interfaces.md — CLI/API surface and precedence rules.
- spec-db-conformance.md — Acceptance tests (DB‑AT‑XXX) and parity profiles.
- spec-db-tracing.md — Tracing/instrumentation and parity workflows.
- spec-db-vis.md — Visual diagnostics standards and plot definitions.

Backend summary (informative)
- diffbragg — Default backend (legacy); not Spec‑DB conformant (diagnostic only).
- nanobrag — Non‑default; Spec‑DB conformance target (DB‑AT profiles) and SHALL be selected via `--backend nanobrag`.

References (informative unless noted)
- docs/config_crosswalk.md — Normative by reference for detector/beam/crystal/config mapping when cited from `spec-db-core.md` §Geometry Mapping.
- docs/nanobrag_api.md, docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md — API detail.
- plans/nanobrag_integration_plan.md — Execution plan implementing this spec.
