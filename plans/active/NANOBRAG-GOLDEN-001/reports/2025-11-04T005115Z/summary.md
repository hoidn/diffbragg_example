# Loop Summary: 2025-11-04T005115Z

## Focus
NANOBRAG-GOLDEN-001 — Phase A4 detector geometry alignment for canonical DB-AT-001 tensors

## Key Observations
- Latest canonical capture (`reports/2025-11-04T011500Z`) still shows torch peak offsets of 5–7 px (e.g., roi_idx=40 diff_peak=[7,6] vs torch_peak=[0,11]) with localization 5.6% and torch_max 5.3e4 (>1.47× diffbragg_max).
- `dbex/nanobrag_bridge.create_detector_config` currently hardcodes zero XYZ rotations despite `refGeom.expt` panel tilt; missing rotations explain the systematic Y+6, X+1 pixel drift.
- Dxtbx panel axes from `refGeom.expt` map to a rotation matrix yielding XYZ angles ≈(179.72°, -0.045°, -0.097°); supplying these under `DetectorConvention.DIALS` keeps BEAM pivot fixed and matches the prototype that eliminated offsets.
- `AUTHORITATIVE_CMDS_DOC` exported to `./docs/TESTING_GUIDE.md` for this loop.
- Promoted ROI offset summarizer to reusable script `plans/active/NANOBRAG-GOLDEN-001/bin/summarize_roi_offsets.py` for downstream parity validation.

## One-off analysis
### Dxtbx orientation → XYZ Euler check (T1)
```bash
python - <<'PY'
from dxtbx.model.experiment_list import ExperimentListFactory
from scitbx import matrix
exp = ExperimentListFactory.from_json_file('refGeom.expt', check_format=False)[0]
panel = exp.detector[0]
fast = panel.get_fast_axis()
slow = panel.get_slow_axis()
normal = panel.get_normal()
R = matrix.sqr(fast + slow + normal)
angles = tuple(a * 180.0 / 3.141592653589793 for a in R.r3_rotation_matrix_as_x_y_z_angles())
print('fast axis', fast)
print('slow axis', slow)
print('normal', normal)
print('XYZ degrees', angles)
PY
```
Output:
```
fast axis (0.9999982614666334, 0.0016932224556383707, -0.000781064291071184)
slow axis (0.0016894016506467187, -0.9999867300677044, -0.004866786471866984)
normal (-0.0007892944785418853, 0.004865458479493718, -0.9999878520902196)
XYZ degrees (179.72115248952696, -0.044751691956970804, -0.09701457643417304)
```

## Next Steps
1. Derive per-panel XYZ rotations inside `dbex/nanobrag_bridge.py::create_detector_config` using dxtbx axes and populate `DetectorConfig(detector_rotx_deg, detector_roty_deg, detector_rotz_deg)` while keeping BEAM pivot.
2. Regenerate canonical dataset with `scripts/generate_simple_cubic_golden.py` into a new report directory (timestamp this loop) and capture ROI offsets/metrics proving localization ≤1 px and torch_max ≈ diffbragg_max.
3. Run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke`, archive log to artifacts, and update Attempts History with results plus any new findings.
