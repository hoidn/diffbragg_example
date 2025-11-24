### Turn Summary
Documented spot_scale misapplication as the remaining DB-AT-027 blocker: Stage A engine paths skip the mapping spot-scale baseline, yielding mean_abs_diff=57.07 and max_abs_diff=1.34e7 despite chi² parity.
Refreshed input.md with a calibrated Do Now to thread spot_scale_override through Stage A warm cache/Bragg reconstruction, align probe logging, and target xfail removal.
Updated docs/fix_plan.md attempts to record the persisted gap and pointed artifacts to the new run directory for the upcoming implementation loop.
Next: implement the spot-scale threading, rerun the engine probe plus pytest selector, and unxfail DB-AT-027 once tolerances are satisfied.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T231449Z/ (input.md, summary.md)
