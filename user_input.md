# MANUAL OVERRIDE: Smoke Test Resource Guardrail

**Directives:**
1. Do not proceed with heavy debugging loops that rerun Stage A/B/C smoke tests until we control their runtime and VRAM footprint.
2. Prioritize PERF-SMOKE-DETSIZE (or an equivalent mitigation) so smoke fixtures can run on a cropped/small detector while parity tests keep the full dataset.
3. Document any alternative approach in the fix plan if you choose a different strategy; the key requirement is to make repeated smoke runs practical on developer GPUs.

**Action Plan:**
- Focus item: PERF-SMOKE-DETSIZE (refGeom_small fixture and gated tests) or a documented equivalent.
- Deliverables:
  * `refGeom_small.expt/.refl` (or comparable optimization) with README and artifacts showing runtime/VRAM improvements.
  * Updated `tests/dbex/test_torch_refine_smoke.py` fixtures allowing small/full detector selection; smoke defaults to the low-resource dataset.
  * Updated docs/TESTING_GUIDE.md noting the new workflow and how parity tests still use the full detector.
- Only after this item is done may you resume deep debugging/telemetry loops that iterate on Stage A/B/C.
