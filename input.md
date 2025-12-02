Summary:
- Remove the `RefinementInputs`/config factory re-export shim from `dbex.nanobrag_bridge` by moving all remaining callers to `dbex.refinement.{inputs,config_factories}` and prove there is no behavior drift.

Mode: Parity

InitiativeType: architecture

Focus: ARCH-BRIDGE-RESP-001 — Writer / bridge responsibility split

Branch: integration

Mapped tests:
- tests/dbex/test_nanobrag_bridge.py
- tests/dbex/test_background_semantics.py::TestBackgroundSentinelGuard::test_background_sentinel_guard
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata

Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T041200Z/

Do Now:
- Implement: Use `rg "dbex\\.nanobrag_bridge.*prepare_refinement_inputs" -n` and `rg "dbex\\.nanobrag_bridge.*create_" -n` to locate every caller still importing `prepare_refinement_inputs`, `RefinementInputs`, or the config factories from the bridge (tests such as `tests/dbex/test_mapping_consistency.py`, `tests/dbex/test_mask_semantics.py`, `tests/dbex/test_background_semantics.py`, `tests/dbex/test_calibration_policy.py`, `tests/dbex/test_nanobrag_smoke.py`, `tests/dbex/test_torch_refine_smoke.py`, `tests/dbex/test_gradients.py`, CLI/vis tooling scripts under `plans/active/**/bin/*.py`, etc.). Update each file to import from `dbex.refinement.inputs` / `dbex.refinement.config_factories` instead, adjust fixtures/mocks accordingly, and ensure CLI/test patches (`@patch(...)`) point at the new module paths.
- Implement: In `dbex/nanobrag_bridge.py`, drop the top-level `from dbex.refinement.inputs import RefinementInputs, prepare_refinement_inputs` and config factory re-exports. Keep any necessary type hints under a `TYPE_CHECKING` block or via module imports (`import dbex.refinement.inputs as refinement_inputs`) so the bridge can still annotate arguments without exposing the names. Update module docstrings/comments to state that refinement input prep now lives under `dbex.refinement.inputs` and that the bridge only handles HKL/calibration/orchestration helpers.
- Implement: Update documentation that still claims `prepare_refinement_inputs` lives in the bridge (e.g., `docs/architecture/dbex/physics/forward.idl.md`, `docs/spec-db-conformance.md`, `docs/config_crosswalk.md`) so they cite `dbex.refinement.inputs`. Run `rg "nanobrag_bridge.*prepare_refinement_inputs" docs -n` to confirm there are no stale references.
- Validate: Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_nanobrag_bridge.py --maxfail=1`.
- Validate: Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_background_semantics.py::TestBackgroundSentinelGuard::test_background_sentinel_guard --maxfail=1` to prove the sentinel/loss-mask guards still pass with the new import path.
- Validate: Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1` so the CLI path (and ROI payload plumbing) still exercises the bridge helpers successfully.
- Verify: After the edits/tests, run `rg "dbex\\.nanobrag_bridge.*prepare_refinement_inputs"` and `rg "dbex\\.nanobrag_bridge.*create_"` to confirm no callers rely on the re-exported names. Capture the commands + zero-result evidence under the artifacts directory.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md rg "dbex\\.nanobrag_bridge.*prepare_refinement_inputs" -n`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md rg "dbex\\.nanobrag_bridge.*create_" -n`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_nanobrag_bridge.py --maxfail=1`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_background_semantics.py::TestBackgroundSentinelGuard::test_background_sentinel_guard --maxfail=1`
5. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1`

Pitfalls To Avoid:
- Do not delete bridge-only helpers (HKL/grid/geometry math); only remove the re-export shim while keeping geometry helpers (compute_baseline_misset_deg, quaternion transforms, etc.) in place.
- Keep Environment Freeze in mind—do not edit `nanobrag_torch` or install packages while touching scripts/tests.
- When updating tests, ensure fixtures still point at the same trusted-mask/mapping assets and that deterministic CLI mocks keep returning real `DetectorConfig` objects (per DIAGNOSTICS-001 / CONFIG-001).
- Maintain doc/spec consistency: every reference to `prepare_refinement_inputs` must cite the refinement module, and `/torch_diagnostics` provenance language (PHYSICS-LOSS-001/002/003) must stay intact.
- Ensure new imports stay eager at module scope for production code; any lazy imports should only exist where circular dependencies force them.

If Blocked:
- If any legacy tooling (`plans/active/**/bin/*.py`) genuinely depends on the bridge alias (e.g., third-party consumers outside this repo), halt before deleting the shim, document the path + justification in `plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T041200Z/blockers.md`, and revert the alias removal until a follow-up initiative absorbs those consumers.
- If removing the re-export exposes unforeseen circular imports, capture stack traces under the same artifacts directory and update docs/fix_plan.md Attempts History so we can decide whether to split the module further.

Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` schema must stay untouched while refactoring imports.
- CONFIG-001 — Detector/beam/crystal mapping rules enforced by the config factories must remain intact after moving imports.
- PHYSICS-LOSS-001/002/003 — Variance-weighted loss/telemetry contracts still rely on `RefinementInputs` metadata; do not change the dataclass fields while editing references.

Pointers:
- dbex/nanobrag_bridge.py
- dbex/refinement/inputs.py
- tests/dbex/test_nanobrag_bridge.py
- docs/architecture/dbex/physics/forward.idl.md
- docs/spec-db-conformance.md

Next Up (optional):
- Once no callers rely on the bridge re-export, plan Phase C.7 to trim unused compatibility imports and consider moving HKL/helpers into smaller modules before closing ARCH-BRIDGE-RESP-001.

