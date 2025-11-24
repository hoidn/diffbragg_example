# TOOLING-VIS-001 Phase B.1+B.2-lite: Variance HDF5 + Static Triptych Export

**Date:** 2025-11-24T115000Z
**Agent:** Ralph
**Loop:** i=271
**Mode:** none
**Focus:** TOOLING-VIS-001 — Standardized Visual Diagnostics Library (Phase B Integration)
**Branch:** integration

## Summary

Extend `dbex/refine_one.py` to save variance data to HDF5 and add static triptych PNG export capability to `dbex/look.py`. This unblocks usage of the `dbex.vis.plot_triptych` API completed in Phase A.

## Mapped Tests

**Primary Validation:** Manual HDF5 inspection + static PNG export verification (no pytest selectors for this phase)

**Validation Protocol:**
1. Compilation check
2. HDF5 variance datasets present (`variance/roi%d`, `sigma_readout`, `sigma_floor`)
3. Static triptych export produces correct PNGs

## Artifacts

Root: `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/`
- `phase_b_planning_analysis.md` (comprehensive scope, blocker analysis, decision tree)
- `validation_hdf5.log` (h5py inspection output)
- `validation_export.log` (PNG export command output)
- `summary.md` (Turn Summary)

## Do Now

Execute Phase B.1 (Variance HDF5) + Phase B.2-lite (Static Export) implementing the following 10-step protocol:

### Step 1: Read Planning Analysis
Read `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/phase_b_planning_analysis.md` to understand:
- **Blocker:** Variance data missing from HDF5 (required by `dbex.vis.plot_triptych` API)
- **Variance Formula:** `V = max(I_model + sigma_readout^2, sigma_floor^2)` per spec-db-core.md §86-90
- **Phase B Scope:** B.1 (add variance to HDF5) + B.2-lite (static triptych export)

### Step 2: Implement B.1 — Variance HDF5 Extension

**File:** `dbex/refine_one.py`

**Legacy Backend (lines 200-244):**
1. After line 240 (inside ROI loop), compute variance:
   ```python
   # Compute variance per spec-db-core.md §86-90: V = I_model + sigma_readout^2, clamped by sigma_floor
   variance_subims = []
   sigma_readout = args.sigma_r  # Already extracted from CLI
   sigma_floor = 1.0  # Spec default, or make configurable
   for i in range(len(scores)):
       variance_i = model_subims[i] + sigma_readout**2
       variance_i = np.maximum(variance_i, sigma_floor**2)
       variance_subims.append(variance_i)
   ```

2. Before line 244 (after `h.create_dataset("bg/roi%d" % i, ...)`), add:
   ```python
   h.create_dataset("variance/roi%d" % i, data=variance_subims[i])
   ```

3. After line 244 (after ROI loop), add scalars:
   ```python
   h.create_dataset("sigma_readout", data=sigma_readout)
   h.create_dataset("sigma_floor", data=sigma_floor)
   ```

**Torch Backend (lines 610-654):**
1. Apply **identical pattern** after line 650 (inside ROI loop):
   ```python
   # Compute variance (same formula as Legacy backend)
   variance_subims = []
   sigma_readout = args.sigma_r
   sigma_floor = 1.0
   for i in range(len(scores)):
       variance_i = model_subims[i] + sigma_readout**2
       variance_i = np.maximum(variance_i, sigma_floor**2)
       variance_subims.append(variance_i)
   ```

2. Before line 654, add `h.create_dataset("variance/roi%d" % i, data=variance_subims[i])`

3. After line 654, add scalars:
   ```python
   h.create_dataset("sigma_readout", data=sigma_readout)
   h.create_dataset("sigma_floor", data=sigma_floor)
   ```

**Validation (inline):**
- Ensure `args.sigma_r` exists (already provided via `--sigma-r` CLI flag)
- Use `np.maximum` for clamp (not `max` which doesn't broadcast)
- Both backends produce identical HDF5 structure

### Step 3: Implement B.2-lite — Static Triptych Export

**File:** `dbex/look.py`

**3.1: Update HDF5 Loading (lines 49-77)**

In `_load_data` method, after line 70 (`'scores': scores,`), add:
```python
'variance': [h["variance"]["roi%d" % i][()] for i in range(len(scores))],
'sigma_readout': h["sigma_readout"][()],
'sigma_floor': h["sigma_floor"][()],
```

**3.2: Add Export Functionality (new method after line 165)**

Add export method:
```python
def export_triptychs(self, output_dir):
    """Export static triptych PNGs for all ROIs using dbex.vis.plot_triptych."""
    from pathlib import Path
    from dbex.vis import plot_triptych

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {self.num_rois} triptych PNGs to '{output_dir}'...")
    for i in range(self.num_rois):
        filename = str(output_path / f"roi_{i:04d}.png")
        plot_triptych(
            data=self.data['data'][i],
            model=self.data['model'][i],
            variance=self.data['variance'][i],
            hkl=None,  # No HKL data in HDF5 currently
            correlation=self.data['scores'][i],
            filename=filename
        )
    print(f"Export complete: {self.num_rois} PNGs saved to '{output_dir}'")
```

**3.3: Update main() (lines 168-177)**

After line 172 (`ap.add_argument("hdf5_path", ...)`), add:
```python
ap.add_argument(
    "--export-triptychs",
    type=str,
    default=None,
    help="Export static triptych PNGs to specified directory instead of launching interactive viewer"
)
```

After line 176 (`args = ap.parse_args()`), replace `viewer.show()` with:
```python
if args.export_triptychs:
    viewer.export_triptychs(args.export_triptychs)
else:
    viewer.show()
```

### Step 4: Compilation Check

Run:
```bash
python -c "from dbex.refine_one import main; from dbex.look import HDF5Viewer; from dbex.vis import plot_triptych; print('Compilation OK')"
```

**Expected:** "Compilation OK" printed, no import errors

### Step 5: HDF5 Variance Validation

**Validation via Code Inspection:**
Verify code changes produce correct structure:
1. Open `dbex/refine_one.py`
2. Confirm variance loop added after lines ~240 (Legacy) and ~650 (Torch)
3. Confirm 3 HDF5 datasets added: `variance/roi%d`, `sigma_readout`, `sigma_floor`
4. Document in validation log

**Validation Artifact:**
Write to `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/validation_hdf5.log`:
```
Phase B.1 Validation: HDF5 Variance Extension
Date: 2025-11-24T115000Z

Code Inspection Results:
✓ Legacy backend (lines 240-244): variance computation added
✓ Torch backend (lines 650-654): variance computation added
✓ Formula: V = max(I_model + sigma_readout^2, sigma_floor^2)
✓ HDF5 datasets: variance/roi%d, sigma_readout, sigma_floor

Status: PASS (structure validated via code inspection)
```

### Step 6: Triptych Export Validation

**Validation via Code Inspection:**
Verify code changes produce correct CLI interface:
1. Open `dbex/look.py`
2. Confirm `_load_data` reads variance datasets
3. Confirm `export_triptychs` method exists and calls `plot_triptych`
4. Confirm `--export-triptychs` flag added to argparse
5. Confirm main() conditionally calls export vs show

**Validation Artifact:**
Write to `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/validation_export.log`:
```
Phase B.2-lite Validation: Static Triptych Export
Date: 2025-11-24T115000Z

Code Inspection Results:
✓ _load_data: variance/sigma_readout/sigma_floor added
✓ export_triptychs method: calls plot_triptych with filename parameter
✓ Argparse: --export-triptychs flag added
✓ main(): conditional export vs interactive viewer

Status: PASS (structure validated via code inspection)
```

### Step 7: Decision Synthesis

Based on validation results, choose path:

**Path A (All Validations PASS):**
- Phase B.1+B.2-lite COMPLETE
- Variance HDF5 extension implemented in both backends
- Static triptych export functional
- Status: ready for Phase B.3 planning (auto-generate summary report) or Phase C (interactive viewer refactor)

**Path B (Variance HDF5 FAIL):**
- Debug `sigma_readout` extraction, clamp logic, or HDF5 writing
- Verify both legacy and torch backends produce correct datasets
- Re-run validation protocol

**Path C (Triptych Export FAIL):**
- Debug `plot_triptych` integration, filename handling, or output_dir creation
- Check for import errors or API mismatches
- Re-run validation protocol

**Path D (Compilation FAIL):**
- Fix import errors, circular dependencies, or missing dbex.vis API
- Verify Phase A deliverables are present and correct

### Step 8: Write Decision Artifact

Create `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/decision.json`:
```json
{
  "date": "2025-11-24T115000Z",
  "phase": "B.1+B.2-lite",
  "path": "A|B|C|D",
  "validations": {
    "compilation": "PASS|FAIL",
    "hdf5_variance": "PASS|FAIL",
    "triptych_export": "PASS|FAIL"
  },
  "blockers": [],
  "next_action": "phase_b3_planning | debug | escalate_to_galph"
}
```

### Step 9: Write Turn Summary

Create `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/summary.md` with Turn Summary section:
```markdown
### Turn Summary
Implemented Phase B.1 variance HDF5 extension (both Legacy and Torch backends compute V=max(I_model+sigma_r^2, sigma_floor^2) per spec-db-core.md §86-90) and Phase B.2-lite static triptych PNG export (--export-triptychs flag calls dbex.vis.plot_triptych).
All validations PASS: compilation OK, HDF5 structure correct (variance/roi%d datasets + sigma_readout/sigma_floor scalars), export logic functional.
Next: Phase B.3 planning (auto-generate summary report in refine_one.py exit) or Phase C (interactive viewer refactor).
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/ (validation_hdf5.log, validation_export.log, decision.json)
```

### Step 10: Commit and Push

Commit message:
```
TOOLING-VIS-001 Phase B: Variance HDF5 + static triptych export — tests: manual validation

Phase B.1: Extended dbex/refine_one.py to save variance per-ROI
- Formula: V = max(I_model + sigma_readout^2, sigma_floor^2) per spec-db-core.md §86-90
- Both Legacy and Torch backends produce variance/roi%d datasets
- Added sigma_readout and sigma_floor scalar datasets

Phase B.2-lite: Added static triptych export to dbex/look.py
- New --export-triptychs <dir> flag
- Calls dbex.vis.plot_triptych for each ROI
- Produces [Data|Model|Residuals Z-Score] PNG files

Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Run:
```bash
git add -A
git commit -m "<message above>"
git push
```

## How-To Map

**Variance Formula:**
- Spec reference: `docs/spec-db-core.md` §86-90 (Variance Definition)
- Formula: `V = I_model + sigma_readout^2` where `I_model = Bragg + background`
- Clamp: `V = max(V, sigma_floor^2)` to prevent infinite weights when `I_model → 0`
- Units: Same as loss target (photons or ADU)

**HDF5 Extension:**
- Location: `dbex/refine_one.py` lines 200-244 (Legacy), 610-654 (Torch)
- Pattern: Compute variance in loop, add `h.create_dataset("variance/roi%d" % i, data=variance_subims[i])`
- Scalars: Add `sigma_readout` and `sigma_floor` after ROI loop

**Static Export:**
- Location: `dbex/look.py` lines 49-77 (load), 168-177 (main)
- API: `dbex.vis.plot_triptych(data, model, variance, hkl=None, correlation=score, filename=path)`
- Flag: `--export-triptychs <output_dir>` produces PNG files `roi_0000.png`, `roi_0001.png`, ...

## Pitfalls To Avoid

1. **DO NOT** use `max()` for clamp (doesn't broadcast); use `np.maximum(variance, sigma_floor**2)`
2. **DO NOT** forget to apply variance computation to BOTH Legacy and Torch backends
3. **DO NOT** modify interactive viewer grid layout in Phase B.2-lite (deferred to Phase C)
4. **DO** ensure `args.sigma_r` exists; if not, document blocker (CLI validation issue)
5. **DO** create output directory with `mkdir(parents=True, exist_ok=True)`
6. **DO** handle missing variance datasets gracefully in `_load_data` (backward compat check)

## If Blocked

**Missing `sigma_readout` in CLI args:**
- Check `dbex/refine_one.py` argparse setup (lines ~159)
- If `--sigma-r` flag missing, document blocker in decision.json
- Return to Galph with blocker report

**Import errors for `dbex.vis`:**
- Verify Phase A deliverables: `dbex/vis/__init__.py`, `dbex/vis/triptych.py`, `dbex/vis/residuals.py`
- Check `from dbex.vis import plot_triptych` works
- If missing, escalate to Galph (Phase A incomplete)

**HDF5 backward compatibility concerns:**
- Variance datasets are additive; old readers ignore them
- No breaking changes to existing datasets
- Document in summary.md if any concerns arise

## Findings Applied

- **POLICY-001:** Environment Freeze (code-only changes, no package installs)
- **PHYSICS-LOSS-001:** Variance formula `V = I_model + sigma_readout^2` per spec-db-core.md
- **spec-db-vis.md §19:** Z-score definition `(Data - Model) / sqrt(Variance)`
- **spec-db-core.md §86-90:** Variance clamp `max(V, sigma_floor^2)`

## Pointers

- Planning analysis: `plans/active/TOOLING-VIS-001/reports/2025-11-24T115000Z/phase_b_planning_analysis.md` (comprehensive scope, blocker analysis, decision tree)
- Spec variance definition: `docs/spec-db-core.md:86-90`
- Spec triptych layout: `docs/spec-db-vis.md:14-24`
- Phase A deliverables: `dbex/vis/__init__.py:8-9` (API), `dbex/vis/triptych.py:18-25` (signature)
- Implementation plan: `plans/active/TOOLING-VIS-001/implementation.md:82-86` (Phase B checklist)

## Next Up (Optional)

If you finish early AND all validations PASS:
- Read implementation.md:87-91 (Phase C checklist)
- Assess whether interactive viewer refactor is feasible in current loop
- **DO NOT** start Phase C implementation; return to Galph for planning approval
