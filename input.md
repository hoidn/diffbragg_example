**Summary**: Align nanoBragg’s incident-beam orientation with the C reference so the canonical DB_AT_001 torch tensors carry non-zero intensities.

**Mode**: Parity

**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

**Branch**: integration

**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001

**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/

**Do Now (hard validity contract)**
- Implement: ../nanoBragg/src/nanobrag_torch/simulator.py::Simulator.__init__ — cache the source→sample incident beam vector (negate and normalize the detector beam vector) so single-source runs share the convention already used in the multi-source path, then persist a `.patch` in the loop artifacts.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/golden_dataset/

**Priorities & Rationale**
- docs/config_crosswalk.md:27-33 requires the bridge to expose the beam vector as sample→source; the simulator must flip it back to source→sample before using `q = (k_f - k_i)` so HKL indices land inside the P1 grid.
- docs/forward_equivalence.md:21-52 mandates regenerating paired DiffBragg/torch stacks and parity metrics once the physics bug is fixed so we re-establish forward equivalence evidence.
- docs/spec-db-conformance.md:23-26 keeps DB_AT_001 as the canonical acceptance check; we must rerun it immediately after regenerating tensors.
- docs/TESTING_GUIDE.md:86-87 documents the exact selector/command we rely on; keeping it green upholds TESTING-003.
- docs/findings.md (HKL-ORIENT-001) records the orientation pitfall we are correcting; the loop’s plan adheres to that lesson before moving fixtures/manifest changes forward.

**How-To Map**
1. Export canonical tensors with HKL stats: `PYTHONPATH=../nanoBragg/src:$PYTHONPATH python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/torch_hkl_debug.json | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/canonical_capture.log`.
2. Verify `[HKL stats]` lines in the capture log sit within the structure-factor bounds (e.g., `grep "HKL stats" canonical_capture.log`) and record the new `torch_max`/`hit_rate` into `metrics.json`.
3. Parity validation: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/pytest_db_at_001.log` and archive the updated tensors/metrics under `golden_dataset/`.

**Pitfalls To Avoid**
- Environment Freeze: do not reinstall packages or rebuild simtbx; log any missing import as a blocker instead.
- Negate the beam vector once—avoid double-negating in multi-source code paths which already flip `source_directions`.
- Keep tensors/device placement intact; no `.cpu()` or dtype downgrades around the incident vector change.
- Ensure the `.patch` saved in artifacts only contains the targeted `Simulator.__init__` edit.
- Confirm `bragg_torch.npy` is non-zero before touching fixtures/manifest files.
- Maintain `[panel, slow, fast]` ordering when saving regenerated stacks.
- Run pytest with `KMP_DUPLICATE_LIB_OK=TRUE` to match documented runtime guardrails.
- Inspect HKL stats before tests—if bounds regress, stop and capture the failure rather than overwriting good artifacts.
- Leave `torch.compile` enabled unless the fix requires an env guard already documented in findings.
- Keep artifact paths unique per loop to avoid overwriting prior evidence.

**If Blocked**
- If HKL stats still miss the grid or torch output stays zero, halt implementation, append the new log snippet to docs/fix_plan.md Attempts History, stash `canonical_capture.log`/`torch_hkl_debug.json` under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T100617Z/`, and set the initiative to `blocked` pending deeper scattering analysis.

**Findings Applied (Mandatory)**
- HKL-ORIENT-001 — Plan explicitly flips the cached incident vector to match the documented source→sample requirement.
- CONFIG-001 — Honor dxtbx→torch geometry mapping while adjusting physics math.
- CONFORMANCE-001 — Re-run DB_AT_001 acceptance selector after regenerating tensors.
- TESTING-003 — Capture fresh pytest/collect evidence proving the selector still collects >0 tests.
- PARITY-001 — Use the updated HKL stats and parity metrics as first-divergence breadcrumbs once tensors go non-zero.
