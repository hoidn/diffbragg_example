Summary: Prepare Stage A LBFGS nucleus handoff so nanobrag torch refinement can descend and record telemetry.
Mode: TDD
Focus: TORCH-REFINE-001 — Implement LBFGS refinement nucleus (Stage A)
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_loss_decreases
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T002425Z/
Do Now:
- TORCH-REFINE-001: Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — add Stage A LBFGS nucleus optimizing global scale + one crystal DoF with deterministic ROI sampling and telemetry capture; Implement: dbex/refine_one.py::run_nanobrag_backend — invoke the nucleus, plumb optimizer telemetry into `_write_torch_outputs`, and keep existing SCALE-003/006 guards intact; Implement: tests/dbex/test_torch_refine_smoke.py::test_loss_decreases — deterministic ROI smoke verifying ≥5% loss drop, telemetry keys, and non-increasing full-loss trace. Validate: env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_loss_decreases; env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1; env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1. Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T002425Z/.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export TORCH_REFINE_ARTIFACTS=plans/active/TORCH-REFINE-001/reports/2025-11-05T002425Z
3. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_loss_decreases | tee "$TORCH_REFINE_ARTIFACTS/collect_refine_smoke.log"
4. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1 --durations=1 | tee "$TORCH_REFINE_ARTIFACTS/pytest_refine_smoke.log"
5. env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1 --durations=1 | tee "$TORCH_REFINE_ARTIFACTS/pytest_cli_diag.log"
6. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o tmp/torch_refine_stage_a.h5 -m 747_mask.pkl -z scaled.mtz --mtzCol F,SIGF | tee "$TORCH_REFINE_ARTIFACTS/refine_cli.log"
7. python - <<'PY' > "$TORCH_REFINE_ARTIFACTS/telemetry_snapshot.json"
import json, h5py
from pathlib import Path
h5_path = Path("tmp/torch_refine_stage_a.h5")
if not h5_path.exists():
    raise SystemExit(f"missing {h5_path}; rerun refine_one before dumping telemetry")
with h5py.File(h5_path, "r") as h:
    diag = h["torch_diagnostics"]
    payload = {"attrs": {k: diag.attrs[k] for k in diag.attrs}}
    for name in diag.keys():
        payload[name] = diag[name][() if diag[name].shape == () else ...].tolist()
print(json.dumps(payload, indent=2))
PY
8. cp tmp/torch_refine_stage_a.h5 "$TORCH_REFINE_ARTIFACTS/torch_refine_stage_a.h5"
Pitfalls To Avoid:
- Keep LBFGS parameters (`log_scale`, crystal perturbation) as torch tensors on the same device; never convert to numpy mid-loop.
- Reuse warmed Simulator objects per panel to avoid torch.compile recompiles and respect Environment Freeze (no cache clears via reinstall).
- Maintain deterministic ROI sampling order so smoke test assertions remain stable; seed any randomness explicitly.
- Flush or invalidate Crystal geometry caches when mutating cell parameters so gradients reflect updated state.
- Preserve SCALE-003/006/007 telemetry: do not drop refined MTZ provenance or calibration when threading new telemetry payloads.
- Ensure `_write_torch_outputs` continues to coerce ROI scores to floats (TORCH-CLI-004) while adding new datasets.
- Skip or xfail gracefully if `refGeom.refl` is absent—document in test to protect CI.
- Keep torch tensors in float32 for runtime but support float64 in tests when `torch.set_default_dtype` flips for gradcheck.
If Blocked: Capture failing LBFGS traces (loss_sample/full per iteration) plus stack trace into `$TORCH_REFINE_ARTIFACTS/blocked.md`, update docs/fix_plan.md Attempts History with the blocker summary, append the same to galph_memory (state=blocked), and flag whether dependency (e.g., nanobrag_torch gradients) needs upstream work before reattempt.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` must remain authoritative; extend rather than replace existing attrs.
- SCALE-003 — Continue preferring refined structure factors and surface provenance in telemetry/HDF5.
- SCALE-006 — Thread DiffBragg calibration metadata through the refinement loop without regressions.
- TESTING-002 — Keep CLI coverage via mocks deterministic; extend assertions when adding telemetry keys.
Pointers:
- plans/nanobrag_integration_plan.md:150 — LBFGS closure + telemetry requirements for the refinement nucleus.
- docs/spec-db-workflow.md:24 — Stage A staging/optimizer mandates (LBFGS, ROI policy).
- docs/nanobrag_api.md:1 — Crystal/Simulator API surfaces for parameter updates.
- dbex/refine_one.py:200 — Current nanobrag backend flow and `_write_torch_outputs` telemetry plumbing.
- tests/dbex/test_nanobrag_smoke.py:1 — Canonical fixtures for refGeom dataset ingestion and ROI handling.
- docs/TESTING_GUIDE.md:60 — Selector table to extend with the new refinement smoke test.
Next Up (optional): Stage B checklist stub once Stage A nucleus lands (telemetry for full loss trace).
Doc Sync Plan: After code passes, append the new smoke selector (name, env flags, artifact logs) to `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md`, referencing `$TORCH_REFINE_ARTIFACTS/collect_refine_smoke.log`; regenerate artifact listings if telemetry datasets change.
