# Input

- Summary: Align Stage A/B/C chi-squared telemetry via a shared variance-weighted helper so Stage C gates and Stage B modifiers compare apples to apples on the canonical detector.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full`
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full`
  * `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/nanobrag_refinement.py::{_accumulate_variance_weighted_loss,run_nanobrag_refinement}` plus `tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` and `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` — create a shared chi-squared helper that consumes one cached `sigma_floor_sq` tensor, thread it through Stage A/B/C closures + telemetry so the canonical detector emits identical Σ((pred-target)^2 / V) traces, and add assertions that Stage A vs Stage B/C chi-squared agree within the REFINE-007/008 tolerances.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/telemetry_stage_c.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/pytest_stage_c_full.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/telemetry_stage_b.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/pytest_stage_b_full.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/pytest_cli_metadata.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/

## How-To Map
1. Update `dbex/nanobrag_refinement.py` to expose a single `_compute_variance_weighted_loss` helper that wraps `_accumulate_variance_weighted_loss`, reusing one `sigma_floor_sq` tensor per device; ensure Stage A/B/C closures call it for sampled and full validations so `chi_squared_trace_*` always reflects Σ((pred-target)^2 / (pred.detach()+sigma^2)).
2. Thread Stage A canonical detector metadata (baseline detector distances + ROI counts) into the helper so Stage C’s improvement compares against the same full-detector snapshot; store Stage A final chi-squared inside Stage B/C telemetry for cross-checking.
3. Refresh `tests/dbex/test_torch_refine_smoke.py::{test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` to assert Stage A and downstream chi-squared traces differ by ≤1e-6 relative error when `--smoke-detector-size=full`, and ensure telemetry JSON written to `$DBEX_SMOKE_TELEMETRY_PATH` captures the aligned values for artifacts.
4. Run the Stage C full-detector smoke with telemetry path `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/telemetry_stage_c.json`, confirm detector_offset_reduction_min ≥0.8 and the Stage A vs Stage C chi-squared improvement is ≥2e-5, and archive the log + JSON in the artifacts directory.
5. Run the Stage B full-detector smoke under the same env flags, verify the improvement gate (≥-1e-6) references the shared chi-squared helper, and capture telemetry to `telemetry_stage_b.json` plus the pytest log.
6. Re-run `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata` to prove `/torch_diagnostics` reports the new chi-squared schema without regressions, teeing output to `pytest_cli_metadata.log`.

## Pitfalls To Avoid
- Do not relax the strict Stage B/C gates; fix the math so the existing thresholds pass.
- Preserve `RefinementTelemetry` backward compatibility (legacy `loss_trace_*` fields still populated).
- Keep Stage A baseline detector plumbing intact; `baseline_detector` must remain optional and default to current behavior when not provided.
- Avoid detaching tensors incorrectly — only the variance denominator is detached, not the numerator.
- Always run smokes with `DBEX_SMOKE_DETECTOR_SIZE=full`, `KMP_DUPLICATE_LIB_OK=TRUE`, and `NANOBRAGG_DISABLE_COMPILE=1` so the canonical dataset is exercised.
- Telemetry JSON must live under `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/`; don’t scatter files elsewhere.
- Do not change environment deps or install packages (Environment Freeze policy).
- Keep sigma-floor default ≥1 photon/ADU equivalent; do not zero it out while testing.
- Maintain Stage B shell modifier clamp (`stage_b_max_modifier`) logic while refactoring — no inadvertent gradient detach.

## If Blocked
- Capture the failing pytest log + telemetry JSON, note the exact assertion in `docs/fix_plan.md` Attempts History, mark PHYSICS-LOSS-001 `blocked` with the error signature, and ping Galph before modifying gates or datasets.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — All stages must emit chi-squared alongside masked-MSE, so keep telemetry dual metrics intact while refactoring.
- PHYSICS-LOSS-002 — Sigma-floor guard (V = max(I_model + sigma^2, sigma_floor^2)) stays enabled; record clamp fractions in telemetry.
- PHYSICS-LOSS-003 — Stage A must reuse the per-pixel Σ((diff^2)/V) helper so canonical comparisons with Stage B/C remain meaningful.
- REFINE-007 — Stage C must show ≥0.002% chi-squared improvement and ≥80% detector-offset reduction on the full detector; keep gate assertions untouched.
- REFINE-008 — Stage B shell modifiers must stay within ±1% with ≤1e-6 regression; ensure new helper honors this telemetry budget.

## Pointers
- docs/spec-db-core.md:57 — Normative variance-weighted loss equation and sigma-floor guard.
- docs/TESTING_GUIDE.md:38 — Canonical Stage B/C smoke gates and required env vars.
- dbex/nanobrag_refinement.py:360 — `_accumulate_variance_weighted_loss` implementation that needs to be shared across stages.
- tests/dbex/test_torch_refine_smoke.py:500 — Stage C detector smoke assertions referencing chi-squared + telemetry.
- plans/active/PHYSICS-LOSS-001/implementation.md:1 — Phase breakdown and exit criteria for this initiative.

## Next Up (optional)
1. After chi-squared alignment, replay DB-AT-024 mapping (Phase C2) under the new loss to capture updated telemetry.

## Doc Sync Plan (Conditional)
- n/a (no new selectors this loop; update docs only if assertions change).

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
