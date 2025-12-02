### Turn Summary
Re-scoped ARCH-LAZY-IMPORTS-001 per the problems-ledger guard and planned the Stage A/C stage-wrapper lazy-import cleanup in Mode none / planning.
Updated the implementation plan, fix-plan attempts, and problems.md with the new artifact path, the Stage A/C import-hoist checklist, and the validation expectations.
input.md now directs Ralph to hoist the Stage A/C config-factory + stdlib imports, keep the documented geometry exceptions lazy, and rerun the Stage A smokes plus the known-failing Stage C smoke while logging evidence.
Next: implement the module-scope import changes and capture the three pytest logs (Stage C failure should match the ARCH-TELEMETRY-001 `loss_trace_sample` signature) under `plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-04T010500Z/`.
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-04T010500Z/ (input.md, planning notes)
