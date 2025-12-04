### Turn Summary — 2025-12-30T150000Z (Supervisor Planning)

- Locked Phase B.6 scope: migrate `capture_smoke_calibration.py` (DiffBragg smoke bundle capture) into owner modules so calibration provenance is produced by `dbex.calibration`/`dbex.tools` rather than a 330+ LOC plan script.
- Implementation plan updated with B6 checklist (new helper module `dbex/calibration/smoke_capture.py`, CLI `python -m dbex.tools.capture_smoke_calibration`, plan shim, doc updates, dual validation commands for full + small datasets).
- docs/fix_plan.md Attempts History records the new phase plus reserved artifact path `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/` to keep probe-freeze directive serviced.
- Next loop (implementation_ready) will build the owner modules, update doc references, collapse the plan script to a shim, and run the canonical capture commands while stashing configs/manifests/logs under `capture_full/` and `capture_small/` in this directory.
