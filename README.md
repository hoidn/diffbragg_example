# Single Image Optimization Benchmark

## Setup Instructions

### 1. Configure simtbx Environment
Set up the environment as described in the [easyBragg guide](https://smb.slac.stanford.edu/~dermen/easybragg/). Verify GPU functionality by running the example script:

```bash
cd easyBragg
python example.py
```

This should generate two visualization plots.

### 2a. Install DIALS and MPI4PY
Confirm the simtbx installation, then add required packages:

```bash
python -c "from simtbx.nanoBragg import nanoBragg;N=nanoBragg()"
mamba install -c conda-forge openmpi mpi4py dials -y
python -c "import dials"
```

### 2b. Install XFEL Module
Clone and build the xfel project:

```bash
git clone https://github.com/pixel-modelers/xfel_project.git
cd xfel_project
cmake -B build .
make -C build -j4 install
pip install -e .
```

### 3. Install the Scorer
Download the benchmarking tool and associated model:

```bash
git clone https://github.com/pixel-modelers/score_trainer.git
cd score_trainer
pip install -e .
score.getMod
```

### 4. Obtain Data Files
Download test data including mask, structure factors, configuration, and sample images:

```bash
wget https://smb.slac.stanford.edu/~dermen/dbex/747_mask.pkl
wget https://smb.slac.stanford.edu/~dermen/dbex/scaled.mtz
wget https://smb.slac.stanford.edu/~dermen/dbex/stills_proc.phil
wget https://smb.slac.stanford.edu/~dermen/dbex/refGeom.expt
wget https://smb.slac.stanford.edu/~dermen/dbex/lys_nitr_10_6_000{1,2,3}.cbf
```

Verify file integrity:

```bash
dials.image_viewer lys_nitr_10_6_0001.cbf mask=747_mask.pkl show_mask=True brightness=30
```

### 5. Run DIALS Still Processing
Generate initial structural model:

```bash
dials.stills_process stills_proc.phil lys_nitr_10_6_*cbf \
  input.reference_geometry=refGeom.expt output_dir=sp.proc \
  dispatch.integrate=False
```

### 6. Install dbex
Install the diffBragg example package:

```bash
git clone https://github.com/pixel-modelers/diffbragg_example.git
cd diffbragg_example
pip install -e .
```

### 7. Fit an Image
Process images using diffBragg with GPU acceleration:

```bash
DIFFBRAGG_USE_CUDA=1 python -m dbex.refine_one \
  -e sp.proc/idx-0000_refined.expt \
  -r sp.proc/idx-0000_indexed.refl \
  -i 0 -o dbex_0000_0.h5 -m 747_mask.pkl -z scaled.mtz
```

Visualize results:

```bash
python -m dbex.look dbex_0000_0.h5
```

Use arrow keys to navigate modeled regions. Left plots show data; right plots display model predictions.

### 8. Next Steps
Replace the `Bragg = run_diffbragg(DL)` routine in `dbex/refine_one.py` with a PyTorch-based implementation for performance benchmarking.
