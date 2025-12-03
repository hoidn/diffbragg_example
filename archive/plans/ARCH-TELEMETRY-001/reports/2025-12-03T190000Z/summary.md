### Turn Summary
Focused this loop on ARCH-TELEMETRY-001 (Mode Parity, action=planning): clarified how Stage B/C must finish the telemetry collector migration and logged the outstanding Stage B parity guard regression.
Updated docs/fix_plan.md and input.md so the next implementation loop fixes `_check_stage_b_baseline_parity`, removes the remaining `telemetry_state` dict shims, and validates via the Stage B guard plus the Stage B/C small-detector smokes.
Next: implement those collector fixes and capture the mapped pytest logs under the reserved artifact directory before touching writer integration.
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T190000Z/
