# diffBraggCUDA.cu Line 708 Bugfix Patch

**Date**: 2025-10-29
**Reporter**: Ralph (NANOBRAG-GOLDEN-001 loop 2025-10-29T063817Z)
**Finding**: DIFFBRAGG-001
**Policy**: POLICY-001 (Environment Freeze bugfix exception)

## Problem

`diffBragg_forward` standalone forward pass crashes with `GPUassert: invalid argument` at `diffBraggCUDA.cu:708` on both CPU (devId=-1) and GPU (devId=0) modes.

## Root Cause

Lines 708-709 in `gpu_free_all()` unconditionally call `cudaFree()` on `cp.cu_sourceI_scale` and `cp.cu_sourceI_grad` without checking if these pointers were ever allocated or already freed:

```cuda
// BEFORE (buggy code):
if (cp.Fhkl_grad_arrays_allocated){
    gpuErr(cudaFree(cp.FhklLinear_ASUid));
    gpuErr(cudaFree(cp.Fhkl_scale));
    gpuErr(cudaFree(cp.Fhkl_scale_deriv));
    cp.Fhkl_grad_arrays_allocated=false;
}
gpuErr(cudaFree(cp.cu_sourceI_scale));  // ← Line 708: UNCONDITIONAL FREE
gpuErr(cudaFree(cp.cu_sourceI_grad));   // ← Line 709: UNCONDITIONAL FREE
if (cp.grad_arrays_allocated){
    gpuErr(cudaFree(cp.data_trusted));
    ...
}
```

### Allocation Pattern

These arrays are allocated in two places:

1. **Dynamic reallocation** (lines 76-95): When `previous_nsource` changes
2. **Initial allocation** (lines 122-130): When `!device_is_allocated`

In both cases, `cp.previous_nsource` is set to `db_beam.number_of_sources` after allocation.

### Why It Fails

When `gpu_free_all()` is called:
- If the arrays were never allocated (first call, no sources): `cudaFree()` on uninitialized pointers → assertion
- If called multiple times: double-free → assertion

## Fix

Add conditional guard using `cp.previous_nsource != 0` as the allocation flag, matching the pattern used by other array groups:

```cuda
// AFTER (fixed code):
if (cp.previous_nsource != 0) {
    gpuErr(cudaFree(cp.cu_sourceI_scale));
    gpuErr(cudaFree(cp.cu_sourceI_grad));
    cp.previous_nsource = 0;
}
```

## Patch File

**Location**: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/diffBraggCUDA_cu_line708_fix.patch`

**Apply command**:
```bash
cd /home/ollie/Documents/easyBragg/simtbx_project
patch -p1 < /home/ollie/Documents/diffbragg_example_2/diffbragg_example/plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/diffBraggCUDA_cu_line708_fix.patch
```

**Verify**:
```bash
grep -A 5 "if (cp.Fhkl_grad_arrays_allocated)" simtbx/diffBragg/src/diffBraggCUDA.cu | tail -8
```

Expected output after patch:
```cuda
    if (cp.previous_nsource != 0) {
        gpuErr(cudaFree(cp.cu_sourceI_scale));
        gpuErr(cudaFree(cp.cu_sourceI_grad));
        cp.previous_nsource = 0;
    }
```

## Rebuild Steps

### Prerequisites

- CUDA Toolkit (nvcc compiler)
- CMake >= 3.15
- C++ compiler (g++/clang++)
- Python 3.9 (simtbx environment active)

### Build Commands

```bash
# Navigate to simtbx build directory
cd /home/ollie/Documents/easyBragg/simtbx_project

# If build directory exists, clean it
if [ -d build ]; then
    rm -rf build
fi

# Create fresh build directory
mkdir build && cd build

# Configure with CMake (adjust paths as needed)
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=86 \
    -DPYTHON_EXECUTABLE=$(which python3)

# Build (adjust -j flag based on CPU cores)
make -j8

# Install to conda environment
make install
```

### Alternative: Build in-place

If CMake is not available or simtbx uses a different build system:

```bash
cd /home/ollie/Documents/easyBragg/simtbx_project
python setup.py build_ext --inplace
```

## Testing

### Minimal test script

```python
import numpy as np
from simtbx.modeling.forward_models import diffBragg_forward
from dxtbx.model import ExperimentList

# Load experiment
el = ExperimentList.from_file("refGeom.expt", check_format=False)
expt = el[0]

# Minimal forward pass (should not crash)
result = diffBragg_forward(
    CRYSTAL=expt.crystal,
    DETECTOR=expt.detector,
    BEAM=expt.beam,
    Famp=None,  # Will use default_F
    energies=[12398.4],
    fluxes=[1e12],
    device_Id=0,
    cuda=True,
    default_F=100,
    Ncells_abc=(10, 10, 10)
)

print(f"Success! Forward pass produced shape: {result.shape}")
```

**Expected**: No CUDA assertion, returns 3D array

## Environment Tagging

After successful rebuild and test:

```bash
# Create environment tag file
cat > /home/ollie/miniconda3/envs/simtbx/.environment_patches << 'EOF'
simtbx-patched-diffbraggCUDA708
Date: 2025-10-29
Patch: diffBraggCUDA_cu_line708_fix.patch
Issue: DIFFBRAGG-001 - gpu_free_all unconditional cudaFree
Source: /home/ollie/Documents/easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu:708-709
EOF
```

## Verification Checklist

- [ ] Patch file created and saved
- [ ] Patch applies cleanly (no conflicts)
- [ ] Rebuild completes without errors
- [ ] Extension loads in Python (`import simtbx_diffBragg_ext`)
- [ ] Minimal forward pass test succeeds
- [ ] Full canonical capture script succeeds
- [ ] Environment tagged
- [ ] DIFFBRAGG-001 finding updated with patch status

## Rollback

If the patch causes issues:

```bash
# Revert patch
cd /home/ollie/Documents/easyBragg/simtbx_project
patch -R -p1 < /path/to/diffBraggCUDA_cu_line708_fix.patch

# Rebuild original version
cd build && make clean && make -j8 && make install

# Remove environment tag
rm /home/ollie/miniconda3/envs/simtbx/.environment_patches
```

## References

- **Finding**: DIFFBRAGG-001 (docs/findings.md:16)
- **Policy**: POLICY-001 (docs/findings.md:15)
- **Blocking issue**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/blocking_summary.md
- **Source file**: /home/ollie/Documents/easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu

