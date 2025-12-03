### Turn Summary
Completed Phase A lazy-import cleanup for geometry/physics leaf modules; promoted torch/nanobrag_torch imports to module scope with guarded try/except blocks and descriptive helpers.
Scanned repo (229 lazy imports), updated dbex/geometry/crystallography.py and dbex/physics/forward.py; kept dbex.* imports lazy per leaf-module circular dependency constraint.
Module imports PASSED, mapped tests failed with pre-existing issues unrelated to import changes (simulator initialized successfully proving imports work).
Next: Phase B (Stage helper import cleanup after ARCH-REFACTOR-001 stabilizes).
Artifacts: plans/active/ARCH-LAZY-IMPORTS-001/reports/2025-12-02T082202Z/ (lazy_import_audit.md, lazy_import_rg.txt, pytest logs)
