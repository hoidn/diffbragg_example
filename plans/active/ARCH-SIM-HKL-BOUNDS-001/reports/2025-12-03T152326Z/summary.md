### Turn Summary
Phase A probe verified MOSFLM A* parity (max|ΔA*|=4.4e-09 Å⁻¹), so the 0% HKL coverage stems from the scattering-vector→HKL projection rather than config factories.
Scoped Phase B.1 around a dedicated `inspect_hkl_projection.py` probe that reproduces nanobrag_torch's pixel math for the beam spot and ±slow/fast offsets to expose the constant +30/+40 index shift.
Updated the implementation plan, fix-plan entry, and artifacts directory so Ralph can build the script, capture JSON/summary evidence, and keep telemetry grounded in the canonical mapping fixture.
Next: implement the projection probe, drop the metrics + Markdown summary into the reserved reports directory, and run the sigma-map pytest smoke to ensure the repo stays clean.
Artifacts: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z/

### Turn Summary
Implemented `inspect_hkl_projection.py` CLI to reproduce scattering-vector→HKL projection math for beam-center and offset pixels; script reveals all test pixels correctly map to HKL=(0,0,0) and fall IN BOUNDS, contradicting DIAG's 0% coverage finding.
The per-pixel projection geometry is correct around the beam center, suggesting the 0% coverage issue occurs elsewhere (possibly ROI-specific pixels, oversampling, or full-detector runs rather than small-detector smoke tests).
Next: compare this small-detector beam-center evidence against DIAG's full run to isolate where the out-of-bounds queries originate.
Artifacts: plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T152326Z/ (hkl_projection_metrics.json, hkl_projection_summary.md)
