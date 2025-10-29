# NANOBRAG-GOLDEN-001 Phase A1 Environment Diagnostics

**Timestamp:** 2025-10-29T030352Z

## Environment Status: RESOLVED

### Torch Installation (Pinned)
- **Status:** ✓ Working
- **Version:** 2.4.1+cu121 (do not upgrade)
- **CUDA Available:** True
- **CUDA Toolkit:** 12.1 (PyTorch wheel)
- **GPU:** NVIDIA GeForce RTX 3090 (driver 570.195.03)
- **Python:** 3.9.23 @ /home/ollie/miniconda3/envs/simtbx/bin/python

### nanobrag_torch Installation
- **Status:** ✓ Installed (editable)
- **Version:** 0.1.0
- **Repository:** https://github.com/hoidn/nanoBragg.git
- **Command:** `pip install -e ./nanoBragg`

### DiffBragg Baseline Export
- **Status:** ✓ Completed on GPU
- **Command:** `DIFFBRAGG_USE_CUDA=1 python -m dbex.refine_one -e refGeom.expt -r refGeom.refl -i 0 -o .../dbex_diffbragg_gpu.h5 -m 747_mask.pkl -z scaled.mtz`
- **Iterations:** 2101 (basinhopping converged, F=678151, sigZ=12.27)
- **Output:** `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T030352Z/golden_dataset/legacy/dbex_diffbragg_gpu.h5`
- **Log:** `.../legacy/diffbragg_forward_gpu.log`
- **Result:** No CUDA errors encountered after torch downgrade; baseline tensor ready for Phase B comparisons.

### Residual Actions
- Capture canonical nanoBragg tensors (Phase A3)
- Proceed with manifest/metadata updates (Phase B)

## Validation Commands
```bash
which python
python -m torch.utils.collect_env | head -n 25
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
python -c "import dbex; import dbex.refine_one"
```

## Artifacts
- Full environment details: `env_bootstrap.log`
- GPU run log: `legacy/diffbragg_forward_gpu.log`
- DiffBragg baseline: `legacy/dbex_diffbragg_gpu.h5`
