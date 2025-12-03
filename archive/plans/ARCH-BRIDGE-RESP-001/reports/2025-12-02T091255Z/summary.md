### Turn Summary
Repaired CLI test fixtures by replacing bare Mock objects with typed DetectorConfig/BeamConfig/CrystalConfig instances; all three mapped selectors (test_nanobrag_backend_runs_simulator, test_nanobrag_backend_applies_calibration, test_torch_diagnostics_metadata) now PASSED.
The mocked DetectorConfig previously lacked distance_mm and mask_array tensor attributes, causing simulator factory to fail before writer assertions could run; new helpers _make_detector_config/beam_config/crystal_config instantiate real nanobrag_torch.config dataclasses with deterministic parameters.
Next: Phase B.4 (test registry update if needed) or proceed to Phase C (bridge decomposition).
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T091255Z/ (pytest_cli_success.log, 4/4 tests passed in 1.01s)
