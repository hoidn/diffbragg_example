# Phase C.5 Documentation Alignment Summary

**Date**: 2025-12-02T094947Z
**Focus**: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split (docs alignment)
**Mode**: Docs

## Problem & SPEC/ARCH alignment

Updated documentation to reflect the Phase C modular split of `dbex/nanobrag_bridge.py` responsibilities into:
- `dbex/refinement/inputs.py` (RefinementInputs dataclass + prepare_refinement_inputs)
- `dbex/refinement/config_factories.py` (create_detector_config, create_beam_config, create_crystal_config)
- `dbex/nanobrag_bridge.py` (orchestration + HKL helpers)

Per the bridge_split_summary.md (plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T020500Z/), the code split was completed in Phase C.2-C.3 with all tests passing. This loop ensures documentation references are consistent with the new module structure.

## Changes made

Updated five documentation files to cite the new module paths:

1. **docs/data_dependency_manifest.md**:
   - Added "Preparation Responsibilities" notes to ROI helper sections explaining that RefinementInputs/prepare_refinement_inputs now live in `dbex.refinement.inputs` and config factories in `dbex.refinement.config_factories.py`
   - Updated `write_torch_outputs` inputs table to reference `dbex.refinement.inputs.RefinementInputs` dataclass instead of namedtuple

2. **docs/architecture/live_backend.md**:
   - Updated Torch Backend section to reference `dbex/refinement/inputs.py::prepare_refinement_inputs` for prep step
   - Added explicit mention of config builders living in `dbex/refinement/config_factories.py`
   - Added "Orchestration" bullet describing bridge module's reduced scope (HKL grids, calibration, orientation helpers)
   - Updated Implementation Interfaces section with fully-qualified module paths for prepare_refinement_inputs and config builders

3. **docs/architecture/module_map.md**:
   - Inserted two new table rows for `dbex/refinement/inputs.py` and `dbex/refinement/config_factories.py` with responsibilities, APIs, tests, and Active status
   - Rewrote `dbex/nanobrag_bridge.py` row to describe reduced scope (orchestration + HKL helpers + re-exports with TODO note)

4. **docs/architecture/data_telemetry_flow.md**:
   - Updated pipeline prep step to reference `dbex.refinement.inputs.prepare_refinement_inputs`
   - Updated ROI scoring step to cite `dbex.io.roi_scoring.score_roi_payloads` with Phase B note

5. **docs/architecture/dbex/io/writer.idl.md**:
   - Fixed inputs parameter row to reference `dbex.refinement.inputs.RefinementInputs` dataclass (instead of "namedtuple")
   - Updated Provenance column to cite `dbex.refinement.inputs.prepare_refinement_inputs()`

## Docs & ledgers updates

- Updated `docs/fix_plan.md` Tier 0 ARCH-BRIDGE-RESP-001 entry with timestamp for this Phase C.5 docs alignment loop.
- All normative spec language preserved; only module names/paths and descriptions changed.
- GEOMETRY/CONFIG/DIAGNOSTICS/PHYSICS-LOSS references remain intact per Findings Applied requirements.

## Next steps

Exit criteria for ARCH-BRIDGE-RESP-001 Phase C.5 (docs alignment) are now met:
- All five docs updated to reflect the new module structure
- Module map rows added for `dbex/refinement/inputs.py` and `dbex/refinement/config_factories.py`
- Bridge module row updated to reflect orchestration-only scope
- Prep/config/ROI references now cite the correct modules

Next action (future loop): Remove the re-export layer from `dbex/nanobrag_bridge.py` after verifying all downstream consumers (scripts, notebooks) have migrated to the new import paths.

## Artifacts

- Updated docs: docs/data_dependency_manifest.md, docs/architecture/live_backend.md, docs/architecture/module_map.md, docs/architecture/data_telemetry_flow.md, docs/architecture/dbex/io/writer.idl.md
- This summary: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-02T094947Z/summary.md
