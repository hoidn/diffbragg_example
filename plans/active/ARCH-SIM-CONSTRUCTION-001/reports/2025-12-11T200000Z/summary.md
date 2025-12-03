### Turn Summary
Mapped Stage A vs reconstruction callchain and confirmed the cold path drops trusted-mask tensors on CUDA, explaining the 18% raw-intensity gap.
Documented the mask-normalization plan plus trace tap points so the next loop can safely patch reconstruction without touching Stage A.
Next: normalize the mask handling, rerun the intensity probe, then capture DB-AT-028/029 artifacts to prove chi²/ROI parity.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-11T200000Z/ (callchain/static.md, trace/tap_points.md)
