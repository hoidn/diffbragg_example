# Environment Remediation — Sigma Embedding Infrastructure

## Loop Context
- **Initiative:** ARCH-ENGINE-ARTIFACTS-001 (RefinementEngine artifact channel & final-Bragg unification)
- **Phase:** B.2 (Parity validation)
- **Timestamp:** 2025-12-02T194000Z
- **Actor:** Galph (supervisor)
- **Action Type:** Environment remediation (supervisor-only, per Environment Freeze exception)

## Blocker Summary
Phase B.2 parity tests (created in loop 2025-12-05T040000Z, attempt 2) were SKIPPED because:
1. Tests require `sigma_readout_map_source == "external_lookup"` (test_artifact_parity.py:65-72)
2. Test fixture passed sigma via CLI args → DataLoad set `source="cli_map"` (dbex/data_load.py:471)
3. Experiment files with embedded sigma tiles did not exist in current workspace (only in old workspace per manifest)

## Root Cause
Sigma metadata experiment files existed in prior workspace (`/home/ollie/Documents/diffbragg_example_2/diffbragg_example/`) per `sp.proc/sigma_metadata_manifest.json`, but were not present in current workspace (`/home/ollie/Documents/diffbragg_example`).

## Remediation Actions
Generated sigma metadata experiment files using the existing `embed_sigma_external_lookup.py` script:

### Full Detector
```bash
python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py \
  --expt refGeom.expt \
  --expt-idx 0 \
  --sigma-value 3.0 \
  --output sp.proc/idx-0000_sigma_metadata.expt \
  --report plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000000Z/sigma_metadata_full.json \
  --manifest sp.proc/sigma_metadata_manifest.json
```

**Outputs:**
- `sp.proc/idx-0000_sigma_metadata.expt` (5.2K, experiment with embedded sigma tiles)
- `sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl` (24M, flex.double tiles for 1 panel @ 2527×2463)
- Manifest: `sp.proc/sigma_metadata_manifest.json`
- Report: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000000Z/sigma_metadata_full.json`

### Small Detector
```bash
python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py \
  --expt sp.proc/refGeom_small/refGeom_small.expt \
  --expt-idx 0 \
  --sigma-value 3.0 \
  --output sp.proc/refGeom_small/idx-0000_sigma_metadata_small.expt \
  --report plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000000Z/sigma_metadata_small.json \
  --manifest sp.proc/refGeom_small/sigma_metadata_manifest_small.json
```

**Outputs:**
- `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.expt` (5.3K, experiment with embedded sigma tiles)
- `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl` (4.1M, flex.double tiles for 1 panel @ 1024×1024)
- Manifest: `sp.proc/refGeom_small/sigma_metadata_manifest_small.json`
- Report: `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-02T000000Z/sigma_metadata_small.json`

## Verification
All files created successfully:
```
sp.proc/idx-0000_sigma_metadata.expt              5.2K  2025-12-02 19:40
sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl   24M   2025-12-02 19:40
sp.proc/refGeom_small/idx-0000_sigma_metadata_small.expt              5.3K  2025-12-02 19:40
sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl  4.1M  2025-12-02 19:40
```

## Expected Outcome
With sigma tiles embedded in `imageset.external_lookup.pedestal`:
1. Fixture loads experiment files (idx-0000_sigma_metadata.expt instead of idx-0000_refined.expt)
2. DataLoad sets `sigma_readout_map_source = "external_lookup"` (dbex/data_load.py:469)
3. Tests no longer SKIP
4. Both parity tests should execute:
   - `test_stage_a_artifact_matches_helper` → PASSED (already passed in attempt 2)
   - `test_stage_b_artifact_matches_helper_shell_mode` → PASSED (baseline_crystal fix already applied)

## Compliance
- **Environment Freeze Exception:** Generating test infrastructure data files (sigma embedding) is permitted per CLAUDE.md Environment Freeze exception for test infrastructure setup. No package installs or upgrades were performed.
- **Initiative Type Constraint:** Architecture initiatives cannot modify test acceptance criteria. The `sigma_readout_map_source == "external_lookup"` requirement is normative for this phase.
- **Lifecycle Impact:** No implementation code changes this loop. Lifecycle counter: `implementation_attempt_count=3` for Phase B.2 (attempt 1: created tests, attempt 2: diagnosed baseline_crystal bug, attempt 3: retry after sigma embedding).

## Next Action
Ralph will retry parity tests per `input.md` (2025-12-02T194000Z). Expected: both tests PASS, Phase B.2 complete.

## Artifacts
- Sigma metadata reports: `sigma_metadata_{full,small}.json` (this directory)
- Manifests: `sp.proc/sigma_metadata_manifest.json`, `sp.proc/refGeom_small/sigma_metadata_manifest_small.json`
- Pending: `pytest_parity_retry.log` (Ralph's next execution)
