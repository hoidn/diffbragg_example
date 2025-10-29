# Phase A Notes — Golden Data Inventory

## Dataset Survey

**Date:** 2025-10-29T010131Z
**Loop:** PARITY-HARNESS-002 A1

### nanoBragg2 Mirror Status
- External path `nanoBragg2/tests/golden_data/simple_cubic/`: NOT FOUND
- No nanoBragg2 repository cloned in working tree

### DBEX Local Fixtures
- `tests/fixtures/golden_data/`: Created empty directory structure
- No pre-existing golden data or manifests

### Available Test Data
- Examining existing test infrastructure from test_nanobrag_smoke.py
- refGeom.expt, scaled.mtz potentially available (checking...)

### Fallback Strategy
Per input.md:21-22, if nanoBragg2 mirror unavailable:
- Craft fallback tensors using existing smoke helpers
- Use refGeom experiment data as basis for simple cubic golden set
- Generate minimal representative dataset with documented provenance

## Next Steps
1. Check refGeom file availability
2. Generate simple cubic golden tensors from smoke test infrastructure
3. Create manifest.json with SHA256 checksums
4. Document provenance in manifest
