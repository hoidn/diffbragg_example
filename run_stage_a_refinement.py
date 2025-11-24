#!/usr/bin/env python
"""
Run Stage A refinement from unperturbed configuration and generate:
1. Refinement loss curve
2. ROI comparison triptychs (experimental, pre-refinement, post-refinement)

Per spec-db-workflow.md §68-95 and spec-db-conformance.md §63-100
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import h5py
from pathlib import Path

# Output directory for artifacts
OUTPUT_DIR = Path("stage_a_refinement_output")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 80)
print("Stage A Refinement from Unperturbed Configuration")
print("=" * 80)

# Step 1: Run Stage A refinement using nanobrag backend
print("\n[1/3] Running Stage A refinement with nanobrag backend...")
print("Configuration per spec-db-workflow.md §68-95:")
print("  - Geometry: refGeom.expt / refGeom.refl (canonical)")
print("  - Structure factors: scaled.mtz")
print("  - Mask: 747_mask.pkl")
print("  - Backend: nanobrag (PyTorch)")
print("  - Sigma readout: 3.0 ADU (CLI override)")

# Construct command per docs/TESTING_GUIDE.md §1.1 and spec-db-core.md §32-68
import subprocess

output_h5 = OUTPUT_DIR / "stage_a_refinement.h5"
cmd = [
    "python", "-m", "dbex.refine_one",
    "--backend", "nanobrag",
    "-e", "refGeom.expt",
    "-r", "refGeom.refl",
    "-i", "0",
    "-o", str(output_h5),
    "-m", "747_mask.pkl",
    "-z", "scaled.mtz",
    "--sigma-rdout", "3.0",  # Per spec-db-core.md §32-68: strictly positive, CLI override
    "--device", "cuda:0",
    "--report-dir", str(OUTPUT_DIR / "triptychs_auto")  # Auto-generate triptychs
]

env = os.environ.copy()
env["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # Per docs/TESTING_GUIDE.md §1.1

print(f"\nExecuting: {' '.join(cmd)}")
print(f"Environment: KMP_DUPLICATE_LIB_OK=TRUE")

try:
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=600  # 10 minute timeout
    )

    print("\n" + "=" * 80)
    print("STDOUT:")
    print("=" * 80)
    print(result.stdout)

    if result.stderr:
        print("\n" + "=" * 80)
        print("STDERR:")
        print("=" * 80)
        print(result.stderr)

    if result.returncode != 0:
        print(f"\n[ERROR] Refinement failed with return code {result.returncode}")
        sys.exit(1)

    print(f"\n[SUCCESS] Refinement completed. Output: {output_h5}")

except subprocess.TimeoutExpired:
    print("[ERROR] Refinement timed out after 10 minutes")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Failed to run refinement: {e}")
    sys.exit(1)

# Step 2: Extract and plot loss curve
print("\n[2/3] Extracting and plotting refinement loss curve...")

try:
    with h5py.File(output_h5, "r") as f:
        # Check for torch_diagnostics group per spec-db-interfaces.md
        if "torch_diagnostics" in f:
            diag = f["torch_diagnostics"]

            # Extract telemetry
            print("\nTorch diagnostics found:")
            for key in diag.attrs.keys():
                print(f"  {key}: {diag.attrs[key]}")

            # Check for Stage A telemetry
            if "stage_a" in diag:
                stage_a = diag["stage_a"]

                # Extract loss trace if available
                if "loss_trace" in stage_a.attrs:
                    loss_trace = stage_a.attrs["loss_trace"]

                    # Plot loss curve
                    plt.figure(figsize=(10, 6))
                    plt.plot(loss_trace, 'b-', linewidth=2, marker='o', markersize=4)
                    plt.xlabel("Iteration", fontsize=12)
                    plt.ylabel("Loss (Variance-Weighted χ²)", fontsize=12)
                    plt.title("Stage A Refinement Loss Curve", fontsize=14, fontweight='bold')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()

                    loss_curve_path = OUTPUT_DIR / "stage_a_loss_curve.png"
                    plt.savefig(loss_curve_path, dpi=150, bbox_inches='tight')
                    print(f"\n[SUCCESS] Loss curve saved to: {loss_curve_path}")
                    print(f"  Initial loss: {loss_trace[0]:.6e}")
                    print(f"  Final loss: {loss_trace[-1]:.6e}")
                    print(f"  Improvement: {(1 - loss_trace[-1]/loss_trace[0])*100:.2f}%")
                    plt.close()
                else:
                    print("[WARNING] No loss_trace found in stage_a diagnostics")
            else:
                print("[WARNING] No stage_a group found in torch_diagnostics")
        else:
            print("[WARNING] No torch_diagnostics group found in HDF5 output")

except Exception as e:
    print(f"[ERROR] Failed to extract loss curve: {e}")

# Step 3: Generate ROI comparison triptychs
print("\n[3/3] Generating ROI comparison triptychs...")
print("Per spec-db-vis.md §14-24: [Observed Data | Model Prediction | Residual Z-Score]")

try:
    # Check if auto-generated triptychs exist
    auto_triptych_dir = OUTPUT_DIR / "triptychs_auto"
    if auto_triptych_dir.exists():
        triptych_files = list(auto_triptych_dir.glob("roi_*.png"))
        if triptych_files:
            print(f"\n[SUCCESS] Auto-generated triptychs found: {len(triptych_files)} ROIs")
            print(f"  Location: {auto_triptych_dir}")
            print(f"  Files: {[f.name for f in sorted(triptych_files)[:5]]} ...")
        else:
            print(f"[WARNING] No triptych PNG files found in {auto_triptych_dir}")
    else:
        print(f"[WARNING] Auto-triptych directory not created: {auto_triptych_dir}")

    # Also read HDF5 directly to generate custom visualization if needed
    with h5py.File(output_h5, "r") as f:
        # Count ROIs
        n_rois = 0
        while f"data/roi{n_rois}" in f:
            n_rois += 1

        print(f"\n[INFO] Total ROIs in HDF5: {n_rois}")

        if n_rois > 0:
            # Generate a summary figure with first 3 ROIs
            from dbex.vis import plot_triptych

            fig, axes = plt.subplots(3, 3, figsize=(15, 15))
            fig.suptitle("Stage A Refinement: ROI Comparison (First 3 ROIs)",
                        fontsize=16, fontweight='bold')

            for roi_idx in range(min(3, n_rois)):
                # Load data
                data = f[f"data/roi{roi_idx}"][:]
                model = f[f"model/roi{roi_idx}"][:]

                # Load variance if available
                variance = None
                if f"variance/roi{roi_idx}" in f:
                    variance = f[f"variance/roi{roi_idx}"][:]

                # Get score if available
                score_key = f"score"
                score = f[score_key][roi_idx] if score_key in f else None

                # Plot using dbex.vis
                row_axes = axes[roi_idx, :]

                # Data panel
                im0 = row_axes[0].imshow(data, cmap='viridis', origin='upper')
                row_axes[0].set_title(f"ROI {roi_idx}: Observed Data")
                plt.colorbar(im0, ax=row_axes[0])

                # Model panel
                im1 = row_axes[1].imshow(model, cmap='viridis', origin='upper',
                                        vmin=data.min(), vmax=data.max())
                row_axes[1].set_title(f"ROI {roi_idx}: Model (Post-Refinement)")
                plt.colorbar(im1, ax=row_axes[1])

                # Residual panel
                if variance is not None:
                    from dbex.vis import compute_z_scores
                    z_scores = compute_z_scores(data, model, variance)
                    im2 = row_axes[2].imshow(z_scores, cmap='seismic', origin='upper',
                                            vmin=-3, vmax=3)
                    row_axes[2].set_title(f"ROI {roi_idx}: Residual Z-Score")
                else:
                    residual = data - model
                    im2 = row_axes[2].imshow(residual, cmap='seismic', origin='upper')
                    row_axes[2].set_title(f"ROI {roi_idx}: Residual (Data - Model)")
                plt.colorbar(im2, ax=row_axes[2])

                if score is not None:
                    row_axes[1].text(0.02, 0.98, f"CC: {score:.3f}",
                                    transform=row_axes[1].transAxes,
                                    va='top', ha='left', color='white',
                                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))

            plt.tight_layout()
            summary_path = OUTPUT_DIR / "roi_comparison_summary.png"
            plt.savefig(summary_path, dpi=150, bbox_inches='tight')
            print(f"\n[SUCCESS] ROI comparison summary saved to: {summary_path}")
            plt.close()

except Exception as e:
    print(f"[ERROR] Failed to generate triptychs: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Stage A Refinement Complete")
print("=" * 80)
print(f"\nOutput artifacts in: {OUTPUT_DIR}/")
print("  1. stage_a_refinement.h5       - HDF5 output with all ROI data")
print("  2. stage_a_loss_curve.png      - Refinement loss curve")
print("  3. roi_comparison_summary.png  - ROI triptychs (first 3 ROIs)")
print("  4. triptychs_auto/             - Individual ROI triptychs (all ROIs)")
print()
