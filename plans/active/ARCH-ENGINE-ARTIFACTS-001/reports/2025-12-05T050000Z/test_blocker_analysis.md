# Stage B Parity Test Blocker Analysis

## Issue Summary
Stage B parity test (`test_stage_b_artifact_matches_helper_shell_mode`) SKIPPED due to sigma source infrastructure mismatch.

## Root Cause
The test fixture and test logic have misaligned expectations for sigma_readout provenance:

1. **Test expectation** (tests/dbex/test_artifact_parity.py:65):
   - Requires `sigma_readout_map_source == "external_lookup"`
   - This means sigma should be loaded from dxtbx imageset external_lookup metadata

2. **Fixture behavior** (tests/conftest.py:465-471):
   - When `smoke_sigma_source == "metadata"`, the fixture passes `args.sigma_map=<path>` to DataLoad
   - DataLoad then sets `sigma_readout_map_source = "cli_map"` (dbex/data_load.py:471)
   - This causes the test to skip because the source is `"cli_map"` not `"external_lookup"`

## Code Evidence

### Test skip condition (tests/dbex/test_artifact_parity.py:65-72)
```python
if sigma_map is None or sigma_map_source != "external_lookup":
    pytest.skip(
        "Metadata sigma source requested but DataLoad lacks an external_lookup sigma_readout_map. "
        "Ensure sp.proc/idx-0000_sigma_metadata.expt and "
        "idx-0000_sigma_metadata.sigma_tiles.pkl exist by running "
        "plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py "
        "with --sigma-value/--sigma-map."
    )
```

### Fixture sigma_map loading (tests/conftest.py:109-130)
```python
if smoke_sigma_source == "metadata":
    sigma_map_override = os.environ.get("DBEX_SMOKE_SIGMA_MAP_PATH")
    if sigma_map_override:
        sigma_map_path = repo_root / sigma_map_override
    else:
        # Default to cropped sigma-map for small detector, full sigma-map otherwise
        if smoke_detector_size == "small":
            sigma_map_path = repo_root / "sp.proc" / "refGeom_small" / "idx-0000_sigma_metadata_small.sigma_tiles.pkl"
        else:
            sigma_map_path = repo_root / "sp.proc" / "idx-0000_sigma_metadata.sigma_tiles.pkl"
```

Then passes this as `args.sigma_map=str(smoke_dataset_paths.sigma_map_path)` (line 255).

### DataLoad behavior (dbex/data_load.py:465-483)
```python
def _initialize_sigma_readout_map(self) -> None:
    """Populate `sigma_readout_map` from CLI assets or metadata."""
    sigma_map_path = getattr(self.args, "sigma_map", None)
    if sigma_map_path:
        self.sigma_readout_map = load_sigma_readout_map(
            sigma_map_path,
            self.data.shape
        )
        self.sigma_readout_map_source = "cli_map"  # ← Sets source to "cli_map"
        self.sigma_readout_map_metadata = {"path": str(sigma_map_path)}
        return

    imageset = getattr(self.Expt, "imageset", None)
    metadata_map, metadata = _load_external_lookup_sigma_map(
        imageset,
        self.data.shape
    )
    if metadata_map is not None:
        self.sigma_readout_map = metadata_map
        self.sigma_readout_map_source = "external_lookup"  # ← Would need this
        self.sigma_readout_map_metadata = metadata
```

## Required Fix
To make the test work, sigma tiles must be embedded in the experiment file's imageset as external_lookup metadata, NOT passed via CLI args.

The skip message references the correct script:
```
plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py
```

This script should embed the sigma tiles into `sp.proc/idx-0000_sigma_metadata.expt` (and the small variant) so that DataLoad loads them from `imageset.external_lookup` instead of CLI args.

## Initiative Type Impact
This is an **architecture** initiative. Changing test acceptance criteria (relaxing the `"external_lookup"` check) would be out of scope. The blocker is a test infrastructure / data dependency issue, not a test logic issue.

## Recommended Action
1. Mark focus item `blocked_environment_dependency` in fix_plan.md
2. Surface to supervisor (Galph) that the sigma embedding script needs to run to generate the correct metadata experiment files
3. Do NOT modify the test's sigma source check (that's the acceptance criterion)
4. Do NOT proceed with baseline_crystal fix validation until the blocker is resolved

## Files/Artifacts
- Test log: plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T050000Z/pytest_stage_b_fixed.log
- Code fix already applied: tests/dbex/test_artifact_parity.py:326 (baseline_crystal=crystal)
- Data files exist:
  - sp.proc/idx-0000_sigma_metadata.sigma_tiles.pkl ✓
  - sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl ✓
  - sp.proc/idx-0000_sigma_metadata.expt ✓
- Missing: external_lookup embedding in experiment files
