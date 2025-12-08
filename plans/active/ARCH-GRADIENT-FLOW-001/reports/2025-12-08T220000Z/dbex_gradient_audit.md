# DBEX Layer Gradient Audit — Phase B.5

**Date:** 2025-12-08T22:00:00Z
**Focus:** ARCH-GRADIENT-FLOW-001 — DB-AT-010 gradcheck failure
**Status:** ROOT CAUSE IDENTIFIED (Confidence: 0.95)

---

## 1. Tensor Flow Trace

### Entry Point
- **Test**: `tests/dbex/test_gradients.py:185-230` (`TestDB_AT_010_Gradcheck.test_db_at_010_gradcheck_crystal_cell_a`)
- **Input tensor**: `cell_a_param = torch.tensor(base_cell_a, dtype=dtype, device=device, requires_grad=True)` (line 221)
- **Override dict**: `crystal_overrides = {'cell_a': cell_a_tensor}` (line 208)

### DBEX Forward Path

1. **`forward.py:73-87`**: `simulate_forward_torch(...)` receives `crystal_overrides={'cell_a': tensor}`
2. **`forward.py:196`**: `crystal_config, _ = create_crystal_config(crystal, experiment)` — **NO crystal_overrides passed!**
3. **`config_factories.py:342-347`**: Because `crystal_overrides is None`:
   ```python
   A_tuple = crystal.get_A()
   A = np.array(A_tuple).reshape(3, 3)
   mosflm_a_star = np.array(A[:, 0])  # ← MOSFLM vectors set from base crystal
   mosflm_b_star = np.array(A[:, 1])
   mosflm_c_star = np.array(A[:, 2])
   ```
4. **`forward.py:200-226`**: Override applied AFTER config creation:
   ```python
   if crystal_overrides is not None:
       if 'cell_a' in crystal_overrides:
           a = crystal_overrides['cell_a']  # tensor with requires_grad=True
       crystal_config.cell_a = a  # Assigned to config
   ```
5. **`forward.py:248`**: `create_unified_simulator(crystal_config=crystal_config, ...)` passes config to factory
6. **`helpers.py:198`**: `crystal = Crystal(crystal_config, beam_config=beam_config, device=device, dtype=dtype)`

### nanobrag_torch Crystal Construction

7. **`crystal.py:69-86`**: `Crystal.__init__` stores cell params:
   ```python
   self.cell_a = torch.as_tensor(self.config.cell_a, device=self.device, dtype=self.dtype)
   # cell_a is now the tensor with requires_grad=True ✓
   ```

8. **`crystal.py:660-663`**: In `compute_cell_tensors()`, MOSFLM check:
   ```python
   mosflm_provided = (
       hasattr(self.config, "mosflm_a_star") and self.config.mosflm_a_star is not None
       and hasattr(self.config, "mosflm_b_star") and self.config.mosflm_b_star is not None
       and hasattr(self.config, "mosflm_c_star") and self.config.mosflm_c_star is not None
   )
   ```
   **Result: `mosflm_provided = True`** (because mosflm vectors were set from base crystal at step 3)

9. **`crystal.py:815-874`**: MOSFLM path executes:
   ```python
   if mosflm_provided:
       # MOSFLM orientation provided - convert to tensors and use directly
       a_star = torch.as_tensor(self.config.mosflm_a_star, ...)  # Uses base crystal A*
       b_star = torch.as_tensor(self.config.mosflm_b_star, ...)
       c_star = torch.as_tensor(self.config.mosflm_c_star, ...)
       ...
       # Step 3: Compute real-space vectors: a = (b* × c*) × V_cell, etc.
       a_vec = b_star_cross_c_star * V_cell  # Computed from MOSFLM, not from cell_a
       ...
       # Step 4: Update cell parameters (magnitudes in Å)
       self.cell_a = torch.norm(a_vec)  # ← OVERWRITES our tensor override!
   ```

### Gradient Break Point

**Location:** `crystal.py:872` — `self.cell_a = torch.norm(a_vec)`

The tensor with `requires_grad=True` that we passed through `crystal_overrides` is OVERWRITTEN by a new tensor computed from MOSFLM reciprocal vectors. The output intensity image thus has NO computational dependency on our input tensor.

---

## 2. Suspect Patterns

| File:Line | Pattern | Impact |
|-----------|---------|--------|
| `forward.py:196` | `create_crystal_config(crystal, experiment)` without `crystal_overrides` | MOSFLM injection enabled → gradient break |
| `crystal.py:872` | `self.cell_a = torch.norm(a_vec)` | Overwrites tensor override with MOSFLM-derived value |
| `config_factories.py:342-347` | MOSFLM A* extraction when `crystal_overrides is None` | Sets mosflm vectors from base crystal |

---

## 3. Hypothesis

**Root Cause:** The `forward.py:196` call to `create_crystal_config` does NOT pass `crystal_overrides`, causing MOSFLM A* vectors to be injected into the config from the base dxtbx crystal. When `Crystal.compute_cell_tensors()` runs, it takes the MOSFLM path (lines 815-877) because `mosflm_a_star` is not None, computing all geometry from those vectors instead of from the cell parameters. This path overwrites `self.cell_a` with a new tensor at line 872, disconnecting the computational graph from our input tensor.

The cell parameter tensor override is correctly stored on `crystal_config.cell_a`, but it's never used because the MOSFLM path takes precedence.

---

## 4. Confidence

**0.95** — High confidence based on:
1. gradcheck error is "Numerical gradient for function expected to be zero" which means output tensor has no `requires_grad=True` (disconnected graph)
2. Clear code path shows MOSFLM injection when `crystal_overrides` not passed
3. MOSFLM path explicitly overwrites cell parameter tensors at line 872
4. The `config_factories.py` already has logic to skip MOSFLM injection when `crystal_overrides` is provided (lines 354-357)

---

## 5. Proposed Fix

**Single-line change in `dbex/physics/forward.py:196`:**

Current:
```python
crystal_config, _ = create_crystal_config(crystal, experiment)
```

Proposed:
```python
crystal_config, _ = create_crystal_config(crystal, experiment, crystal_overrides=crystal_overrides)
```

This causes `config_factories.py:354-357` to execute:
```python
else:
    # Let nanobrag_torch compute A* from overridden cell parameters
    mosflm_a_star = None
    mosflm_b_star = None
    mosflm_c_star = None
```

When `mosflm_a_star = None`, the `mosflm_provided` check at `crystal.py:660-663` will be False, and the default orientation path (lines 682-716) will execute instead, computing geometry FROM the cell parameters (including our tensor with `requires_grad=True`).

---

## 6. Additional Findings

### Secondary Concern: `nanobrag_bridge.py:603-608`
```python
a_val = float(a.item() if hasattr(a, 'item') else a)
b_val = float(b.item() if hasattr(b, 'item') else b)
...
```

This pattern in `compute_reciprocal_space_from_cell` would also break gradients if called with tensor parameters. However, this function doesn't appear to be on the `simulate_forward_torch` critical path — it's used for dxtbx compatibility, not for the main forward simulation.

### Architectural Observation

The current design has TWO competing mechanisms for cell parameter handling:
1. **Cell parameter path**: Uses `cell_a`/`cell_b`/etc. tensor values to compute geometry
2. **MOSFLM orientation path**: Uses pre-computed A* reciprocal vectors, overwriting cell params

For gradient-based refinement, only the cell parameter path preserves gradients. The fix ensures that when `crystal_overrides` is provided, the cell parameter path is used.

---

## 7. Test Validation Plan

After fix:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --smoke-detector-size=full --tb=short
```

Expected: PASS

---

## 8. Files Examined

| File | Lines | Purpose |
|------|-------|---------|
| `tests/dbex/test_gradients.py` | 159-230 | Test implementation |
| `dbex/physics/forward.py` | 73-274 | Forward simulation entry point |
| `dbex/refinement/config_factories.py` | 278-450 | Crystal config factory |
| `dbex/refinement/helpers.py` | 83-228 | Unified simulator factory |
| `nanobrag_torch/models/crystal.py` | 40-1000 | Crystal model with geometry computation |
| `nanobrag_torch/config.py` | 96-165 | CrystalConfig dataclass |
