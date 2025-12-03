# Do Now — ARCH-SIM-CONSTRUCTION-001 Phase C.1 Debug Instrumentation

## Summary
Add debug instrumentation to reconstruction helper to diagnose the 23,400× scale mismatch between expected and actual bragg_after output.

## Mode
none (debugging / evidence collection)

## InitiativeType
architecture

## Focus
[ARCH-SIM-CONSTRUCTION-001] — Simulator Construction Convention Alignment (Training vs Reconstruction)

## Branch
integration

## Mapped tests
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity -s
```

(Single test for faster iteration; `-s` flag captures print output)

## Artifacts
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T121500Z/`

---

## Do Now

### Context

Ralph correctly removed `* sqrt_spot_scale` per my prior diagnosis (2025-12-03T005008Z), but this made `bragg_after` output 23,400× too small (1.02e-05) instead of matching the expected ~0.24.

My analysis was incomplete. Before making another code change, we need empirical data showing:
1. What is the **raw simulator output** (`bragg_panel.mean()` before any scaling)?
2. What is `scale_factor` actually computed as?
3. What is `log_scale_baseline` from telemetry?
4. What is `log_scale` (the delta parameter)?
5. What is `sqrt_spot_scale`?

### Task

**Instrument `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` to print intermediate values:**

1. **Add debug prints at line ~235** (just before the loop):
   ```python
   # DEBUG instrumentation for ARCH-SIM-CONSTRUCTION-001
   print(f"[ARCH-SIM-CONSTRUCTION-001 DEBUG]")
   print(f"  log_scale_baseline_value: {log_scale_baseline_value}")
   print(f"  log_scale (param_deltas_a): {param_deltas_a.get('log_scale', {}).get('final', 'MISSING')}")
   print(f"  delta_bound: {delta_bound}")
   print(f"  scale_factor (after exp): {scale_factor.item() if hasattr(scale_factor, 'item') else scale_factor}")
   print(f"  sqrt_spot_scale: {sqrt_spot_scale}")
   print(f"  spot_scale_override: {spot_scale_override}")
   ```

2. **Add debug print inside the simulator loop** (after line 237, inside the `for pid, sim in zip...` loop):
   ```python
   bragg_panel = sim.run()
   # DEBUG: print first panel's raw output
   if pid == 0:
       print(f"  bragg_panel[0] mean (raw sim output): {bragg_panel.mean().item():.6e}")
       print(f"  bragg_panel[0] max: {bragg_panel.max().item():.6e}")
   bragg_scaled = bragg_panel * scale_factor
   if pid == 0:
       print(f"  bragg_scaled[0] mean (after scale_factor): {bragg_scaled.mean().item():.6e}")
   ```

3. **Add final bragg_full summary** (after the loop, before return):
   ```python
   # DEBUG: final output summary
   print(f"  bragg_full mean (final output): {bragg_full.mean():.6e}")
   print(f"  bragg_full max: {bragg_full.max():.6e}")
   print(f"[END DEBUG]")
   ```

### Expected Outcome

Test will FAIL (same as before), but pytest log with `-s` flag will show:
```
[ARCH-SIM-CONSTRUCTION-001 DEBUG]
  log_scale_baseline_value: 20.138...
  log_scale (param_deltas_a): 0.0 (or small number)
  scale_factor (after exp): 5.57e+08
  sqrt_spot_scale: 5.57e+08
  bragg_panel[0] mean (raw sim output): <CRITICAL VALUE>
  bragg_scaled[0] mean (after scale_factor): <CRITICAL VALUE>
  bragg_full mean (final output): 1.02e-05 (matches prior loop)
[END DEBUG]
```

The **raw sim output** value will tell us if the simulator is producing the same magnitude as Stage A or not.

### Validation

Run the mapped test, capture the full pytest output (including debug prints), and save to:
```
plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T121500Z/pytest_db_at_028_debug.log
```

Extract the debug block and save to:
```
plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T121500Z/debug_output.txt
```

### Pitfalls To Avoid

1. **Do NOT change any logic** — only add print statements
2. **Do NOT remove the debug prints after capturing** — leave them for the next loop
3. **Use `.item()` when printing tensors** to avoid large tensor dumps
4. **Capture FULL pytest output** including `-s` flag so prints are visible

### Findings Applied

- SCALE-009: Spot-scale baseline embedding — confirms log_scale_baseline = log(sqrt(spot_scale))
- ARCH-ENGINE-002: Lazy import hygiene — use existing module-scope imports

### Pointers

- Reconstruction helper: `dbex/refinement/reconstruction.py:148-241`
- Stage A baseline derivation reference: `dbex/refinement/stage_a.py:435-468`
- simulate_forward_once scaling: `dbex/nanobrag_bridge.py:1428-1438`
- Test: `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity`

### If Blocked

If the test times out or crashes before printing debug output:
1. Add the prints earlier (before the simulator loop)
2. Reduce to minimal instrumentation (just log_scale_baseline + scale_factor)
3. Capture whatever output is available and note the crash point

---

## Next Up

After capturing debug output, Galph will analyze the empirical values to determine:
- Whether the simulator raw output matches Stage A's magnitude
- Whether scale_factor is correct
- What correction (if any) is needed to line 238
