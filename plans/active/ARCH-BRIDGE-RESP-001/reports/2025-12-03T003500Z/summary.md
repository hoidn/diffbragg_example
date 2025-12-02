### Turn Summary
Implemented writer Phase B.3: removed inline Nelder-Mead loop, made roi_payloads required, and added ROI scoring telemetry attrs.
Writer now consumes pre-scored ROIAnalysisPayload instances from score_roi_payloads helper; test_torch_diagnostics_metadata validates new attrs and passes.
Next: Fix pre-existing CLI test mock issues (detector_config missing distance_mm, mask_array not handling Mocks) blocking full CLI test suite.
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T003500Z/ (pytest logs)
