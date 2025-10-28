Summary: Close out TORCH-BRIDGE-001 by rerunning bridge + smoke tests and sealing ledger/doc updates.
Mode: none
Focus: TORCH-BRIDGE-001 — Bridge DataLoad to nanobrag_torch
Branch: integration
Mapped tests: pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py
Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z/{pytest.log,smoke_metrics.json,roi_triptych.png,do-now-notes.md}
Do Now:
  1. TORCH-BRIDGE-001 D1 (plans/active/TORCH-BRIDGE-001/implementation.md) — Ensure refGeom assets exist, export KMP_DUPLICATE_LIB_OK=TRUE, run `pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py`; tee log to the artifact path and copy smoke metrics + triptych into the new reports directory. tests: pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py
  2. TORCH-BRIDGE-001 D2 (plans/active/TORCH-BRIDGE-001/implementation.md) — Update docs/fix_plan.md status→done with final Attempts History entry (Metrics/Artifacts lines pointing to new report), refresh do-now-notes.md summary, and note dataset requirements or skips. tests: none
Priorities & Rationale:
- docs/spec-db-core.md:20-41 — Confirms `[panel, slow, fast]` ordering, square-pixel guard, and loss mask policy validated by rerun.
- docs/config_crosswalk.md:16-34 — Detector/beam/trusted-mask mapping stays conformant when rehydrated through tests.
- docs/spec-db-workflow.md:24-29 — Masked-MSE smoke harness remains aligned with stitched per-panel simulation requirements.
- docs/dxtbx_api.md:5-42 — Geometry extraction via dxtbx stays in sync before marking initiative done.
- docs/TESTING_GUIDE.md:5-31 — Enforces environment flags and artifact logging mandated for closure evidence.
How-To Map:
- Verify dataset prerequisites: `[ -f refGeom.refl ] || { echo "refGeom.refl missing; see README Step 5"; exit 1; }`
- `export ART=plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z`
- `mkdir -p "$ART"`
- `python -V > "$ART/run_env.txt" && pip show torch >> "$ART/run_env.txt"`
- `export KMP_DUPLICATE_LIB_OK=TRUE`
- `pytest -v tests/dbex/test_nanobrag_bridge.py tests/dbex/test_nanobrag_bridge_configs.py tests/dbex/test_nanobrag_smoke.py | tee "$ART/pytest.log"`
- After pytest, copy artifacts produced under `plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/` into `$ART` (`cp` metrics + triptych) and update `$ART/do-now-notes.md` with outcomes.
Pitfalls To Avoid:
- Do not run pytest without `KMP_DUPLICATE_LIB_OK=TRUE` (CONFORMANCE-001).
- Failing to generate `refGeom.refl` will skip smoke tests; treat this as a block if unresolved.
- Avoid overwriting 2025-10-28T230500Z artifacts; copy to new timestamp directory instead.
- Capture skip counts in pytest log and note them in Attempts History if dataset absent.
- Keep detector mask polarity assertions intact; do not bypass trusted mask construction shortcuts.
- Ensure final ledger entry includes `Metrics:` and `Artifacts:` lines per policy.
- Leave `nanobrag_torch` stub in place; do not attempt to import real simulator yet.
- Preserve ROI bbox exclusivity when validating artifacts.
- Sync `docs/fix_plan.md` status with actual exit-criteria verification before handoff.
If Blocked:
- If dataset assets cannot be produced, document the block under Attempts History (status `blocked`), attach partial pytest log with skip rationale, and ping TORCH-RUNTIME-002 once prerequisites land.
Findings Applied (Mandatory):
- GEOMETRY-001 — Re-running bridge tests confirms detector geometry mapping + pixel guard before closure.
- CONFORMANCE-001 — Plan enforces `KMP_DUPLICATE_LIB_OK=TRUE` and canonical pytest logging.
- DXTBX-001 — Ledger update will note crystal A* tuple handling as part of wrap-up guidance.
- RUNTIME-001 — Maintains torch.compile disablement by keeping stub harness flow untouched.
