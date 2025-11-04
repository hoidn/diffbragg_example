# 2025-11-04T021141Z — Planning kickoff for NANOBRAG-BACKEND-002

## Focus
- Initiative: `NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator`
- Action type: planning / evidence collection

## Key observations
- Verified `nanobrag_torch` is importable in the frozen environment and exposes `Simulator`, `Detector`, `Crystal`, and config dataclasses (see micro probe below).
- Current `dbex.nanobrag_bridge` still returns local dataclass stubs, so `dbex.refine_one.run_nanobrag_backend` falls back to a Gaussian random tensor stub (`_stub_bragg_tensor`).
- The canonical golden dataset generator (`scripts/generate_simple_cubic_golden.py`) already demonstrates the desired integration flow (config hydration → HKL grid → √scale override), which we can promote into production code.
- Existing findings (SCALE-001/002, GEOMETRY-002, MANIFEST-001) remain applicable and must be enforced during the migration.

## Micro probes
### Probe: enumerate nanobrag_torch simulator API
```bash
python - <<'PY'
import importlib
sim = importlib.import_module('nanobrag_torch.simulator')
cfg = importlib.import_module('nanobrag_torch.config')
print("Simulator:", sim.Simulator)
print("Detector model:", sim.Detector)
print("Crystal model:", sim.Crystal)
print("BeamConfig fields:", cfg.BeamConfig.__dataclass_fields__.keys())
PY
```
Output:
```
Simulator: <class 'nanobrag_torch.simulator.Simulator'>
Detector model: <class 'nanobrag_torch.models.detector.Detector'>
Crystal model: <class 'nanobrag_torch.models.crystal.Crystal'>
BeamConfig fields: dict_keys(['wavelength_A', 'nopolar', 'polarization_axis', 'polarization_fraction', 'polarization_factor', 'dmin', 'beamsize_mm', 'flux', 'exposure'])
```

## Decisions
- Created implementation plan with Phase A (config promotion), Phase B (simulator integration), Phase C (parity validation); artifacts rooted at `plans/active/NANOBRAG-BACKEND-002/reports/`.
- Next actionable increment: promote bridge helpers to emit real `nanobrag_torch.config` objects and add unit tests guarding geometry + polarization invariants.

## Next actions
1. Draft fix-plan entry for NANOBRAG-BACKEND-002 with dependencies (`TORCH-BRIDGE-001`, `NANOBRAG-GOLDEN-001`, SCALE findings).
2. Prepare `input.md` Do Now instructing Ralph to replace bridge stubs with real config constructors and add targeted tests (`tests/dbex/test_nanobrag_bridge_configs.py`).
3. Map validating pytest selector(s) (likely bridge config tests module) and capture planned artifact directory under this initiative.
