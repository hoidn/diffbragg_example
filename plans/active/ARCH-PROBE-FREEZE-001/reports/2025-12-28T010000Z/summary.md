### Turn Summary (Galph — 2025-12-28T010000Z)

Phase A inventory from 2025-12-27 cataloged 53 plan-local probes and flagged seven
shadow pipelines; this loop selects `compare_stage_a_baseline.py` as the first
migration target for Phase B because it re-implements Stage A/mapping physics and
feeds the DB-AT-027/028/029 diagnostics. Evidence from
`probe_inventory.md` rows 60–111 shows the script is 2,200 LOC, reconstructs warm
contexts manually, and computes ROI/mapping metrics entirely outside Stage A.
The next execution loop must push those computations into production owner APIs
so probes become thin wrappers and telemetry is available directly from Stage A.

**Scope for Phase B.1 (next engineer loop)**
- Extend `RefinementConfig` / Stage A to emit structured baseline metrics when a
  debug flag or metrics output path is set. Metrics need to cover the parity
  summaries currently produced by the probe (masked means, ROI Pearson stats,
  chi² per pixel, top/bottom ROI snippets) so DB-AT-027 evidence can be captured
  without a parallel pipeline.
- Store the metrics in `StageAArtifacts` (e.g., `baseline_metrics`) and allow an
  opt-in JSON dump via env/config so downstream tooling can persist the payload.
- Rework `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py`
  to call Stage A through `RefinementEngine` (no direct simulator/ROI math) and
  simply write the artifact bundle produced by the new telemetry hook.
- Add a pytest covering the new instrumentation (e.g.,
  `tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump`)
  to guard the contract, plus reuse an existing Stage A smoke selector to ensure
  DB-AT evidence still collects.

Artifacts from the implementation loop must be rooted at
`plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T010000Z/` (JSON metrics,
pytest logs, updated script README if applicable).
