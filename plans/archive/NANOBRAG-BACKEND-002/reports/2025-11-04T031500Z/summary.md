# NANOBRAG-BACKEND-002 Loop Summary (2025-11-04T031500Z)

## Focus & Current State
- Initiative remains pending in fix_plan but Phase A helpers now land; preparing Phase B (simulator integration).
- `run_nanobrag_backend` still emits Gaussian stub; no structure-factor hydration or spot-scale handling yet.
- DataLoad exposes structure factors (`F`) and reflections but no stored spot-scale override, so CLI must accept or derive the scale explicitly.

## One-off Analysis
### Probe: Inspect DataLoad for scale metadata (T1)
```python
from types import SimpleNamespace
from dbex.data_load import DataLoad
args = SimpleNamespace(
    mtzFile="scaled.mtz",
    mtzCol="F,SIGF",
    exptName="refGeom.expt",
    exptIdx=0,
    reflName="_geom_ref.refl"
)
dl = DataLoad(args)
scale_attrs = [attr for attr in dir(dl) if 'scale' in attr.lower()]
print('scale_attrs', scale_attrs)
print('has spot_scale_override in args?', hasattr(args, 'spot_scale_override'))
print('data shape', dl.data.shape)
print('bbox len', len(dl.bbox))
print('Refs keys iterator?', type(dl.Refs.keys()))
```
Output:
```
scale_attrs []
has spot_scale_override in args? False
data shape (1, 2527, 2463)
bbox len 92
Refs keys iterator? <class 'dict_keys'>
```

### Probe: Enumerate reflection table keys (T1)
```python
from types import SimpleNamespace
from dbex.data_load import DataLoad
args = SimpleNamespace(
    mtzFile="scaled.mtz",
    mtzCol="F,SIGF",
    exptName="refGeom.expt",
    exptIdx=0,
    reflName="_geom_ref.refl"
)
dl = DataLoad(args)
ref_keys = list(dl.Refs.keys())
print('num_keys', len(ref_keys))
print('sample_keys', ref_keys[:10])
```
Output:
```
num_keys 24
sample_keys ['bbox', 'delpsical.rad', 'delpsical2', 'entering', 'flags', 'id', 'imageset_id', 'intensity.sum.value', 'intensity.sum.variance', 'miller_index']
```

## Key Decisions & Next Steps
- Promote canonical `build_structure_factor_grid` logic from `scripts/generate_simple_cubic_golden.py:565` into `dbex.nanobrag_bridge` so the CLI can hydrate HKL data without duplication.
- Extend `create_parser` with optional `--spot-scale-override` (float, default 1.0) to satisfy SCALE-002 while preserving backward compatibility when the value is unknown.
- Rewrite `run_nanobrag_backend` to instantiate real nanobrag_torch models per panel, run Simulator on CPU by default, apply √(spot_scale_override), then reuse `_write_torch_outputs` for artifact emission.
- Author targeted pytest coverage in `tests/dbex/test_refine_one_cli.py` that patches Simulator to a deterministic stub verifying structure-factor hydration, scaling, and call ordering. Capture log at `plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T031500Z/pytest_nanobrag_backend.log` on execution.

## Risks / Watch Items
- `nanobrag_torch` import may be absent on some rigs; tests should `pytest.importorskip` and mark fix_plan blocked if imports fail at runtime.
- Ensure Euler analytic inversion (GEOMETRY-002) survives when configs feed simulator to avoid reintroducing detector drift.
- Maintain SCALE-001 by leaving structure factors unscaled; apply only the post-simulation √scale.

## Handoff Intent
- Provide Ralph with Do Now that wires simulator + scaling + tests and records pytest command `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend`.
- Update fix_plan status to `in_progress` with new attempt entry referencing this loop.
