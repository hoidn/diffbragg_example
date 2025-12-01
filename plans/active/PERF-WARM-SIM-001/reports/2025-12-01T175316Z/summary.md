### Turn Summary
Documented that Stage C best-snapshot tuples never persist back into telemetry_state, so the smoketest logs the last LBFGS iterate and trips REFINE-007 even though an earlier validation matched Stage A.
Updated docs/fix_plan.md, docs/findings.md, and input.md with REFINE-013 plus a ready-to-run Do Now directing Ralph to persist the tuples, reload them before final chi² logging, and rerun both Stage C smoketests with telemetry + summarizer capture.
Next: implement the telemetry persistence in dbex/refinement/stage_c_impl.py and generate the 2025-12-01T175316Z Stage C smoketest artifacts so we can confirm the gate is green again.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T175316Z/ (stage_c_best_snapshot_bug.md, summary.md)
