### Turn Summary
Implemented mask tensor coercion fixing the AttributeError so nanobrag_torch.Detector initializes successfully in the Stage A LBFGS refinement path.
Forward pass now works correctly (6 successful simulator runs, finite loss values), but backward pass encounters NaN/Inf gradients—a separate issue requiring gradient debugging.
Committed working mask coercion changes; next step is to spawn TORCH-REFINE-001b investigating autograd support or loss formulation numerical stability.
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T014500Z/ (collect_refine_smoke.log, pytest_refine_smoke.log, blocked.md)
