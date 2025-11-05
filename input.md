Summary: Align the nanobrag bridge mask contract with torch tensor emission while keeping Stage B telemetry green.
Mode: none
Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
Branch: integration
Mapped tests: tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_mask_array_float_conversion, tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z/

Do Now:
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
  - Implement: dbex/nanobrag_bridge.py::create_detector_config — coerce `trusted_mask` with `torch.as_tensor(..., dtype=torch.float32)` (no implicit device change), assert the tensor stays 0/1-valued, and refresh the inline comment/doc reference so CLI-001 and Stage B conversions remain aligned.
  - Implement: tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_mask_array_float_conversion — accept torch.Tensor masks by checking `torch.is_floating_point`, convert to numpy for polarity asserts, and fail fast if the tensor leaves {0.0, 1.0} or shape drifts.
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_mask_array_float_conversion --maxfail=1 | tee $ARTIFACTS/pytest_bridge_mask.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 | tee $ARTIFACTS/pytest_stage_b_regression.log
  - Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z
- mkdir -p "$ARTIFACTS"
- pytest --collect-only tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_mask_array_float_conversion | tee "$ARTIFACTS/collect_bridge_mask.log"
- pytest -vv tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigMapping::test_mask_array_float_conversion --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_bridge_mask.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee "$ARTIFACTS/collect_stage_b.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_b_regression.log"
- rg "Stage [AB] (final|improvement)" "$ARTIFACTS/pytest_stage_b_regression.log" | tee "$ARTIFACTS/stage_b_metrics.txt"
- printf "Bridge mask + Stage B telemetry verified; see %s and %s\n" "$ARTIFACTS/pytest_bridge_mask.log" "$ARTIFACTS/pytest_stage_b_regression.log" >> "$ARTIFACTS/summary.md"

Pitfalls To Avoid:
- Respect Environment Freeze; treat missing deps as blockers instead of installing anything.
- Do NOT revert CLI-001: `create_detector_config` must keep returning torch float masks so the CLI path remains functional.
- Preserve Stage B tensor conversions in `run_nanobrag_refinement`; keep them device/dtype neutral and idempotent.
- Maintain halo/interpolation guards from REFINE-005; mask updates must not bypass default_F protections.
- Keep ROI sampling deterministic and reuse Stage A panel IDs to avoid telemetry regressions.
- Capture any dtype/device mismatches via asserts rather than silent casts so failures surface quickly.

If Blocked:
- Record the failing command, traceback, and `type/dtype` of `mask_array` in $ARTIFACTS/blocker_mask.log, flag the fix-plan item as blocked with rationale, and log the next retry condition in galph_memory.md before exit.

Findings Applied (Mandatory):
- CLI-001 — Bridge must emit torch float masks for CLI paths; validating we stay in compliance after tightening tests.
- REFINE-005 — Halo + interpolation guardrails remain enforced; Stage B tweaks must not reintroduce default_F fallbacks.
- REFINE-008 — Stage B gate calibrated to 1e-8; smoke run needs to keep telemetry consistent while we adjust mask handling.
- SCALE-001/002 — Shell modifiers stay multiplicative; mask updates must not sneak in intensity rescaling.
- RUNTIME-001 — Keep `NANOBRAGG_DISABLE_COMPILE=1` during Stage B pytest to avoid torch.compile side effects.

Pointers:
- dbex/nanobrag_bridge.py:379 — Mask tensor emission path tied to CLI-001.
- tests/dbex/test_nanobrag_bridge_configs.py:141 — Bridge mask dtype/polarity assertions to update.
- docs/nanobrag_api.md:44 — Mask semantics (tensor 0/1, shape requirements).
- docs/config_crosswalk.md:31 — Detector mask mapping reference; cross-check after edits.
- docs/findings.md:41 — CLI-001 details on torch mask requirement.

Next Up (optional):
- Re-run the CLI refine-one telemetry smoke once bridge/test contract stabilizes to ensure mask asserts stay silent end-to-end.

Doc Sync Plan (Conditional):
- None — selectors unchanged; note doc edits in the commit if mask semantics text moves.
