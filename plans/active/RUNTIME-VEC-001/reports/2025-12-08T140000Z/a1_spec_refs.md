# A1: nanobrag_torch Accessibility and Spec References

## nanobrag_torch Import Status

**Tested:** 2025-12-08T14:00:00Z

### Import Results:
```
nanobrag_torch version: 0.1.0
```

### Available Exports:
```python
['__builtins__', '__cached__', '__doc__', '__file__', '__loader__',
 '__name__', '__package__', '__path__', '__spec__', '__version__']
```

**Note:** `Simulator` is not directly exported from `nanobrag_torch`. Users must import submodules directly (e.g., `from nanobrag_torch.simulator import Simulator`).

### Editable Install Location:
```
/home/ollie/Documents/nanoBragg/src/nanobrag_torch/__init__.py
```

---

## Spec References for Source Weighting

### 1. `docs/architecture/pytorch_design.md` §1.1.5 (Source Weighting & Integration)

**Objective:** Support equal weighting by default while honoring explicit per-source weights when provided.

**Implementation:** `src/nanobrag_torch/simulator.py` lines 399-423 (guard) and steps normalization at line 1892. Default path divides by the number of sources (equal weighting).

**Normative Reference:** See `docs/spec-db-core.md` (Source Handling and Weighting) for the canonical rules:
- Equal weighting by default
- Per-source weights allowed and interpreted as one coefficient per source
- A global flux/exposure knob is separate from per-source weights

**Validation Thresholds (from Phase G evidence):**
- Correlation ≥0.999 (observed: 0.9999886)
- |sum_ratio−1| ≤5e-3 / 0.5% (observed: 0.0038 / 0.38%)

### 2. `docs/pytorch_runtime_checklist.md` §4 (Source Handling & Equal Weighting)

**Key Rules:**
1. **Do not apply source weights as multiplicative factors.** The weight column in sourcefiles is parsed but ignored per `specs/spec-a-core.md:151-153`.
2. Steps normalization divides by source count, not weight sum: `steps = sources * mosaic_domains * phisteps * oversample^2`.
3. CLI `-lambda` is authoritative for all sources; sourcefile wavelength column is also ignored.

**Parity Memo:** `nanoBragg2/reports/2025-11-source-weights/phase_h/20251010T002324Z/parity_reassessment.md` confirms C reference (nanoBragg.c:2570-2720) implements equal weighting.

**Test Command:**
```bash
pytest nanoBragg2/tests/test_cli_scaling.py::TestSourceWeights* -v
# Expected: 7/7 passing
```

### 3. Relevant Findings (from `docs/findings.md`)

| ID | Summary |
|----|---------|
| RUNTIME-001 | Gradient tests require `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference with `torch.autograd.gradcheck` |

---

## Environment Requirements

Per `docs/pytorch_runtime_checklist.md` §5:

| Variable | Purpose | Required |
|----------|---------|----------|
| `KMP_DUPLICATE_LIB_OK=TRUE` | Prevent duplicate library conflicts | Always |
| `NANOBRAGG_DISABLE_COMPILE=1` | Disable torch.compile for gradient tests | For gradient tests |
| `CUDA_VISIBLE_DEVICES` | GPU device pinning | Optional |

---

## Conclusion

nanobrag_torch is accessible from the DBEX environment (version 0.1.0). The spec references confirm:
- Source weights are parsed but ignored (equal weighting)
- CLI `-lambda` is authoritative
- Validated thresholds: correlation ≥0.999, |sum_ratio−1| ≤5e-3
