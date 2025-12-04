### Loop 2025-12-17T210000Z — Phase C.14 Planning

Focus stays on **ARCH-SIM-CONSTRUCTION-001** (architecture, Tier 0). Phase C.13 aligned mapping and Stage A zero-iteration baselines (DB-AT-027 now PASS), but DB-AT-028/029 still fail because cold-path reconstruction ignores the telemetry baseline whenever `StageAArtifacts` are missing. Today’s loop scoped Phase C.14 to realign the cold path with Stage A telemetry so DB-AT fixtures and future probes see the same masked-intensity scale even without warm caches.

Key decisions:
- Reuse `telemetry_a.model_mean_masked` (and the new mapping diagnostics) to derive a scalar correction whenever `stage_a_ctx.bragg_zero_iter` is absent for `param_state="initial"`. The helper must compute the cold-path masked mean on the canonical loss mask and multiply the tensor by `telemetry/ cold` when both values are positive; guard NaN/zero cases.
- Add regression coverage in `tests/dbex/test_artifact_parity.py` that drops the cached Stage A context before calling `build_final_bragg_from_stage_a_telemetry` and asserts the masked mean matches telemetry within floating-point noise. This keeps SCALE-008/SCALE-009 guardrails enforced.
- Extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` diagnostics so each probe records whether the correction fired (`baseline_alignment_factor`, cache-hit vs cold-path) and surfaces the ratio in JSON/console output, keeping DB-AT-028/029 evidence actionable.

Next Do Now (artifacts to land under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/`):
1. Implement `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` cold-path alignment logic (apply telemetry-derived ratio, emit diagnostics).
2. Add `tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline`.
3. Update `compare_stage_a_baseline.py` instrumentation and rerun the baseline probe plus DB-AT-028/029 per docs/spec-db-conformance.md §DB-AT-028/029.
