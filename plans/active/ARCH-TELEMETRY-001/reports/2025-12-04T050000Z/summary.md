### Turn Summary
Refactored writer serialization to consume typed StageResult telemetry/perf counters when available, falling back to legacy RefinementTelemetry.to_dict() path for mocks/tests that lack stage_results. Added _extract_stage_payload() helper and updated Stage B baseline attrs with three-tier priority logic (stage_artifacts → typed StageResult → RefinementTelemetry fallback).
All four mapped selectors passed (CLI metadata 0.95s, Stage B guard 0.91s, Stage B shell smoke 22.84s, Stage C microslip 6.95s), confirming byte-for-byte /torch_diagnostics schema compatibility and variance-floor telemetry preservation per PHYSICS-LOSS-001.
Next: Phase C.3.2 to remove legacy_telemetry_dict plumbing inside Stage A/B/C once writer is StageResult-first.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-04T050000Z/ (pytest_cli_diag.log, pytest_stage_b_guard.log, pytest_stage_b_smoke.log, pytest_stage_c_smoke.log)
