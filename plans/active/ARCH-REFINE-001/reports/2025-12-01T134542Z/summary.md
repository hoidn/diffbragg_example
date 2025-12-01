### Turn Summary
Relocated DB-AT-010 forward and loss helpers from `dbex/nanobrag_bridge.py` into `dbex/physics/` module to decouple gradcheck tests from the bridge monolith.
Created `dbex/physics/forward.py` (235 lines) and extended `dbex/physics/loss.py` (+90 lines) with full spec/finding references; replaced bridge definitions with re-export imports (-241 lines, net +108).
All 5 DB-AT-010 gradcheck tests passed in 95s (crystal_cell_a, crystal_cell_gamma, detector_distance, wavelength).
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/ (collect_db_at_010.log, pytest_db_at_010.log, db_at_010/ subdirectory)
