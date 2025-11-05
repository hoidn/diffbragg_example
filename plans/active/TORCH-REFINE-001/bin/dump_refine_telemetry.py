#!/usr/bin/env python3
"""
Dump Stage A refinement telemetry from the torch backend HDF5 (initiative: TORCH-REFINE-001, owner: galph).
Inputs: --h5 path to output HDF5    Data deps: tmp/torch_refine_stage_a.h5
Outputs: JSON under plans/active/TORCH-REFINE-001/reports/<timestamp>/telemetry_snapshot.json
Repro: python plans/active/TORCH-REFINE-001/bin/dump_refine_telemetry.py --h5 tmp/torch_refine_stage_a.h5 --output plans/active/TORCH-REFINE-001/reports/<timestamp>/telemetry_snapshot.json
"""

import argparse
import json
from pathlib import Path

import h5py


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract /torch_diagnostics telemetry into JSON.")
    parser.add_argument(
        "--h5",
        required=True,
        help="Path to the torch refine HDF5 produced by dbex.refine_one (--backend nanobrag).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Destination JSON file path (will be created or overwritten).",
    )
    args = parser.parse_args()

    h5_path = Path(args.h5)
    if not h5_path.exists():
        raise SystemExit(f"HDF5 file not found: {h5_path}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(h5_path, "r") as handle:
        if "torch_diagnostics" not in handle:
            raise SystemExit("HDF5 file missing 'torch_diagnostics' group.")

        diag = handle["torch_diagnostics"]
        payload = {"attrs": {key: diag.attrs[key] for key in diag.attrs}}

        for name in diag.keys():
            dataset = diag[name]
            data = dataset[()]
            if getattr(data, "shape", ()) == ():
                payload[name] = data.item() if hasattr(data, "item") else data
            else:
                payload[name] = data.tolist()

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"Wrote telemetry JSON to {output_path}")


if __name__ == "__main__":
    main()
