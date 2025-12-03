### Turn Summary
Removed re-export compatibility shim from dbex/nanobrag_bridge.py (Phase C.6 complete), updating 10 test files and 5 tooling scripts to import directly from dbex.refinement.inputs and dbex.refinement.config_factories.
All mapped tests PASSED (test_nanobrag_bridge.py 5/5, test_torch_diagnostics_metadata 2/2, test_DB_AT_022_sentinel_complement 1/1); zero stale imports remain in production code per rg verification.
Next: ARCH-BRIDGE-RESP-001 Phase C complete; initiative ready for archive once downstream initiatives pick up.
Artifacts: plans/active/ARCH-BRIDGE-RESP-001/reports/2025-12-03T041200Z/ (verify_no_prepare_refinement_inputs.txt, verify_no_create_factories.txt)
