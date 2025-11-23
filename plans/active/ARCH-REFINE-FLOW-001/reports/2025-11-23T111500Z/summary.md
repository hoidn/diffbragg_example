### Turn Summary
Ralph's loop i=217 DISPROVED the warm cache hypothesis — both warm and cold paths exhibit identical gradient failures, proving the root cause lies elsewhere.
Diagnostic evidence (line 157: `shell_modifiers_grad_fn` exists) confirms gradients present on shell modifiers, so the break happens during in-place HKL grid construction (lines 2441-2447) where PyTorch autograd semantics don't propagate `requires_grad` from masked assignment RHS.
Next: Ralph applies out-of-place `torch.where` fix to preserve gradient graph, reverts the disproven warm cache change, and validates with full+small detector tests.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T111500Z/ (root_cause_analysis_v2.md, input.md with 12-step protocol)
