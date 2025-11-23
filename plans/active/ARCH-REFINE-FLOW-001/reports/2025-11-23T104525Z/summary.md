### Turn Summary
Applied Galph's warm cache hypothesis fix (disable warm cache for CPU fallback), confirmed it forces cold path via diagnostic, but test still fails with identical gradient error.
Cold path (fresh simulators) exhibits same "element 0 of tensors does not require grad" bug as warm path, disproving the simulator reuse hypothesis; root cause is likely in-place HKL grid construction (lines 2441-2447).
Next: Test Hypothesis A (rebuild HKL grid with out-of-place operations to preserve gradient graph) or escalate to nanobrag_torch inspection if that fails.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/ (blocker_hypothesis_disproven.md, pytest logs with [CACHE_MODE_DECISION] diagnostics)
