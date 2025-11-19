# spec-db-vis.md — Visual Diagnostics (Normative)

Overview (Normative)
- Purpose: Define standard visual artifacts for verifying refinement quality.
- Scope: Residual maps, ROI triptychs, and scatter plots.

Coordinate Systems (Normative)
- Images SHALL be displayed in `(slow, fast)` matrix coordinates.
- Origin `(0, 0)` is top-left.
- Fast axis is horizontal (left→right).
- Slow axis is vertical (top→bottom).

Standard Artifacts (Normative)

1. ROI Triptych
   - Layout: Three panels horizontally `[Observed Data | Model Prediction | Residual Z-Score]`.
   - Scaling:
     - Data/Model: Shared colormap range `[0, max(data, model)]`. Log scaling is optional but MUST be labeled.
     - Residuals: Z-score map `(Data - Model) / sqrt(Variance)`.
   - Colormaps:
     - Intensity: Perceptually uniform sequential (e.g., Viridis, Cividis).
     - Residuals: Diverging (e.g., Blue-White-Red or PiYG) centered at 0.
   - Annotation: Each ROI MUST be labeled with its HKL index and correlation coefficient (CC).

2. Residual Histogram
   - Histogram of Z-scores across all trusted pixels.
   - Overlay: Standard normal curve (`μ=0`, `σ=1`).
   - Purpose: Validates the noise model; skew or width deviations indicate modeling errors.

3. Radial Profile
   - X-axis: Inverse resolution squared (`1/d^2`) in Å\(^{-2}\).
   - Y-axis: Average intensity (`I_model` vs `I_obs`).
   - Purpose: Detects resolution-dependent scaling errors (e.g., B-factor mismatch).

Terminology (Normative)
- `I_model`: Simulated intensity (Bragg + background).
- `I_obs`: Observed experimental data.
- `Residual`: `I_obs - I_model`.

File Formats (Normative)
- Static reports SHALL be saved as PNG (lossless) or PDF (vector).
- Interactive data SHALL be saved as HDF5 following the layout in `spec-db-interfaces.md`.
