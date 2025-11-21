### Turn Summary
Cropper emitted the refGeom_small dataset plus README/checksums so we can flip Stage smokes onto a 1024×1024 detector without touching the canonical assets.
Smokes now honor --smoke-detector-size/DBEX_SMOKE_DETECTOR_SIZE, log perf telemetry when asked, and keep the full-detector gates when parity selectors run; docs and the fix-plan entry explain the new workflow.
Next: teach DB-AT selectors to assert --smoke-detector-size=full (and chase the Stage-B telemetry "error" that nanoBragg reports under the relaxed smoke run).
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/ (refGeom_small_report.json, refGeom_small.sha256, collect_stage_a_small.log, pytest_stage_smokes_small.log, pytest_stage_a_full.log, telemetry_small.json)

### Turn Summary
Elevated PERF-SMOKE-DETSIZE per the manual override, marked PHYSICS-LOSS-001 blocked, and updated docs/fix_plan plus galph memory so the small-detector work is now the active initiative.
Ran quick probes on `refGeom` to confirm the detector is a single 2463×2527 panel with 282 ROIs and that a centered 1024×1024 crop preserves 87 ROIs (~31%)—enough coverage for Stage smokes while shrinking tensors by ~76%.
Drafted the new Do Now/input (crop script + pytest option + doc updates) and captured evidence paths so Ralph can implement the refGeom_small fixture immediately.
Next: Ralph wires the cropper and smoke fixtures, reruns the Stage A/B/C smoke selectors on the small dataset, and records runtime/VRAM improvements before resuming the PHYSICS-LOSS work.
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/ (summary.md)

#### Micro probes
- Command:
  ```
  python - <<'PY'
  from dxtbx.model import ExperimentList
  from dials.array_family import flex
  expt = ExperimentList.from_file('refGeom.expt')[0]
  detector = expt.detector
  print(f'n_panels={len(detector)}')
  print('panel_shape_px', detector[0].get_image_size())
  refs = flex.reflection_table.from_file('refGeom.refl')
  bboxes = [tuple(bbox) for bbox in refs['bbox']]
  slow_min = min(b[2] for b in bboxes)
  slow_max = max(b[3] for b in bboxes)
  fast_min = min(b[0] for b in bboxes)
  fast_max = max(b[1] for b in bboxes)
  print('bbox_fast_range', (fast_min, fast_max))
  print('bbox_slow_range', (slow_min, slow_max))
  print('roi_count', len(bboxes))
  PY
  ```
  Output:
  ```
  n_panels=1
  panel_shape_px (2463, 2527)
  bbox_fast_range (103, 2453)
  bbox_slow_range (5, 2501)
  roi_count 282
  ```
- Command:
  ```
  python - <<'PY'
  from dxtbx.model import ExperimentList
  from dials.array_family import flex
  expt = ExperimentList.from_file('refGeom.expt')[0]
  panel = expt.detector[0]
  slow, fast = panel.get_image_size()
  refs = flex.reflection_table.from_file('refGeom.refl')
  central_fast0 = (fast - 1024)//2
  central_fast1 = central_fast0 + 1024
  central_slow0 = (slow - 1024)//2
  central_slow1 = central_slow0 + 1024
  count = 0
  for bbox in refs['bbox']:
      x0, x1, y0, y1, *_ = bbox
      if x0 >= central_fast0 and x1 <= central_fast1 and y0 >= central_slow0 and y1 <= central_slow1:
          count += 1
  print('central_fast_range', (central_fast0, central_fast1))
  print('central_slow_range', (central_slow0, central_slow1))
  print('roi_in_central_1024', count)
  PY
  ```
  Output:
  ```
  central_fast_range (751, 1775)
  central_slow_range (719, 1743)
  roi_in_central_1024 87
  ```
