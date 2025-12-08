# Input for Ralph — Loop i=153

## Summary
Execute DB-AT-023 Phase A (Calibration Policy Guard reality check) to establish baseline metrics and calibration policy requirements.

## Mode
Parity

## ActionType
planning

## DecisionStatus
exploring

## InitiativeType
harness

## Focus
DB-AT-023 — Calibration Policy Guard (ADU vs Photons)

## Branch
integration

## Mapped tests
none — Phase A is evidence/planning only

## Artifacts
`plans/active/DB-AT-023/reports/2025-12-08T022101Z/`

## Findings Applied (Mandatory)
- **TESTING-003**: Registry updates will occur in Phase C after test authoring
- **RUNTIME-001**: Environment flags documented for Phase B test commands
- **DIAGNOSTICS-001**: Artifact structure follows standard pattern
- **No calibration-specific findings yet** — DB-AT-023 Phase A will surface calibration policy requirements from spec-db-workflow.md

## Pointers

### SPEC
- `docs/spec-db-workflow.md:19-47` — Calibration Policy (ADU vs Photons), precedence ladder, normative requirements
- `docs/spec-db-workflow.md:34-47` — Calibration & Unit Conventions (gain, sigma, spot_scale)
- `docs/spec-db-core.md:32-68` — Variance inputs, sigma_readout ladder
- `docs/spec-db-conformance.md` — DB-AT-023 acceptance criteria

### ARCH
- `docs/architecture.md:165-178` — Calibration ladder architecture
- `docs/config_crosswalk.md` — Parameter mapping between backends

### Plan
- `plans/active/DB-AT-023/implementation.md` — Phase A/B/C checklist
- `plans/active/DB-AT-SUITE-CARE-001/implementation.md` — Roll-up coordination
- `docs/fix_plan.md:267-292` — DB-AT-SUITE-CARE-001 Attempts History

### Asset Validation Reference
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md` — Loop i=143 centralized validation (4/4 assets VALID)

## ARCH Contracts (mandatory)

1. **ARCH-CONTRACT-CALIBRATION-001** (Calibration Precedence)
   - Doc: `docs/spec-db-workflow.md:34` "Precedence ladder (highest → lowest)"
   - Owner: `dbex/refine_one.py`, `dbex/nanobrag_bridge.py::prepare_refinement_inputs`
   - Classification: Implementation conforms (precedence ladder documented, no enforcement test yet)

2. **ARCH-CONTRACT-UNIT-MODE-001** (ADU vs Photon Mode)
   - Doc: `docs/spec-db-workflow.md:35` "A run SHALL choose a single unit mode"
   - Owner: `dbex/refine_one.py`, `dbex/data_load.py`
   - Classification: Implementation partially exists (no --adu-per-photon CLI flag yet per DB-AT-023 Phase B1)

3. **ARCH-CONTRACT-SIGMA-001** (Sigma Sourcing)
   - Doc: `docs/spec-db-workflow.md:36-37` "sigma_readout MUST follow canonical ladder"
   - Owner: `dbex/data_load.py::_resolve_sigma_readout`, `dbex/refinement/inputs.py`
   - Classification: Implementation conforms (ladder implemented)

## Do Now (hard validity contract)

Execute **DB-AT-023 Phase A** — Calibration Policy Guard reality check:

1. **Implement:** Read and confirm Phase A tasks in `plans/active/DB-AT-023/implementation.md`

2. **A1 — Asset Availability Check**
   - Cross-reference loop i=143 asset validation (`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md`)
   - Confirm 4/4 canonical assets still VALID: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`
   - Record asset snapshot in `asset_availability.md`

3. **A2 — Baseline Metrics Capture**
   - Load DataLoad with canonical inputs (see conftest.py refgeom_dataload pattern)
   - Capture baseline calibration context:
     - Background-subtracted ROI sample metrics (mean, std, ROI sums)
     - Current calibration metadata (`spot_scale_override`, `flux`, `exposure`, `beamsize_mm`, `N_cells`)
     - Sigma sourcing status (sigma_readout provenance, sigma_floor if present)
   - Record in `baseline_metrics.md`

4. **A3 — Calibration Policy Summary**
   - Cross-reference normative sources:
     - `docs/spec-db-workflow.md:19-47` (ADU vs photon, precedence ladder)
     - `docs/architecture.md` (calibration architecture)
     - `docs/config_crosswalk.md` (parameter mapping)
   - Summarize calibration expectations:
     - When `--adu-per-photon` is provided: target/sigma converted to photons
     - When absent: target remains ADU, global scale compensates
     - Precedence: torch_config → CLI → external_lookup → MTZ → defaults
   - Identify Phase B requirements:
     - CLI flag extension (`--adu-per-photon`)
     - `prepare_refinement_inputs` photon conversion path
     - Telemetry provenance (`unit_mode`, `gain`)
   - Record in `calibration_policy_summary.md`

5. **Artifacts:** Create 4 files under `plans/active/DB-AT-023/reports/2025-12-08T022101Z/`:
   - `asset_availability.md` — A1 results
   - `baseline_metrics.md` — A2 results
   - `calibration_policy_summary.md` — A3 results
   - `summary.md` — Phase A wrap-up with Phase B scoping notes

6. **Mark Phase A tasks complete** in `plans/active/DB-AT-023/implementation.md`

## How-To Map

```bash
# A1: Cross-reference i=143 asset validation
cat plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md

# A2: Python probe for baseline metrics
cd /home/ollie/Documents/diffbragg_example
python -c "
from tests.conftest import refgeom_dataload
import json

# Get DataLoad via fixture pattern
DL = refgeom_dataload()

# Capture calibration context
metrics = {
    'data_shape': list(DL.data.shape) if hasattr(DL, 'data') else None,
    'n_rois': len(DL.panel_slices) if hasattr(DL, 'panel_slices') else None,
    'calibration_metadata': DL.calibration_metadata if hasattr(DL, 'calibration_metadata') else {},
}
print(json.dumps(metrics, indent=2, default=str))
"

# A3: Read spec sources
head -80 docs/spec-db-workflow.md | tail -60
```

## Pitfalls To Avoid

1. **Do not create tests** — Phase A is planning/evidence only; tests authored in Phase B
2. **Do not modify production code** — Phase A is read-only investigation
3. **Cross-reference existing assets** — i=143 already validated; don't duplicate file checks
4. **Capture calibration metadata** — Need baseline to design Phase B photon conversion logic
5. **Follow DB-AT-020/021/022 pattern** — 4 artifacts, mark implementation.md checkboxes
6. **No new probes beyond thin wrapper** — Use existing DataLoad patterns
7. **Record provenance** — Cite spec section numbers for calibration requirements

## If Blocked

- If DataLoad instantiation fails: record error, propose mock-based Phase B tests
- If calibration_metadata missing: document current state, design Phase B to add it
- If spec ambiguity: cite conflicting sections, request Galph clarification
- Record block in `plans/active/DB-AT-023/reports/2025-12-08T022101Z/summary.md` with next steps

---

**End of input.md for Loop i=153**
