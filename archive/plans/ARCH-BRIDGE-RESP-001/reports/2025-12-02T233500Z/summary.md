### Turn Summary
Implemented Phase B.2 payload threading: wired CLI `run_nanobrag_backend` to call `score_roi_payloads` with correct sigma conversions and pass typed payloads to writer via new `roi_payloads` kwarg.
Extended `write_torch_outputs` signature with `roi_payloads` parameter (default None, unused until Phase B.3 removes inline scoring loop); updated tests to patch helper and assert payload threading; documented new API in writer IDL and manifest.
Next: Phase B.3 will consume `roi_payloads` in writer and delete inline Nelder-Mead loop once payload plumbing is proven stable (test failures unrelated to Phase B.2—mock detector config brittleness in simulator factory).
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T233500Z/ (pytest_nanobrag_backend_runs_simulator.log)
