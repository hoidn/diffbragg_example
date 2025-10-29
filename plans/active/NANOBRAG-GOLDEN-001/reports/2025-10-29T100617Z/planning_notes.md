# NANOBRAG-GOLDEN-001 — HKL Orientation Analysis (2025-10-29T100617Z)

## Key Observations
- Canonical capture log shows `INCIDENT_BEAM_DIRECTION= 0 0 1` while detector normal points toward sample (`DIRECTION_OF_DETECTOR_Z-AXIS≈-z`), implying stored beam vector is sample→source; scattering formula expects source→sample.
- HKL diagnostics remain `[18,48]/[14,53]/[23,61]` with 0% hit rate, matching `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/canonical_capture.log`.
- Multi-source path already negates `source_directions`; single-source default must mirror that by negating `detector.beam_vector` before passing into `compute_physics_for_position`.

## Evidence Links
- Canonical capture log: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/canonical_capture.log
- Torch HKL debug: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/torch_hkl_debug.json

## Proposed Actions
1. Update `nanoBragg_torch.simulator.Simulator.__init__` to store `incident_beam_direction = -detector.beam_vector` (source→sample) and normalize multi-source tensors.
2. Regenerate canonical tensors via `scripts/generate_simple_cubic_golden.py` with `debug_config={'trace_pixel': [beam_slow, beam_fast]}` to confirm HKL range matches structure-factor bounds.
3. Re-run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001` to validate canonical dataset swap readiness.
