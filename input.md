**Summary**: Realign nanoBragg torch HKL projection with the C reference so DB_AT_001 panels receive non-zero structure factors.

**Mode**: Parity

**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

**Branch**: integration

**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001

**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/

**Do Now**
- NANOBRAG-GOLDEN-001:
  - Implement (A3): nanobrag_torch/simulator.py::_compute_physics_for_position — revert Miller index projection to the rotated real-space vectors (meters) used in nanoBragg.c, remove the incorrect Å⁻¹ conversion, and emit bounded HKL min/max + hit-rate diagnostics per panel into the capture log.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
  - Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/

**Priorities & Rationale**
- Honor docs/spec-db-core.md:35-54 geometry and `[panel, slow, fast]` ordering so real-space vectors remain meter-scaled before dotting the scattering vector.
- Follow docs/nanobrag_api.md:71-105 guidance that Simulator physics matches the C reference per-pixel, ensuring non-zero `bragg_torch` tensors.
- Apply docs/development/testing_strategy.md:112 trace requirements to capture Miller index stats that explain first divergence when torch output is zero.
- Keep mapped selector in docs/TESTING_GUIDE.md:64-87 passing so DB_AT_001 remains an Active acceptance guard per CONFORMANCE-001.
- Preserve CONFIG-001 safeguards from docs/config_crosswalk.md:32-72 so detector/beam mappings stay unchanged while adjusting physics math.

**How-To Map**
- Edit nanobrag_torch/simulator.py, updating `compute_physics_for_position` to project the 1/m scattering vector against `rot_a/rot_b/rot_c`, record `h0/k0/l0` extrema, and print a single `[HKL stats]` line per panel.
- Regenerate tensors: `python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/torch_hkl_debug.json | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/canonical_capture.log`.
- Archive HKL stats (copy `torch_hkl_debug.json` and capture log) alongside updated tensors before running tests.
- Run parity smoke: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/pytest_forward.log`.
- If the selector still xfails after fix, capture `pytest --collect-only` output to confirm >0 tests and log metrics deltas in `metrics.json`.

**Pitfalls To Avoid**
- Do not touch environment packages or rebuild simtbx (Environment Freeze); treat missing imports as blockers.
- Keep scattering math device-neutral—no `.cpu()` or dtype casts that break CONFIG-001 guarantees.
- Ensure the HKL diagnostics print once per panel to keep logs under 100 lines.
- Confirm `h0/k0/l0` tensors stay on simulator device before min/max to avoid graph breaks under torch.compile.
- Preserve polarization and lattice-factor logic; only adjust the projection math and logging guards.
- Maintain canonical `[panel, slow, fast]` tensor ordering when saving `bragg_torch.npy`.
- Capture and store a `.patch` of simulator changes in the artifacts directory for reproducibility.
- Reuse existing ROI masks; never flip trusted mask polarity.
- Record updated `torch_max`, `hit_rate`, and HKL bounds in `metrics.json` to document the change.
- Stop immediately if generator still reports `torch_max=0` and log the failure before re-running tests.

**If Blocked**
- If HKL stats remain out of bounds or torch output stays zero, mark NANOBRAG-GOLDEN-001 `blocked` in docs/fix_plan.md with the new `[HKL stats]` excerpt, note the failing signature in docs/findings.md, and halt implementation pending clarification on scattering vector conventions.

**Findings Applied (Mandatory)**
- CONFIG-001 — Fix keeps dxtbx→simulator mappings intact while adjusting lattice math.
- CONFORMANCE-001 — Uphold DB_AT acceptance thresholds by validating the canonical selector after the fix.
- PARITY-001 — Use HKL diagnostics to feed first-divergence tracing once tensors go non-zero.
- TESTING-003 — Reconfirm the mapped selector collects >0 tests and archive logs as evidence.
- DIAGNOSTICS-001 — Log structured HKL metrics alongside canonical artifacts for reproducible debugging.
