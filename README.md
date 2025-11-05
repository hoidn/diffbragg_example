# Single Image Optimization Benchmark

## Prerequisites

**System Requirements:**
- Linux x86_64 with NVIDIA GPU (CUDA-capable) **REQUIRED for full workflow**
- macOS ARM64/Intel supported for setup and testing only (see limitations below)
- ~3GB disk space for conda environment and packages
- cmake 3.10 or higher
- wget or curl
- git

**⚠️ IMPORTANT: GPU/CUDA Limitations**
- **CUDA/GPU is REQUIRED** for the final diffBragg forward model step
- CPU-only mode will complete refinement but **crash before generating visualization files**
- macOS users can complete steps 1-6 for development/testing, but step 7 requires Linux+CUDA
- If you encounter `SCITBX_ASSERT(DIFFBRAGG_USE_KOKKOS_and_DIFFBRAGG_USE_CUDA_flags_unsupported)` error, you need a CUDA-capable GPU

**Estimated Time:**
- Initial setup: 30-45 minutes
- Per-image refinement: 2-5 minutes (GPU), 5-15 minutes (CPU, will crash at end)

## Quick Start

```bash
# Clone this repository (if not already done)
git clone https://github.com/pixel-modelers/diffbragg_example.git
cd diffbragg_example

# The simtbx environment is pre-activated with all required packages
# Continue with steps 4-7 below
```

> **Note:** The environment uses torch==2.4.1+cu121 by default. Keep that version; upgrading torch or torchvision will reintroduce the CUDA runtime mismatch and break DiffBragg.

## Detailed Setup Instructions

### Directory Structure
This guide assumes the following structure:
```
diffbragg_example/
├── easyBragg/           # Created in step 1
├── dbex/                # Part of this repo
├── simforge/            # Conda environment (created in step 1)
└── README.md            # This file
```

---

### Step 1: Configure simtbx Environment

**Working Directory:** `diffbragg_example/`

Set up the environment as described in the [easyBragg guide](https://smb.slac.stanford.edu/~dermen/easybragg/).

<details>
<summary>Click to expand full easyBragg installation steps</summary>

```bash
# Detect platform
PLATFORM=$(uname -m)
if [[ "$PLATFORM" == "arm64" ]]; then
    INSTALLER="Miniforge3-MacOSX-arm64.sh"
elif [[ "$PLATFORM" == "x86_64" ]]; then
    if [[ "$(uname)" == "Darwin" ]]; then
        INSTALLER="Miniforge3-MacOSX-x86_64.sh"
    else
        INSTALLER="Miniforge3-Linux-x86_64.sh"
    fi
fi

# Download and install Miniforge3
wget https://github.com/conda-forge/miniforge/releases/latest/download/$INSTALLER
bash ./$INSTALLER -b -u -p "$PWD/simforge"

# Create simtbx environment
./simforge/bin/mamba create -n simtbx -c conda-forge \
    cctbx-base libboost-devel libboost-python-devel dxtbx python=3.9 cmake -y

# Install build tools
./simforge/envs/simtbx/bin/pip install build

# Clone and build easyBragg
git clone --recurse-submodules https://github.com/pixel-modelers/easyBragg.git
cd easyBragg

export PATH=$PWD/../simforge/envs/simtbx/bin:$PATH
export CONDA_PREFIX=$PWD/../simforge/envs/simtbx

# Configure with policy flag (REQUIRED)
cmake -B build_ext -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .

# Build and install
make -C build_ext -j4 install

# Build Python package
python -m build

# Install Python package
pip install dist/simtbx-0.1.tar.gz
```
</details>

**Verify installation:**
```bash
cd easyBragg
python -c "from simtbx.nanoBragg import nanoBragg; N=nanoBragg(); print('✓ simtbx.nanoBragg working')"
```

**Optional: Test GPU/CPU functionality** (generates plots, may take ~30 seconds):
```bash
python example.py
```
Expected: Two visualization plots showing diffraction simulation.

**Expected Output:**
- `easyBragg/ext/simtbx_nanoBragg_ext.so`
- `easyBragg/ext/simtbx_diffBragg_ext.so`
- `simforge/envs/simtbx/lib/python3.9/site-packages/simtbx/`

---

### Step 2a: Install DIALS and MPI4PY

**Working Directory:** `diffbragg_example/easyBragg/`

**⚠️ Note:** This will downgrade some packages (pillow, libtiff, libjpeg-turbo, lcms2, openjpeg) to versions compatible with DIALS.

```bash
# Ensure environment is activated
export PATH=$PWD/../simforge/envs/simtbx/bin:$PATH
export CONDA_PREFIX=$PWD/../simforge/envs/simtbx

# Install DIALS and MPI
mamba install -c conda-forge openmpi mpi4py dials -y
```

**Verify installation:**
```bash
python -c "import dials; print('✓ DIALS working')"
python -c "from mpi4py import MPI; print('✓ MPI4PY working')"
```

**Expected Output:**
- `dials.stills_process` command available
- MPI4PY importable

---

### Step 2b: Install XFEL Module

**Working Directory:** `diffbragg_example/easyBragg/`

```bash
# Clone xfel_project
git clone https://github.com/pixel-modelers/xfel_project.git
cd xfel_project

# Configure with policy flag (REQUIRED)
cmake -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .

# Build and install
make -C build -j4 install

# Install Python package in editable mode
pip install -e .

cd ..  # Return to easyBragg directory
```

**Verify installation:**
```bash
python -c "import xfel; print('✓ XFEL module working')"
```

**Expected Output:**
- `simforge/envs/simtbx/lib/python3.9/site-packages/xfel_ext.so`
- Various `sx_*.so` and other extension modules

---

### Step 3: Install Score Trainer (with pinned PyTorch)

**Working Directory:** `diffbragg_example/easyBragg/`

**⚠️ IMPORTANT:** DiffBragg currently requires the CUDA 12.1 PyTorch build. Do **not** upgrade or change the torch/torchvision versions installed here.

```bash
# Clone score_trainer
git clone https://github.com/pixel-modelers/score_trainer.git
cd score_trainer

# Install pinned PyTorch + torchvision (CUDA 12.1 build)
pip install --no-cache-dir torch==2.4.1+cu121 torchvision==0.19.1+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install score_trainer (will reuse pinned torch)
pip install -e .

# Download pre-trained model
score.getMod
```

**Verify installation:**
```bash
python -c "import torch; from score_trainer import roi_check; \
print(f'✓ Score trainer working (torch {torch.__version__}, CUDA {torch.version.cuda})')"
ls -lh score_trainer/state_ep10.net  # Should show ~68KB model file
```

**Expected Output:**
- `score_trainer/score_trainer/state_ep10.net` (68KB)
- PyTorch and torchvision installed

```bash
cd ..  # Return to easyBragg directory
```

---

### Step 4: Obtain Data Files

**Working Directory:** `diffbragg_example/easyBragg/`

Download test data including mask, structure factors, configuration, and sample images:

```bash
wget https://smb.slac.stanford.edu/~dermen/dbex/747_mask.pkl
wget https://smb.slac.stanford.edu/~dermen/dbex/scaled.mtz
wget https://smb.slac.stanford.edu/~dermen/dbex/stills_proc.phil
wget https://smb.slac.stanford.edu/~dermen/dbex/refGeom.expt
wget https://smb.slac.stanford.edu/~dermen/dbex/lys_nitr_10_6_0001.cbf
wget https://smb.slac.stanford.edu/~dermen/dbex/lys_nitr_10_6_0002.cbf
wget https://smb.slac.stanford.edu/~dermen/dbex/lys_nitr_10_6_0003.cbf
```

**Expected Output:**
- `747_mask.pkl` (~6MB) - Detector mask
- `scaled.mtz` (~3MB) - Reference structure factors
- `stills_proc.phil` (~300B) - DIALS configuration
- `refGeom.expt` (~5KB) - Reference geometry
- `lys_nitr_10_6_000[1-3].cbf` (~6MB each) - Diffraction images

**Optional: Verify file integrity** (requires X11 forwarding or display):
```bash
# This opens a GUI viewer - skip if running headless
dials.image_viewer lys_nitr_10_6_0001.cbf mask=747_mask.pkl show_mask=True brightness=30
```

---

### Step 5: Run DIALS Still Processing

**Working Directory:** `diffbragg_example/easyBragg/`

Generate initial structural model from diffraction images:

```bash
dials.stills_process stills_proc.phil lys_nitr_10_6_*cbf \
  input.reference_geometry=refGeom.expt output_dir=sp.proc \
  dispatch.integrate=False
```

This will:
1. Find strong spots in each image
2. Index the diffraction patterns
3. Refine crystal orientation and unit cell

**Expected Output:**
```
sp.proc/
├── idx-0000_indexed.refl  (~200KB) - Indexed reflections
├── idx-0000_refined.expt  (~23KB)  - Refined experiment geometry
└── debug/                           - Debug logs
```

**Verify success:**
```bash
ls -lh sp.proc/idx-0000_*
# Should show both .refl and .expt files
```

**Expected console output:**
```
Indexed using 100% of the reflections
Time Taken = 1.1 seconds
Saving 282 reflections to sp.proc/idx-0000_indexed.refl
```

---

### Step 6: Install dbex Package

**Working Directory:** `diffbragg_example/` (parent directory!)

**⚠️ Important:** This must be run from the repository root, not from `easyBragg/`

```bash
cd ..  # Move to diffbragg_example/ if currently in easyBragg/

pip install -e .
```

**Verify installation:**
```bash
python -c "import dbex; print('✓ dbex package working')"
python -m dbex.refine_one --help  # Should show usage information
```

**Expected Output:**
- `dbex` package importable
- `python -m dbex.refine_one` command available

---

### Step 7: Fit an Image with diffBragg (GPU mode)

**Working Directory:** `diffbragg_example/easyBragg/`

**⚠️ CRITICAL:** Use the pinned CUDA 12.1 PyTorch build installed in Step 3. GPU mode is required to complete the refinement.

```bash
cd easyBragg  # If not already there

# GPU mode (required for completion)
DIFFBRAGG_USE_CUDA=1 python -m dbex.refine_one \
  -e sp.proc/idx-0000_refined.expt \
  -r sp.proc/idx-0000_indexed.refl \
  -i 0 -o dbex_0000_0.h5 -m 747_mask.pkl -z scaled.mtz
```

**What this does:**
1. Loads the indexed reflections and refined geometry
2. Runs iterative diffBragg refinement (~100+ iterations)
3. Optimizes: crystal orientation, unit cell, mosaicity, intensity scale
4. Generates predicted Bragg peaks for each reflection
5. Compares model to observed data
6. Saves results to HDF5 file

**Expected Output:**
- `dbex_0000_0.h5` (~varies) - Visualization data with model/data comparison
- `_geom_ref.expt`, `_geom_ref.refl`, `_geom_ref.pkl` - Refined parameters
- `_geom.out/diffBragg_detector.expt` - Refined detector model

**Console output will show:**
```
Iteration 1:
    Resid=765267.6, sigmaZ 13.06254
...
Final Iteration 24:
    Resid=155937.4, sigmaZ 5.573092  # Lower is better
```

**Success criteria:**
- Residual decreases significantly (>50% reduction)
- SigmaZ converges to ~5-7 range
- No crashes or assertion failures
- `dbex_0000_0.h5` file created

**Verify refinement quality:**
```bash
python << 'EOF'
from dials.array_family import flex
import numpy as np

refls = flex.reflection_table.from_file('_geom_ref.refl')
obs_x = refls['xyzobs.px.value'].parts()[0]
obs_y = refls['xyzobs.px.value'].parts()[1]
cal_x = refls['xyzcal.px'].parts()[0]
cal_y = refls['xyzcal.px'].parts()[1]

errors = np.sqrt([(obs_x[i]-cal_x[i])**2 + (obs_y[i]-cal_y[i])**2 for i in range(len(refls))])
print(f"Mean prediction error: {np.mean(errors):.2f} pixels")
print(f"Median prediction error: {np.median(errors):.2f} pixels")
print("Good refinement: errors < 2-3 pixels")
EOF
```

---

### Step 8: Visualize Results

**Working Directory:** `diffbragg_example/easyBragg/`

**⚠️ Note:** Requires X11 forwarding or local display. If running on a remote server without display, you can download the h5 file and view it locally.

```bash
python -m dbex.look dbex_0000_0.h5
```

**Interactive controls:**
- Arrow keys: Navigate between modeled regions
- Left plots: Observed diffraction data
- Right plots: Model predictions from diffBragg

**Expected behavior:**
- Window opens showing data/model comparison
- Multiple ROIs (Regions of Interest) can be viewed
- Similarity scores shown for each ROI

---

## Troubleshooting

### "No module named 'dbex'" or "No module named 'simtbx'"
**Solution:** The simtbx environment should already be activated. Verify with:
```bash
python -c "import simtbx; import dbex; print('Environment OK')"
dbex_status  # Shows detailed package status
```

### "cmake: Compatibility with CMake < 3.5 has been removed"
**Solution:** Add the policy flag to cmake command:
```bash
cmake -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .
```

### "SCITBX_ASSERT(DIFFBRAGG_USE_KOKKOS_and_DIFFBRAGG_USE_CUDA_flags_unsupported) failure"
**Problem:** You're trying to run on CPU-only or macOS (no CUDA support)
**Solution:**
- This is a known limitation - **GPU/CUDA is required** for the final forward model step
- The refinement completes successfully and generates `_geom_ref.*` files
- But the h5 visualization file cannot be created without CUDA
- For full workflow, use a Linux system with NVIDIA GPU

### "Command not found: dials.stills_process" or "score.getMod"
**Solution:** The conda environment's bin directory is not in PATH. See solution above for setting PATH.

### Package version conflicts during mamba install
**Expected:** mamba may downgrade pillow, libtiff, libjpeg-turbo, lcms2, and openjpeg to versions compatible with DIALS. This is normal and expected.

### Extremely verbose output during refinement
**Expected:** The diffBragg refinement outputs detailed debugging information for every iteration (~100,000+ lines). This is normal. To reduce clutter:
```bash
python -m dbex.refine_one [...] 2>&1 | grep -E '(Iteration|Final|Average score)'
```

### Images don't open in dials.image_viewer
**Problem:** No display/X11 forwarding
**Solution:** This step is optional for verification only. Skip if running headless.

---

## Environment Management

The simtbx conda environment is pre-activated and includes all required packages:
- simtbx (with diffBragg/nanoBragg)
- dials
- dbex
- torch 2.4.1+cu121
- nanobrag_torch 0.1.0

Backend staging policy (torch):
- Stage A (geometry + scale): the simulator uses nearest‑neighbor |F| (interpolate disabled) to avoid HKL‑grid halo/OOB artifacts while preserving geometry gradients.
- Stage B (Fhkl): tricubic interpolation enabled with a ±1 halo in the dense |F| grid; any default_F fallback is considered a failure for Stage B runs.

Helper functions available in the environment:
- `dbex_status` - Check environment status and package availability
- `dbex_test` - Run verification tests

---

## Expected Disk Usage

- Miniforge3 installation: ~500MB
- simtbx conda environment: ~1.5GB
- easyBragg build artifacts: ~200MB
- Downloaded data files: ~30MB
- PyTorch and dependencies: ~300MB

**Total: ~2.5GB**

---

## Platform Support

| Platform | Step 1-6 | Step 7 (GPU required) | Notes |
|----------|----------|----------------------|-------|
| Linux x86_64 + NVIDIA GPU | ✓ | ✓ | Full support (torch 2.4.1+cu121). |
| Linux x86_64 (CPU only) | ✓ | ✗ | Crashes during final GPU-only forward model. |
| macOS ARM64 | ✓ | ✗ | Development/testing only |
| macOS Intel | ✓ | ✗ | Development/testing only |

---

## Next Steps

Once you have successfully completed the setup and refinement:

1. **Performance Benchmarking:** Replace the `Bragg = run_diffbragg(DL)` routine in `dbex/refine_one.py` with a PyTorch-based implementation for GPU performance benchmarking.

2. **Batch Processing:** Process multiple images using the same workflow:
```bash
for i in {0..2}; do
    DIFFBRAGG_USE_CUDA=1 python -m dbex.refine_one \
        -e sp.proc/idx-0000_refined.expt \
        -r sp.proc/idx-0000_indexed.refl \
        -i $i -o dbex_0000_${i}.h5 -m 747_mask.pkl -z scaled.mtz
done
```

3. **Custom Data:** Process your own diffraction images by:
   - Running DIALS indexing on your data
   - Providing your own mask file and structure factors
   - Adjusting phil parameters as needed

---

## Reference

**Documentation:**
- [easyBragg Guide](https://smb.slac.stanford.edu/~dermen/easybragg/)
- [DIALS Documentation](https://dials.github.io/)
- [diffBragg Paper](https://journals.iucr.org/m/issues/2022/01/00/ei5060/)

**Citations:**
If you use this software, please cite:
- DIALS: Winter et al. (2018) Acta Cryst. D74, 85-97
- diffBragg: Mendez et al. (2020) IUCrJ 7, 1151-1167

**Support:**
- Issues: https://github.com/pixel-modelers/diffbragg_example/issues
- Discussion: https://github.com/pixel-modelers/diffbragg_example/discussions
