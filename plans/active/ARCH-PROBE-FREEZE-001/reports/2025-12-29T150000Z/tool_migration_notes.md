# Sigma Embedding Tool Migration Summary

## Migration Complete

The sigma metadata embedding helper has been successfully promoted from plan-local script to production owner module.

### New Canonical Entry Point

**Primary CLI:**
```bash
python -m dbex.tools.embed_sigma_external_lookup \
  --expt <input.expt> \
  --output <output.expt> \
  --expt-idx 0 \
  --sigma-value 3.0 \
  --report <report.json> \
  --manifest <manifest.json>
```

**Legacy Compatibility:**
The plan script `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` now delegates to the canonical module, preserving backward compatibility with existing automation.

### Implementation Location

- **Owner module:** `dbex/tools/embed_sigma_external_lookup.py` (365 lines)
  - Core embedding function: `embed_sigma_external_lookup()`
  - CLI entry point: `main()`
  - Manifest/report generators
  - Argument parsing and validation

- **Legacy shim:** `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` (19 lines)
  - Imports and delegates to `dbex.tools.embed_sigma_external_lookup.main()`

### Documentation Updates

All references updated to point to canonical tool:

1. **docs/TESTING_GUIDE.md** (lines 115-125)
   - Primary reference: `python -m dbex.tools.embed_sigma_external_lookup`
   - Legacy note preserved

2. **sp.proc/README.md** (lines 28-34)
   - Example command uses canonical CLI

3. **Test skip messages:**
   - `tests/sp_proc/test_sigma_metadata_fixture.py:31-33` ✓
   - `tests/conftest.py:134-135` ✓
   - `tests/dbex/test_mapping_consistency.py:97-98` ✓
   - `tests/dbex/test_torch_refine_smoke.py:337-338` ✓
   - `tests/dbex/test_artifact_parity.py:70-71` ✓

### Validation Results

1. **Sigma metadata fixture test:** PASSED
   ```
   pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py
   ```
   - Manifest validation successful
   - External lookup sigma map loading verified
   - `sigma_readout_provenance="external_lookup"` confirmed

2. **Tool functionality:** VERIFIED
   - Successfully regenerated small detector sigma metadata:
     - `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.expt`
     - `sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl`
     - `sp.proc/refGeom_small/sigma_metadata_manifest_small.json`
   - CLI help output captured (tool_help.txt)

3. **Stage A metadata smoke test:** Environment-blocked (CUDA OOM)
   - Test loaded metadata successfully (config shows `sigma_readout_provenance="external_lookup"`)
   - Failure unrelated to sigma embedding migration
   - OOM issue is pre-existing environment constraint

### Architecture Conformance

✅ Satisfies ARCH-PROBE-FREEZE-001 requirements:
- Canonical owner API established in `dbex.tools`
- Plan-local script reduced to thin compatibility shim
- Documentation references canonical tool
- No new plan-local probe semantics

✅ Satisfies diagnostic_script_policy (prompts/supervisor.md:272-309):
- Production semantics live in owner module
- Plan scripts delegate to canonical implementation
- No shadow pipeline duplication

✅ Satisfies spec-db-core.md:32-68 sigma provenance contract:
- Metadata embedding uses owner module `dbex.data_load.load_sigma_readout_map`
- External lookup injection preserves provenance tracking
- Manifest includes full reproducibility metadata

## Next Steps

- Stage A metadata smoke requires OOM remediation (separate initiative)
- Consider adding enforcement test under `tests/architecture/` to prevent plan-local probe script expansion
