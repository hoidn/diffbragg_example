Summary: Capture the exact Stage A scale-factor telemetry and wire reconstruction/probes to consume it so we can prove where the log_scale delta inflation originates.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/

Do Now:
- Implement: dbex/refinement/stage_a.py::_run_stage_a_lbfgs — persist the exact values used during the final forward pass (`target_mean_masked`, `model_mean_masked`, `log_scale_baseline_value`, `log_scale_delta_clamped`, `log_scale_clamped`, `scale_factor`) into telemetry. Store a new `param_deltas['log_scale_effective']` (initial=baseline or 0, final=baseline+clamped_delta) plus a `scale_provenance` dict so downstream consumers can read the authoritative numbers.
- Implement: dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry — prefer the recorded `log_scale_effective` / `scale_provenance['scale_factor']` when available, emit warnings when recomputation from baseline+delta disagrees, and fall back to the old code path for legacy telemetry. Keep the existing mask/N_cells logic untouched.
- Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py::main — print the new telemetry block next to the mapping statistics and dump it into the probe JSON so we can compare Stage A vs reconstruction numerically in future loops.
- Validate: (1) Run the scale probe with logging.
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py \
  --detector-size small \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/scale_probe/stage_a_scale_alignment.json \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/scale_probe_run.log
```
(2) Re-run the DB-AT selectors with artifact capture.
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/db_at_028 \
DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/db_at_029 \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/pytest_db_at_028_029.log
```
- Archive the updated telemetry JSON, probe summary, and pytest logs under the artifacts directory so the supervisor can diff the scale numbers next loop.

How-To Map:
1. Modify Stage A telemetry (dbex/refinement/stage_a.py) where `log_scale_clamped` is computed so you record the clamped delta, final log-scale, and resulting `scale_factor` before packaging `param_deltas`.
2. Extend reconstruction’s `build_final_bragg_from_stage_a_telemetry` to read the new telemetry keys first and only fall back to `log_scale_baseline + clamp(delta)` when they are absent; log both values for comparison.
3. Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py` so the JSON + stdout include the new telemetry fields alongside the mapping stats.
4. Run the probe and DB-AT selectors with the commands above, ensuring `AUTHORITATIVE_CMDS_DOC` is set and artifacts land in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/`.

Pitfalls To Avoid:
- Do not change the semantics of `log_scale` (it must remain a delta parameter) or clamp behavior; the new telemetry fields are additive only.
- Keep reconstruction backward compatible: older telemetry won’t have `log_scale_effective`, so guard all lookups.
- Device/dtype neutrality still applies — any tensors you add must live on `config.device` / `dtype` and detach before logging.
- Avoid noisy prints in production paths; the new scale diagnostics should go into telemetry/probe outputs, not unconditional stdout spam.
- Do not relax DB-AT gates or fiddle with variance definitions; we are only observing scale provenance.
- Preserve existing mask/N_cells behavior when touching reconstruction.

If Blocked:
- If telemetry lacks the expected keys or Stage A can’t compute the new stats, leave the previous behavior in place, log the missing data to the artifacts directory (`missing_scale_provenance.json`), and capture the failure signature (including the debug prints) before escalating; do not guess at new scaling logic.

Findings Applied (Mandatory):
- SCALE-009 — Reconstruction helpers must honor the Stage A scale baseline and telemetry when rebuilding cold-path simulators.
- REFINE-001 — Global scale guarding (log-scale clamps and calibration precedence) governs how we record and reuse scaling parameters; instrumentation must respect those constraints.

Pointers:
- docs/fix_plan.md:133 — ARCH-SIM-CONSTRUCTION-001 attempts history and current status.
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md — Phase C.7 checklist describing this telemetry instrumentation work.
- docs/spec-db-core.md:Objective Function & Variance Model — canonical scale/variance definitions that must stay intact during instrumentation.

Next Up (optional): If the new telemetry shows Stage A really is applying the inflated scale, open a dedicated initiative or spec-change to revisit the log_scale baseline math before attempting more reconstruction tweaks.

Doc Sync Plan: n/a — no new selectors are being added; existing tests already cover this area.
