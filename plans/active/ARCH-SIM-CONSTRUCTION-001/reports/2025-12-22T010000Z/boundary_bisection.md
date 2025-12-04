# Boundary Bisection Plan — Mosaic-Domain Sweep

**Boundary:** RefinementConfig `stage_a_mosaic_domains` (producer: `dbex/refinement/config.py:90-110`) → crystal hydration (`dbex/refinement/config_factories.py:287-457`) → `nanobrag_torch` simulator sampling inside Stage A (`dbex/refinement/stage_a.py:400-520`) → DB-AT-028/029 consumers (`tests/dbex/test_stage_a_smoke_parity.py:150-320`).

**Independent reference:** DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` (used by `compare_stage_a_baseline.py` reflection ledger). It is independent because it measures integrated ROI intensities from the experiment, not from nanobrag_torch.

**Hypothesis:** Even after threading `stage_a_mosaic_domains` through Stage A/mapping/reconstruction, the simulator still behaves as if `mosaic_domains=1`. A domain sweep (1 vs 16+) should produce distinct StageA/reflection ratios if the parameter is honored. Identical ratios would prove the simulator ignores the override and keep the parity crisis pinned to the simulator boundary.

**Instrumentation plan (next loop):**
1. Extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` with `--stage-a-mosaic-domains` (int ≥1) and persist the applied count + StageA/reflection median ratios inside the JSON output/console summary. Record the value inside `probe_metadata` so reports are traceable.
2. Re-run the baseline probe twice under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/`:
   - `mosaic_domains=1`, `--geometry-mode baseline` → output file `domain1/stage_a_baseline_probe_baseline.json`
   - `mosaic_domains=16`, `--geometry-mode baseline` (current default) → `domain16/stage_a_baseline_probe_baseline.json`
3. Compare the reflection ledger statistics between the two runs. If the StageA/reflection median stays ≈0.061 for both, the override is ineffective and we escalate to instrumenting nanobrag_torch itself (Environment Freeze exception path). If the ratios diverge, continue tuning `stage_a_mosaic_domains` until ROI correlations stop being negative.
4. Run DB-AT-028/029 once with the default `stage_a_mosaic_domains=16` and capture artifacts in the same report directory so we can correlate the sweep findings with the failing selectors.

**Decision rule:**
- *No change between domain counts* → confirm `mosaic_domains` is ignored, schedule a targeted nanobrag_torch instrumentation patch (DIAG initiative) to log the sampled domains per panel.
- *Meaningful change (ROI median flips sign or chi² drops orders of magnitude)* → continue exploring multi-domain physics within dbex (tune domain count, revisit domain size).
