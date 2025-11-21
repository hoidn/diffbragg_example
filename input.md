# Input

- Summary: Extend variance-weighted telemetry to Stage A + DB-AT selectors so canonical chi-squared evidence is captured, then rerun the full-detector smoke and DB-AT-024 mapping with artifacts.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=full`
  * `tests -k DB_AT_024`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/nanobrag_bridge.py::simulate_forward_once` — compute the variance-weighted chi-squared (spec-db-core.md:57-68) alongside masked-MSE, emit sigma-floor metadata and clamp fractions in the diagnostics dict, and plumb these values into DB-AT artifacts so zero-iteration parity shares the canonical loss metric.
- Implement: `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` and `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` — assert Stage A canonical chi-squared snapshots match the final Stage A trace on the full detector, record canonical telemetry in the smoke JSON, and add DB-AT-024 checks that `simulate_forward_once` reports the new chi-squared/sigma-floor telemetry before logging metrics.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/telemetry_stage_a.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=full | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/pytest_stage_a_full.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests -k DB_AT_024 | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/pytest_db_at_024.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/

## How-To Map
1. In `dbex/nanobrag_bridge.py::simulate_forward_once`, import/reuse the shared variance-weighted helper (or mirror its logic) to compute Σ((I_model-I_obs)^2 / max(I_model + sigma^2, sigma_floor^2)) and clamp counts; add `chi_squared`, `sigma_floor_value`, and `variance_floor_clamp_fraction` to the diagnostics payload that DB-AT-024 writes.
2. Update `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` to assert `telemetry.canonical_stage_label == "A"`, `telemetry.canonical_chi_squared` equals the final entry in `chi_squared_trace_full`, and `canonical_roi_count` matches the number of ROIs when `--smoke-detector-size=full`; extend `_record_stage_telemetry` metadata so the JSON in `telemetry_stage_a.json` captures these canonical fields for artifacts.
3. Extend `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke` to expect the new diagnostics (`chi_squared`, `sigma_floor_value`, `variance_floor_clamp_fraction`) and assert `chi_squared` stays positive and `variance_floor_clamp_fraction` is within [0,1]; log the values to `mapping_metrics.json` for later analysis.
4. Run the Stage A full-detector smoke with the strict env knobs and telemetry path above, capture `pytest_stage_a_full.log`, and verify the telemetry JSON now records canonical chi-squared + ROI counts.
5. Run `pytest -k DB_AT_024` with `DBAT024_ARTIFACT_DIR` pointing at this loop’s report directory so mapping metrics, diagnostics JSON, and the pytest log live alongside the Stage A artifacts.
6. Drop both test logs plus `telemetry_stage_a.json` and the refreshed mapping metrics into `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/`, then update docs/fix_plan.md Attempts History + this report directory with the recorded chi-squared/clamp stats.

## Pitfalls To Avoid
- Keep `DBEX_SMOKE_DETECTOR_SIZE=full`; DB-AT selectors hard-fail if the canonical detector isn’t forced.
- Preserve Environment Freeze—do not install packages or tweak CUDA/toolchains; missing deps must be logged as blockers per fix_plan.
- Reuse the exact sigma-floor guard (max with `sigma_floor_value**2`) so zero-iteration diagnostics match Stage A; do not reintroduce bare `max(pred, 0)` approximations.
- Ensure `_record_stage_telemetry` writes canonical metadata without dropping existing perf counters; JSON schema changes should be additive.
- DB-AT-024 artifacts must include both CSV + JSON outputs; don’t skip artifact creation even if pytest passes locally.
- Avoid detaching gradients in production helpers; variance-weighted denominators should be detached, numerators stay differentiable per PHYSICS-LOSS-001.
- Keep long-running tests pinned to `cuda:0` only; no multi-GPU fan-out without explicit approval.
- Do not relax REFINE-007/008 gates while modifying Stage A assertions—telemetry must prove compliance.
- Record sigma-floor clamp fractions in diagnostics to catch silent underflows; leaving them implicit violates PHYSICS-LOSS-002 finding.

## If Blocked
- Capture the failing pytest log (Stage A or DB-AT-024), dump any telemetry JSON generated so far, and append the failure signature + command to `docs/fix_plan.md` Attempts History before marking PHYSICS-LOSS-001 `blocked`. Note whether the block is due to missing dependencies, clamp regressions, or selector guards so the supervisor can rescope.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — All refinement/diagnostics surfaces must emit chi-squared alongside masked-MSE to preserve spec-aligned gating; new helpers/tests must keep both metrics.
- PHYSICS-LOSS-002 — Enforce `sigma_floor_value` in every variance-weighted computation and emit clamp fractions in telemetry/diagnostics.
- PHYSICS-LOSS-003 — Stage A canonical chi-squared snapshots must match downstream stages; the updated smoke assertions guard this.
- REFINE-007 — Stage C (and Stage A baseline) must document ≥80% detector-offset reduction; rerunning the Stage A/C smoke on the full detector preserves this evidence.
- REFINE-008 — Stage B tolerances (≤1e-6 regression, ±1% modifiers) rely on Stage A canonical chi-squared, so Stage A must log/validate the canonical snapshot before Stage B/C consume it.
- SCALE-007 — DB-AT-024 needs telemetry proof (`hkl_*` + now chi-squared) that refined structure factors and canonical loss metrics are being used; diagnostics updates must not regress this guard.

## Pointers
- docs/spec-db-core.md:57 — Normative variance-weighted loss equation + sigma-floor guard to mirror in zero-iteration diagnostics.
- docs/spec-db-conformance.md:43 — DB-AT-024 acceptance thresholds and artifact expectations.
- docs/TESTING_GUIDE.md:38 — Canonical Stage smoke env knobs + detector gates.
- plans/active/PHYSICS-LOSS-001/implementation.md:1 — Current checklist/phasing for this initiative (Phase C focus).
- docs/findings.md:19-21,43,46 — Active findings driving chi-squared telemetry, sigma-floor, and Stage B/C gating updates.

## Next Up (optional)
1. Replay DB-AT-010 gradcheck with the new chi-squared telemetry once DB-AT-024 evidence lands.

## Doc Sync Plan (Conditional)
- n/a (modifying existing selectors; no new nodes added).

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=full`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests -k DB_AT_024`
