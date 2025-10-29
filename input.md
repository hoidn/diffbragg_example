**Summary**: Align nanobrag_torch Miller index math with reciprocal vectors so the torch forward baseline emits non-zero intensities for DB_AT_001.

**Mode**: Parity

**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

**Branch**: integration

**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001

**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/

**Do Now**
- NANOBRAG-GOLDEN-001:
  - Implement: /home/ollie/Documents/nanoBragg/src/nanobrag_torch/simulator.py::compute_physics_for_position — swap to rotated reciprocal vectors (a*/b*/c*) when computing `h,k,l` and add bounded logging to capture in-range hit rates per panel.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
  - Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/

**Priorities & Rationale**
- Respect docs/architecture/parameter_trace_analysis.md:47 guidance that Miller indices use reciprocal vectors, eliminating the zero-output bug observed in 2025-10-29T091339Z/canonical_capture.log.
- Keep structure-factor ingestion compliant with docs/spec-db-core.md:20-47 so canonical tensors align `[panel, slow, fast]` ordering when parity tests reload them.
- Honor forward-equivalence thresholds from docs/forward_equivalence.md:30-58 to confirm parity metrics become meaningful once torch output is non-zero.
- Preserve CONFIG-001 mapping guarantees (docs/config_crosswalk.md:15-72) while altering the simulator math so downstream fixtures stay valid.

**How-To Map**
- Edit /home/ollie/Documents/nanoBragg/src/nanobrag_torch/simulator.py near the `h = dot_product(...)` block to replace real-space rotations with cached reciprocal vectors and emit debug counters guarded by the existing logger.
- Regenerate torch tensors by running `python scripts/generate_simple_cubic_golden.py --out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T092655Z/golden_dataset` (Environment Freeze: reuse existing env inputs).
- Archive updated capture logs and tensor artifacts under the loop directory before invoking pytest.
- Run `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001` and store `--collect-only` + test logs alongside metrics.json in the artifacts directory.

**Pitfalls To Avoid**
- Do not touch package installs or rebuilds (Environment Freeze).
- Keep structure-factor tensors on the same device/dtype as the simulator to avoid implicit CPU copies zeroing data.
- Ensure logging stays bounded (<100 lines) to prevent canonical_capture.log bloat.
- Reuse existing ROI masks; never invert trusted mask polarity (per CONFIG-001 / GEOMETRY-001).
- Confirm steps multiplier stays non-zero when editing `_compute_physics_for_position` to avoid divide-by-zero after normalization.
- Save a `.patch` capturing simulator changes in the artifact directory for reproducibility.
- Avoid modifying DiffBragg baseline paths; only touch torch-side math this loop.
- Watch for torch compile caches; keep `NANOBRAGG_DISABLE_COMPILE=1` unset unless debugging per RUNTIME-001.
- Record new metric deltas (torch_max, roi coverage) in metrics.json before parity test.
- Keep pytest to the mapped selector; no extra modules beyond evidence scope.

**If Blocked**
- If simulator changes still return all-zero frames, mark NANOBRAG-GOLDEN-001 as `blocked` in docs/fix_plan.md with the new log snippet, note the failing `torch_max=0` signature in docs/findings.md, and pivot to dependency analysis.

**Findings Applied (Mandatory)**
- CONFIG-001 — Maintain beam/geometry mapping consistency while adjusting Miller index math.
- CONFORMANCE-001 — Validate against DB_AT_001 acceptance thresholds once torch outputs are non-zero.
- PARITY-001 — Capture first-divergence style metrics in metrics.json to trace earliest mismatch after the fix.
- TESTING-003 — Reconfirm the DB_AT_001 selector via pytest `--collect-only` and log the artifact in the loop directory.
