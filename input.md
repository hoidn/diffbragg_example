# Input — Loop i=210 (Ralph) — ARCH-GRADIENT-FLOW-001 Phase B.8

## Summary
Debug crystal cell gradient magnitude mismatch (843× for cell_a) — graph is connected, magnitudes are wrong.

## Focus
ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)

## Branch
integration

## Mapped Tests
`pytest -v tests -k "test_db_at_010_gradcheck_crystal_cell_a" --smoke-detector-size=full` — Focused on cell_a first

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/`

---

## Context

**Phase B.7 PARTIAL SUCCESS** (Loop i=209, Ralph):
1. Pure-PyTorch B-matrix implemented at `nanobrag_bridge.py:558-680` — verified vs cctbx (max diff 3.47e-18)
2. Removed `.detach()` from A* extraction at `stage_a.py:1183-1195,1238-1255`
3. **Graph connectivity RESTORED** — analytical gradients now non-zero

**Remaining Issue — Magnitude Mismatch**:
```
cell_a:    numerical=5.94e10, analytical=7.04e7  (843× mismatch)
cell_gamma: numerical=4.63e7, analytical=4.64e7  (much closer, but still fails rtol=0.05)
```

**Upstream Hypotheses** (from `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md`):
1. **Double unit conversion** — Å→m applied twice somewhere
2. **Intermediate scalar extraction** — remaining `.item()/.detach()` calls
3. **Fluence/scaling mismatch** — Different scaling factors

---

## Do Now

### B.8.1 — Isolate nanobrag_torch gradient directly

Create a minimal test that bypasses DBEX integration entirely to confirm upstream gradients work in our environment.

**Target**: Create and run diagnostic script (T1 probe in artifacts, don't commit)

```python
# T1 probe — run directly in Python REPL, save output to artifacts
import torch
import sys
sys.path.insert(0, '/home/ollie/Documents/nanoBragg/src')

from nanobrag_torch.config import CrystalConfig, DetectorConfig, BeamConfig
from nanobrag_torch.models import Crystal, Detector
from nanobrag_torch.simulator import Simulator

device = torch.device('cpu')
dtype = torch.float64

# Create cell_a as differentiable tensor
cell_a = torch.tensor(100.0, dtype=dtype, requires_grad=True)

# Simple crystal config with tensor cell_a
crystal_config = CrystalConfig(
    cell_a=cell_a,
    cell_b=100.0, cell_c=100.0,
    cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
    N_cells=(5, 5, 5),
    default_F=100.0,
)

# Simple detector/beam
detector_config = DetectorConfig(
    fpixels=100, spixels=100, pixel_size_mm=0.1,
    distance_mm=100.0, beam_center_f_mm=5.0, beam_center_s_mm=5.0
)
beam_config = BeamConfig(wavelength_A=1.0, fluence=1e20)

# Create models and simulator
crystal = Crystal(config=crystal_config, device=device, dtype=dtype)
detector = Detector(config=detector_config)
simulator = Simulator(crystal=crystal, detector=detector, beam_config=beam_config,
                      device=device, dtype=dtype)

# Run forward
result = simulator.run()
loss = result.sum()

# Check gradients
loss.backward()
print(f"cell_a.grad = {cell_a.grad}")
print(f"loss = {loss.item()}")

# Run gradcheck
from torch.autograd import gradcheck
def simple_loss(cell_a_param):
    config = CrystalConfig(
        cell_a=cell_a_param, cell_b=100.0, cell_c=100.0,
        cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
        N_cells=(5, 5, 5), default_F=100.0,
    )
    crystal = Crystal(config=config, device=device, dtype=dtype)
    detector = Detector(config=detector_config)
    sim = Simulator(crystal=crystal, detector=detector, beam_config=beam_config,
                    device=device, dtype=dtype)
    return sim.run().sum()

cell_a_test = torch.tensor(100.0, dtype=dtype, requires_grad=True)
try:
    result = gradcheck(simple_loss, (cell_a_test,), eps=1e-6, atol=1e-5, rtol=0.05)
    print(f"gradcheck PASSED: {result}")
except Exception as e:
    print(f"gradcheck FAILED: {e}")
```

Save output to: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/nanobrag_isolated_gradcheck.txt`

### B.8.2 — Compare gradient paths: DBEX vs Direct

If B.8.1 passes, the issue is in DBEX integration. Add diagnostic prints to understand the chain:

**Target**: `dbex/physics/forward.py::simulate_forward_torch` (around line 199-229)

Add temporary diagnostics (remove after debugging):
```python
# After line 199 (after create_crystal_config call)
if crystal_overrides and 'cell_a' in crystal_overrides:
    print(f"[DEBUG] crystal_overrides['cell_a'] requires_grad: {crystal_overrides['cell_a'].requires_grad}")
    print(f"[DEBUG] crystal_config.cell_a type: {type(crystal_config.cell_a)}")
    if hasattr(crystal_config.cell_a, 'requires_grad'):
        print(f"[DEBUG] crystal_config.cell_a requires_grad: {crystal_config.cell_a.requires_grad}")
```

### B.8.3 — Check for duplicate B-matrix computation

Search for any location where B-matrix or A* is computed TWICE for the same crystal:

```bash
grep -n "busing_levy_B_torch\|derive_B_from_cell\|fractionalization_matrix" dbex/**/*.py
```

If found, verify only ONE path computes gradients.

### B.8.4 — Check fluence/scale values

Compare fluence values between DBEX test and nanobrag_torch upstream test:

**DBEX test** (from fixture):
```bash
grep -n "fluence" tests/dbex/test_gradients.py tests/conftest.py dbex/refinement/config_factories.py | head -30
```

**Upstream test** (from response): Uses `fluence=1e28`

If fluence differs by orders of magnitude, this could explain the gradient magnitude difference.

---

## How-To Map

### Run the isolated probe
```bash
cd /home/ollie/Documents/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python3 << 'EOF'
# ... (paste B.8.1 code here)
EOF
```

### Run DB-AT-010 cell_a test with verbose output
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    pytest -v tests -k "test_db_at_010_gradcheck_crystal_cell_a" \
    --smoke-detector-size=full -s 2>&1 | \
    tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T230000Z/gradcheck_cell_a_verbose.log
```

---

## Pitfalls To Avoid

1. **DO NOT** modify production code for diagnostics — use temporary prints removed before commit
2. **DO NOT** install packages — use existing nanobrag_torch from editable install
3. **Environment Freeze:** Do not run pip install
4. **Test artifact capture:** Save all diagnostic output to artifacts directory
5. **Compare apples to apples:** Ensure DBEX test and isolated probe use same fluence/scale values

---

## If Blocked

If isolated nanobrag_torch test FAILS (B.8.1):
- Re-check upstream's exact test pattern
- File follow-up to `~/Documents/nanoBragg/inbox/` requesting exact test code that passes

If isolated test PASSES but DBEX fails:
- Focus on DBEX integration layer (config_factories.py, forward.py)
- Check for any hidden scaling/conversion factors
- Document exactly where gradient magnitude diverges

---

## Findings Applied

- **GRADIENT-002** (Current finding): Graph connected but magnitude mismatch 843×-19352×.
  - Adherence: B.8.1-B.8.4 systematically isolate the magnitude source.

- **RUNTIME-001** (Runtime execution guardrails): Use `NANOBRAGG_DISABLE_COMPILE=1`.
  - Adherence: All commands include this flag.

- **PROBE-FREEZE-001** (No new plan-local scripts): Diagnostics are T1 probes in artifacts.
  - Adherence: B.8.1 code is NOT committed, only output saved.

---

## Pointers

- Phase B.7 fix commit: See `git log -1 --oneline` (i=209)
- Bug locations fixed: `nanobrag_bridge.py:558-680`, `stage_a.py:1183-1195,1238-1255`
- Upstream response: `inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md`
- Forward simulation entry: `dbex/physics/forward.py:165-276`
- Config factory: `dbex/refinement/config_factories.py:278-468`

---

## Next Up (if B.8 isolates root cause)

1. B.8.5 — Apply targeted fix based on diagnosis (scaling factor, double computation, etc.)
2. B.9 — Run full DB-AT-010 suite to verify 5/5 PASS
