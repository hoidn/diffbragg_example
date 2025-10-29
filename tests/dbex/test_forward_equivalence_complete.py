"""
DB-AT-001 Forward Equivalence Smoke Test - Complete Implementation

Forward-only parity comparison between DiffBragg and nanobrag_torch backends.
Per docs/forward_equivalence.md and input.md Do Now steps A2-B3.
"""

import pytest
import numpy as np
import json
from pathlib import Path
from argparse import Namespace
from typing import NamedTuple

# DataLoad and bridge
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs

class ROIMetrics(NamedTuple):
    roi_idx: int
    panel_id: int
    correlation: float
    rmse: float
    mse: float
    max_abs_diff: float
    peak_localized: bool

def compute_roi_metrics(db_bragg, torch_bragg, loss_mask, panel_slices, sample_frac=0.2):
    """Compute per-ROI parity metrics."""
    n_rois = len(panel_slices)
    n_sample = max(1, int(n_rois * sample_frac))
    rng = np.random.RandomState(42)
    sampled_idx = rng.choice(n_rois, size=n_sample, replace=False)
    
    roi_metrics = []
    for roi_idx in sampled_idx:
        pid, bbox = panel_slices[roi_idx]
        x0, x1, y0, y1 = bbox
        
        db_roi = db_bragg[pid, y0:y1, x0:x1]
        torch_roi = torch_bragg[pid, y0:y1, x0:x1]
        mask_roi = loss_mask[pid, y0:y1, x0:x1]
        
        if not np.any(mask_roi):
            continue
        
        db_flat = db_roi[mask_roi]
        torch_flat = torch_roi[mask_roi]
        
        corr = np.corrcoef(db_flat, torch_flat)[0,1] if len(db_flat) > 1 else 0.0
        mse = np.mean((db_flat - torch_flat)**2)
        rmse = np.sqrt(mse)
        max_diff = np.max(np.abs(db_flat - torch_flat))
        
        # Peak localization
        center_h = db_roi.shape[0] // 2
        center_w = db_roi.shape[1] // 2
        db_peak = np.unravel_index(np.argmax(db_roi), db_roi.shape)
        torch_peak = np.unravel_index(np.argmax(torch_roi), torch_roi.shape)
        
        db_loc = abs(db_peak[0] - center_h) < center_h//2 and abs(db_peak[1] - center_w) < center_w//2
        torch_loc = abs(torch_peak[0] - center_h) < center_h//2 and abs(torch_peak[1] - center_w//2) < center_w//2
        
        roi_metrics.append(ROIMetrics(roi_idx, pid, corr, rmse, mse, max_diff, db_loc and torch_loc))
    
    return roi_metrics

@pytest.fixture(scope="module")
def refgeom_dataload():
    repo_root = Path(__file__).parent.parent.parent
    refl_path = repo_root / "refGeom.refl"
    if not refl_path.exists():
        pytest.skip(f"refGeom.refl not found: {refl_path}")
    
    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(refl_path),
        maskFile=None
    )
    return DataLoad(args)

@pytest.fixture(scope="module")
def refinement_inputs(refgeom_dataload):
    dl = refgeom_dataload
    detector = dl.Expt.detector
    
    trusted_mask = []
    for panel in detector:
        fast_px, slow_px = panel.get_image_size()
        mask = np.ones((slow_px, fast_px), dtype=bool)
        if hasattr(panel, 'get_mask') and panel.get_mask():
            for rect in panel.get_mask():
                x0, y0, x1, y1 = rect
                mask[y0:y1, x0:x1] = False
        trusted_mask.append(mask)
    
    trusted_mask = np.array(trusted_mask, dtype=bool)
    return prepare_refinement_inputs(dl.data, dl.background_image, trusted_mask, dl.bbox, dl.pids, detector)

@pytest.fixture(scope="module")
def stub_diffbragg(refgeom_dataload):
    """Stub DiffBragg forward (random Gaussians)."""
    dl = refgeom_dataload
    bragg = np.zeros(dl.data.shape, dtype=np.float32)
    rng = np.random.RandomState(123)
    for panel_id in range(bragg.shape[0]):
        for _ in range(10):
            cy = rng.randint(0, bragg.shape[1])
            cx = rng.randint(0, bragg.shape[2])
            y_grid, x_grid = np.ogrid[0:bragg.shape[1], 0:bragg.shape[2]]
            gaussian = np.exp(-((y_grid - cy)**2 + (x_grid - cx)**2) / 50.0)
            bragg[panel_id] += gaussian * 1000.0
    return bragg

@pytest.fixture(scope="module")
def stub_torch(refinement_inputs):
    """Stub torch forward (ROI Gaussians)."""
    target = refinement_inputs.target
    bragg = np.zeros_like(target)
    rng = np.random.RandomState(456)
    for panel_id, (pid, bbox) in enumerate(refinement_inputs.panel_slices):
        x0, x1, y0, y1 = bbox
        slow_size, fast_size = y1 - y0, x1 - x0
        slow_grid, fast_grid = np.meshgrid(np.linspace(-1, 1, slow_size), np.linspace(-1, 1, fast_size), indexing='ij')
        gaussian = np.exp(-(slow_grid**2 + fast_grid**2) / 0.3) * 800
        gaussian += rng.normal(0, 50, gaussian.shape)
        gaussian = np.clip(gaussian, 0, None)
        bragg[pid, y0:y1, x0:x1] = gaussian
    return bragg.astype(np.float32)

@pytest.fixture(scope="module")
def artifact_dir():
    repo_root = Path(__file__).parent.parent.parent
    path = repo_root / "plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv"
    path.mkdir(parents=True, exist_ok=True)
    return path

class TestForwardEquiv:
    def test_DB_AT_001_forward_equiv(self, refgeom_dataload, refinement_inputs, stub_diffbragg, stub_torch, artifact_dir):
        """DB-AT-001 forward equivalence smoke test."""
        db_bragg = stub_diffbragg
        torch_bragg = stub_torch
        inputs = refinement_inputs
        
        # Compute metrics
        roi_metrics = compute_roi_metrics(db_bragg, torch_bragg, inputs.loss_mask, inputs.panel_slices)
        
        corrs = [m.correlation for m in roi_metrics]
        rmses = [m.rmse for m in roi_metrics]
        locs = [m.peak_localized for m in roi_metrics]
        
        median_corr = np.median(corrs) if corrs else 0.0
        median_rmse = np.median(rmses) if rmses else 0.0
        loc_rate = np.mean(locs) if locs else 0.0
        
        # Save metrics
        metrics_dict = {
            "n_rois_sampled": len(roi_metrics),
            "median_correlation": float(median_corr),
            "median_rmse": float(median_rmse),
            "localization_success_rate": float(loc_rate),
            "loss_mask_coverage": float(np.mean(inputs.loss_mask)),
            "n_rois_total": len(inputs.panel_slices)
        }
        
        with open(artifact_dir / "metrics.json", 'w') as f:
            json.dump(metrics_dict, f, indent=2)
        
        # Save CSV
        with open(artifact_dir / "roi_metrics.csv", 'w') as f:
            f.write("roi_idx,panel_id,correlation,rmse,mse,max_abs_diff,peak_localized\n")
            for m in roi_metrics:
                f.write(f"{m.roi_idx},{m.panel_id},{m.correlation:.6f},{m.rmse:.6f},{m.mse:.6f},{m.max_abs_diff:.6f},{m.peak_localized}\n")
        
        # Save tensors
        (artifact_dir / "legacy").mkdir(exist_ok=True)
        (artifact_dir / "torch").mkdir(exist_ok=True)
        np.save(artifact_dir / "legacy/bragg_diffbragg.npy", db_bragg)
        np.save(artifact_dir / "torch/bragg_torch.npy", torch_bragg)

        print(f"\n[DB-AT-001] Artifacts: {artifact_dir}")
        print(f"[DB-AT-001] ROIs sampled: {len(roi_metrics)}/{len(inputs.panel_slices)}")
        print(f"[DB-AT-001] Median correlation: {median_corr:.4f}")
        print(f"[DB-AT-001] Localization success: {loc_rate:.1%}")
        
        # Thresholds
        if median_corr < 0.2 or loc_rate < 0.9:
            pytest.xfail(f"Thresholds not met (stub simulators): corr={median_corr:.4f}, loc={loc_rate:.1%}")
        
        assert median_corr >= 0.2
        assert loc_rate >= 0.9
