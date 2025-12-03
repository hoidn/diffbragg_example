# Lazy Import Audit — 2025-12-02T082202Z

## Summary

Scanned the `dbex/` tree for function-scoped imports using pattern `^\s+(from|import)\s`.
Found **229 lazy-import instances** across multiple modules.

## Top Offenders

### 1. `dbex/physics/forward.py` (HIGH PRIORITY)

**Lines 103-106, 113-118, 196:**
- Imports `torch`, `nanobrag_torch.simulator.Simulator`, detector/crystal models at function scope
- Imports `dbex.nanobrag_bridge` helpers lazily
- **Impact:** Test-only helper (`simulate_forward_torch`) hides dependencies; grad tests don't surface import drift immediately

**Recommendation:**
- Move torch/nanobrag_torch imports to module scope with guarded try/except (set sentinels)
- Move bridge imports to module scope (already a dbex module, no circular risk per ARCH-ENGINE-002)
- Add `_require_torch()` helper to raise descriptive ImportError
- Keep TEST-ONLY warning; ensure no production LBFGS closures call this

**Relevant Findings:**
- ARCH-ENGINE-002 (module-scope dependency declaration)
- GEOMETRY-001 (geometry helper invariants)
- RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1 for grad tests)

---

### 2. `dbex/geometry/crystallography.py` (HIGH PRIORITY)

**Lines 73-75:**
- Imports `torch`, `nanobrag_torch.config.CrystalConfig`, `nanobrag_torch.models.crystal.Crystal` at function scope inside `derive_u_matrix_from_mosflm_a_star`
- **Impact:** Geometry helper is a leaf module (per docs/architecture.md); lazy imports hide optional dependency status

**Recommendation:**
- Move torch/nanobrag_torch imports to module scope with guarded try/except
- Set sentinel `_TORCH_AVAILABLE = False` on ImportError
- Add `_require_torch_crystal()` helper to raise same ImportError message
- Update docstrings to cite GEOMETRY-001/003 instead of historical ticket IDs (already done)

**Relevant Findings:**
- GEOMETRY-001 (beam/DetectorConfig invariants)
- GEOMETRY-003 (Stage A misset baseline logic)

---

### 3. `dbex/refine_one.py` (MEDIUM PRIORITY — CLI entrypoint)

**Lines 138, 179-183, 289-306, 465, 503-504, 604, 677:**
- Multiple function-scoped imports (numpy, h5py, torch, scipy, nanobrag_bridge, score_roi_payloads)
- **Context:** CLI entrypoint; lazy imports reduce boot time but hide dependencies from diagnostics

**Recommendation:**
- Defer to next phase; CLI helpers are changing under ARCH-BRIDGE-RESP-001 and ARCH-TELEMETRY-001
- Once writer/bridge split lands, consolidate imports at module scope

**Relevant Findings:**
- ARCH-ENGINE-002 (dependency staging rules)

---

### 4. `dbex/tools/stage_a_adam.py` (LOWER PRIORITY — tooling)

**Lines 155, 182, 241-244, 413, 445, 536, 641, 682, 824, 919, 1016, 1170, 1232, 1251, 1314, 1345, 1632-1639, 1700, 1730:**
- Many lazy imports (torch, nanobrag_torch, dbex helpers, pathlib, sys, parity fixtures)
- **Context:** Experimental Adam-based refinement tool; not production path

**Recommendation:**
- Document as "exception: experimental tooling"
- Move to module scope if this tool becomes production-critical

---

### 5. Other Modules (scan coverage)

**Full scan artifact:** `lazy_import_rg.txt` (229 lines)

Most remaining lazy imports are in:
- Test fixtures / exploratory notebooks (acceptable per docs/TESTING_GUIDE.md)
- Legacy helpers under refactoring (ARCH-REFACTOR-001, ARCH-BRIDGE-RESP-001)

---

## Phase A Do Now Completed

**Scoped edits for this loop:**
1. ✅ `dbex/geometry/crystallography.py` — promote torch/nanobrag_torch imports
2. ✅ `dbex/physics/forward.py` — promote torch/nanobrag_torch/bridge imports

**Next Phase:**
- Phase B: Stage helper import cleanup (`dbex/refinement/stage_*_impl.py`) once ARCH-REFACTOR-001 stabilizes
- Phase C: CLI entrypoint consolidation after writer/bridge split lands

---

## References

- ARCH-ENGINE-002 (lazy-import staging rules)
- GEOMETRY-001 (geometry mapping helper invariants)
- GEOMETRY-003 (Stage A misset baseline logic dependencies)
- RUNTIME-001 (torch.compile hygiene for grad tests)
- docs/architecture/pytorch_design.md:12 (vectorization/lazy-import policy)
