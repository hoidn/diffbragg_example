# Stage A Refinement — How to Run It

## 1. What Stage A Does

Stage A is the “geometry + scale” refinement stage of the nanobrag_torch backend. It optimizes:

- Global scale (`log_scale`)
- Unit cell lengths (`a, b, c`) and angles (`α, β, γ`)
- Crystal orientation (via a bounded quaternion parameterization)

against a variance‑weighted chi‑squared loss:

- `L = Σ (I_model − I_obs)^2 / V_detached`
- `V = I_model + sigma_readout^2`, clamped by `sigma_floor^2`

Inputs are background‑subtracted targets and trusted masks in `[panel, slow, fast]` order (see `docs/spec-db-core.md` and `docs/spec-db-vis.md`).

---

## 2. Prerequisites

Environment:

- Activate the simtbx / DBEX environment that has `nanobrag_torch` and `dials` installed.
- Recommended environment variables:

  ```bash
  export KMP_DUPLICATE_LIB_OK=TRUE
  export NANOBRAGG_DISABLE_COMPILE=1  # force eager mode, avoids Torch compile noise
  ```

Canonical data assets (repo root):

- `refGeom.expt`, `refGeom.refl` — canonical DIALS experiment + reflections
- `scaled.mtz` — structure factors
- `747_mask.pkl` — detector trusted mask

Refined fixture assets (preferred for mapping/parity):

- `tests/fixtures/golden_data/simple_cubic/refined.expt`
- `tests/fixtures/golden_data/simple_cubic/refined.refl`
- `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz`
- `tests/fixtures/golden_data/simple_cubic/config_torch.json`

Optional sigma map:

- External lookup in `sp.proc/idx-0000_sigma_metadata.expt` + `idx-0000_sigma_metadata.sigma_tiles.pkl`, or
- A CLI sigma map (see below), or
- Fallback scalar sigma if neither is present.

---

## 3. Running Stage A via the CLI (`refine_one`)

The main user‑facing entry point is the `dbex.refine_one` CLI in “nanobrag” mode. By default, it runs **Stage A only** (Stage B/C are disabled unless you later expose and enable their flags in `RefinementConfig`).

### 3.1 Basic Stage A refinement (legacy geometry)

From the repo root:

```bash
python -m dbex.refine_one \
  --backend nanobrag \
  -e refGeom.expt \
  -r refGeom.refl \
  -i 0 \
  -o stageA_refine.h5 \
  -m 747_mask.pkl \
  -z scaled.mtz \
  -c tests/fixtures/golden_data/simple_cubic/config_torch.json \
  --refined-mtz tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz \
  --device cpu \
  --sigma-floor 1.0
```

What this does:

- Loads `refGeom.expt` / `refGeom.refl` and `747_mask.pkl` via `dbex.data_load.DataLoad`.
- Uses `config_torch.json` to get calibration (`spot_scale_override`, beam flux/exposure/beamsize, N_cells).
- Prefers refined structure factors from `refined_structure_factors.mtz` (falls back to `scaled.mtz` if needed).
- Resolves `sigma_readout` from:
  - External lookup metadata or a CLI `--sigma-map` if present, else
  - A scalar `--sigma-rdout` / default guard.
- Runs zero‑iteration forward mapping, then Stage A LBFGS refinement via `run_nanobrag_refinement` with a default `RefinementConfig`:
  - `enable_stage_b=False`, `enable_stage_c=False`
  - `enable_hkl_interpolation` automatically enabled when the HKL grid has a halo.
- Writes ROI‑level outputs and telemetry to `stageA_refine.h5`.

To inspect the result:

```bash
python -m dbex.look stageA_refine.h5
```

This GUI shows Data|Model composites per ROI and scores.

### 3.2 Stage A with refined geometry (recommended)

To start as close as possible to the DB‑AT‑024 mapping solution:

1. Use the refined assets:

   ```bash
   EXPT=tests/fixtures/golden_data/simple_cubic/refined.expt
   REFL=tests/fixtures/golden_data/simple_cubic/refined.refl
   ```

2. Run:

   ```bash
   python -m dbex.refine_one \
     --backend nanobrag \
     -e $EXPT \
     -r $REFL \
     -i 0 \
     -o stageA_refine_refinedgeom.h5 \
     -m 747_mask.pkl \
     -z scaled.mtz \
     -c tests/fixtures/golden_data/simple_cubic/config_torch.json \
     --refined-mtz tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz \
     --device cpu \
     --sigma-floor 1.0
   ```

The flow is the same, but `DataLoad` now uses the refined experiment and reflections.

---

## 4. Running Stage A via Tests (Smoke / Mapping)

Two useful test‑level entry points:

### 4.1 Stage A smoke test (Stage A expansion)

This exercises Stage A on both small and full detector footprints, with deterministic geometry perturbations:

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Optional: force full detector
export DBEX_SMOKE_DETECTOR_SIZE=full

pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

This test:

- Loads data via the `refgeom_dataload` fixture.
- Builds `RefinementInputs` with an all‑True mask and controlled `sigma_readout`.
- Builds a haloed HKL grid with tricubic interpolation enabled.
- Uses `create_perturbed_geometry` to introduce a small, known miscalibration, then runs Stage A to see if it recovers.
- Asserts telemetry structure and (for full detector) an improvement gate.

This is the best way to quickly verify that Stage A is *functionally* healthy in this repo.

### 4.2 Zero‑iteration mapping test (DB‑AT‑024)

To validate that zero‑iteration mapping (no refinement) matches the DIALS geometry:

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBAT024_ARTIFACT_DIR=plans/active/DB-AT-024/reports/<timestamp>  # choose a directory

pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```

This test:

- Uses refined geometry, refined MTZ, and calibration metadata.
- Calls `simulate_forward_once` (no refinement) and computes per‑ROI correlation and localization.
- Asserts thresholds like `corr_median >= 0.2` and localization success rate ≥ 90%.

Use this to ensure the **starting point** for Stage A is physically reasonable.

---

## 5. Stage A Visualization Helpers (Optional)

For visual debugging of Stage A behavior on the canonical dataset, there are plan‑local helpers under TOOLING‑VIS‑001:

- Zero‑iteration triptychs (refined geometry):

  ```bash
  python plans/active/TOOLING-VIS-001/bin/generate_zero_iter_refined_roi_triptychs.py
  ```

  Outputs:
  - `plans/active/TOOLING-VIS-001/reports/stage_a_zero_iter_refined/<timestamp>/roi_XXXX_zero_iter.png`
  - `summary.md` with ROI table.

- Stage A before/after ROI triptychs (baseline geometry, Stage A refinement on CPU):

  ```bash
  python plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs.py
  ```

  Outputs:
  - `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom/<timestamp>/roi_triptychs/roi_XXXX_{before,after}.png`
  - `summary.md` listing ROI bbox, CC_before, CC_after, and PNG names.

These helpers are not part of the public CLI, but they are useful for diagnosing how Stage A moves peaks ROI‑by‑ROI.

---

## 6. Summary

- Use `python -m dbex.refine_one --backend nanobrag ...` for “normal” Stage A refinement runs; results go into an HDF5 you can inspect with `dbex.look`.
- Use `test_stage_a_expansion` and DB‑AT‑024 to verify Stage A behavior and the zero‑iteration mapping against canonical thresholds.
- Optional plan‑local scripts under TOOLING‑VIS‑001 generate detailed ROI‑level before/after visuals for Stage A debugging.

