#!/usr/bin/env python3
"""
Probe Stage B shell modifiers on canonical or small smoke datasets (initiative: PERF-WARM-SIM-001, owner: galph).
Inputs: --dataset {full,small} (default full), --sigma-source {cli,metadata}, --out /path/to/summary.json
Data deps: refGeom assets under repo root (refGeom*.{expt,refl}, masks, MTZ) and optional refGeom_small.
Outputs: JSON summary containing Stage A/B chi-squared metrics, improvement, perf counters, and param deltas.
Repro: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  python plans/active/PERF-WARM-SIM-001/bin/probe_stage_b_full.py --dataset full --out <dir>/stage_b_probe.json
"""
import argparse
import json
from argparse import Namespace
from pathlib import Path
from typing import Dict

import numpy as np
import torch

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    build_structure_factor_grid,
    prepare_refinement_inputs,
)
from dbex.nanobrag_refinement import RefinementConfig, run_nanobrag_refinement


def _resolve_dataset_paths(repo: Path, dataset: str) -> Dict[str, Path]:
    if dataset == "small":
        base = repo / "sp.proc" / "refGeom_small"
        return {
            "expt": base / "refGeom_small.expt",
            "refl": base / "refGeom_small.refl",
            "mask": base / "refGeom_small_mask.pkl",
        }
    return {
        "expt": repo / "refGeom.expt",
        "refl": repo / "refGeom.refl",
        "mask": repo / "747_mask.pkl",
    }


def _build_inputs(dataload: DataLoad, sigma_source: str):
    detector = dataload.Expt.detector
    trusted_masks = []
    for pid in range(len(detector)):
        slow, fast = detector[pid].get_image_size()[::-1]
        trusted_masks.append(np.ones((slow, fast), dtype=bool))

    if sigma_source == "metadata":
        sigma_map = getattr(dataload, "sigma_readout_map", None)
        if sigma_map is None:
            raise FileNotFoundError("Metadata sigma map missing; run embed_sigma_external_lookup.py")
        sigma_array = np.asarray(sigma_map, dtype=np.float32)
    else:
        sigma_array = np.full_like(dataload.data, 3.0, dtype=np.float32)

    return prepare_refinement_inputs(
        data=dataload.data,
        background_image=dataload.background_image,
        trusted_mask=trusted_masks,
        bbox=dataload.bbox,
        pids=dataload.pids,
        detector=dataload.Expt.detector,
        adu_per_photon=None,
        sigma_readout=sigma_array,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Probe Stage B shell modifiers on refGeom datasets")
    ap.add_argument("--dataset", choices=["full", "small"], default="full")
    ap.add_argument("--sigma-source", choices=["cli", "metadata"], default="cli")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[4]
    ds = _resolve_dataset_paths(repo, args.dataset)
    paths = [ds["expt"], ds["refl"], ds["mask"], repo / "scaled.mtz"]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing dataset assets: {missing}")

    dataload = DataLoad(
        Namespace(
            exptName=str(ds["expt"]),
            reflName=str(ds["refl"]),
            exptIdx=0,
            maskFile=str(ds["mask"]),
            mtzFile=str(repo / "scaled.mtz"),
            mtzCol="F,SIGF",
        )
    )

    refinement_inputs = _build_inputs(dataload, args.sigma_source)

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=dataload.F.indices(),
        amplitudes=dataload.F.data(),
        device=torch.device("cuda:0"),
        halo=True,
    )

    config = RefinementConfig(
        enable_hkl_interpolation=True,
        enable_stage_b=True,
        stage_b_n_shells=5,
        enable_stage_c=False,
        device="cuda:0",
        dtype=torch.float32,
        sigma_readout_provenance=(
            "external_lookup" if args.sigma_source == "metadata" else "cli_override"
        ),
    )

    bragg_refined, telemetry = run_nanobrag_refinement(
        inputs=refinement_inputs,
        detector=dataload.detector,
        beam=dataload.beam,
        crystal=dataload.crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config,
        baseline_detector=dataload.detector,
    )

    telemetry_a = telemetry["A"]
    telemetry_b = telemetry["B"]

    stage_a_trace = telemetry_a.chi_squared_trace_full
    stage_a_final = stage_a_trace[-1][1]
    stage_a_initial = stage_a_trace[0][1]
    stage_b_final = telemetry_b.chi_squared_trace_full[-1][1]
    improvement = (stage_a_final - stage_b_final) / stage_a_final

    perf = telemetry_b.perf_counters or {}
    param_deltas = {k: float(v) for k, v in telemetry_b.param_deltas.items()}

    summary = {
        "dataset": args.dataset,
        "sigma_source": args.sigma_source,
        "n_rois": len(dataload.bbox),
        "stage_a_initial_chi_squared": float(stage_a_initial),
        "stage_a_final_chi_squared": float(stage_a_final),
        "stage_b_final_chi_squared": float(stage_b_final),
        "improvement_fraction": float(improvement),
        "perf_counters": perf,
        "param_deltas": param_deltas,
        "stage_a_chi_squared_trace_full": stage_a_trace,
        "chi_squared_trace_full": telemetry_b.chi_squared_trace_full,
        "bragg_shape": tuple(int(x) for x in bragg_refined.shape),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
