# Phase 6 Optimizer Decision — LBFGS vs Adam

## Spec Guidance

**Source:** `docs/spec-db-workflow.md:107`

**Quote:**
> "Stage B MAY use L-BFGS or Adam. Default optimizer SHALL be L-BFGS when parameter count allows efficient limited-memory approximation."

**Interpretation:**
- LBFGS is **spec default** for Stage B
- Adam is **spec-permitted** alternative for large parameter counts
- Implementation MAY choose dynamically based on parameter count

## Trade-Off Analysis

### LBFGS (Limited-Memory Broyden-Fletcher-Goldfarb-Shanno)

#### Advantages
1. **Better Convergence:** Second-order curvature approximation → fewer iterations to reach minimum
2. **No Learning Rate Tuning:** Line search automatically adapts step size
3. **Spec Default:** Explicitly mentioned as default optimizer in spec:107
4. **Proven for Small-Medium Parameter Counts:** Standard choice for <10K parameters

#### Disadvantages
1. **Limited-Memory Approximation Degrades:** Curvature approximation quality drops with >10K parameters
2. **Full Closure Recomputation:** Every line search iteration requires full forward pass + loss computation
3. **Memory Overhead:** Stores last m iterations of parameters + gradients (typically m=10-20)
4. **Scaling:** O(m × n) memory, O(m × n²) time per iteration (n=parameters)

### Adam (Adaptive Moment Estimation)

#### Advantages
1. **Scales Well to Large Parameter Counts:** Linear O(n) memory/time complexity
2. **Per-Parameter Adaptive Learning Rates:** Handles different parameter scales automatically
3. **Robust to Noisy Gradients:** Moving averages smooth optimization trajectory
4. **No Line Search:** Single gradient evaluation per iteration (cheaper than LBFGS closure calls)

#### Disadvantages
1. **Learning Rate Tuning Required:** Must choose learning rate (1e-3 typical starting point)
2. **Slower Convergence:** First-order method → more iterations than LBFGS for small problems
3. **Not Spec Default:** Requires justification (large parameter count)
4. **Momentum State:** Stores m (1st moment) + v (2nd moment) per parameter → 3× parameter memory

## Parameter Count Gate Analysis

### Gate Threshold: 10,000 ASU Reflections

**Rationale:**
- LBFGS limited-memory approximation quality degrades significantly beyond ~10K parameters
- Industry heuristic: LBFGS preferred for n < 10K, Adam for n ≥ 10K
- Test fixture (P1 space group) has ~35K unique ASU reflections → Adam required

**Implementation:**
```python
def select_stage_b_optimizer(n_asu_unique: int) -> tuple[str, dict]:
    """
    Select optimizer based on ASU parameter count.

    Returns:
        optimizer_name: "LBFGS" or "Adam"
        optimizer_kwargs: Configuration dict for optimizer instantiation
    """
    if n_asu_unique < 10000:
        # Spec default: LBFGS for small-medium parameter counts
        return "LBFGS", {
            "max_iter": 20,
            "history_size": 10,
            "line_search_fn": "strong_wolfe"
        }
    else:
        # Spec-permitted: Adam for large parameter counts
        return "Adam", {
            "lr": 1e-3,  # Default learning rate
            "betas": (0.9, 0.999),
            "eps": 1e-8
        }
```

### Test Fixture Decision

**Space Group:** P1 (No. 1)

**n_asu_unique:** ~35,000

**Decision:** **Adam** (learning rate 1e-3)

**Justification:**
- 35,000 > 10,000 threshold → LBFGS not recommended
- Spec permits Adam for large parameter counts (spec:107)
- Adam scales linearly with parameter count

## Learning Rate Heuristics (Adam)

### Default: 1e-3
**Rationale:** Standard Adam starting point, balances exploration vs stability

**Conditions:**
- Initial Stage B optimization
- No prior knowledge of loss landscape
- Default per PyTorch Adam documentation

### Fallback: 1e-4
**Rationale:** More conservative, for unstable loss landscapes

**Conditions:**
- 1e-3 causes divergence (chi² increases instead of decreasing)
- Modifier oscillations observed in telemetry
- Fallback triggered after 5 iterations without improvement

### Learning Rate Schedule (Optional)
**Strategy:** ReduceLROnPlateau

**Parameters:**
- patience=3 (reduce after 3 iterations without improvement)
- factor=0.5 (halve learning rate)
- min_lr=1e-6 (stop reducing below this)

**Rationale:** Adaptive schedule allows aggressive initial exploration (1e-3) with automatic annealing for fine-tuning

## Recommendation

### Production Implementation

**Dynamic Selection Logic:**
```python
# In Stage B setup
if n_asu_unique < 10000:
    optimizer = torch.optim.LBFGS(
        [log_modifiers],
        max_iter=20,
        history_size=10,
        line_search_fn="strong_wolfe"
    )
    optimizer_name = "LBFGS"
    learning_rate = None  # N/A for LBFGS
else:
    optimizer = torch.optim.Adam(
        [log_modifiers],
        lr=1e-3,
        betas=(0.9, 0.999),
        eps=1e-8
    )
    optimizer_name = "Adam"
    learning_rate = 1e-3

    # Optional: Add learning rate scheduler
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        patience=3,
        factor=0.5,
        min_lr=1e-6
    )
```

### Telemetry

**Stage B Telemetry SHALL include:**
- `optimizer`: "LBFGS" or "Adam"
- `learning_rate`: float or None (for LBFGS)
- `n_asu_unique`: Total unique ASU reflections
- `parameter_count`: n_asu_unique (same value, different semantic)

### Comparison Table

| Criterion | LBFGS (n < 10K) | Adam (n ≥ 10K) |
|-----------|-----------------|----------------|
| Convergence Speed | Fast (fewer iterations) | Slower (more iterations) |
| Memory Overhead | O(m × n) ~10× params | O(3n) = 3× params |
| Time per Iteration | High (line search) | Low (single gradient) |
| Learning Rate Tuning | Not required | Required (1e-3 default) |
| Scaling | Poor (>10K params) | Excellent (linear) |
| Spec Status | Default (spec:107) | Permitted (spec:107) |
| Test Fixture (P1) | ❌ Not recommended (35K params) | ✅ Recommended |

## Summary

**Recommendation:** Implement dynamic optimizer selection based on n_asu_unique threshold (10K gate).

**Test Fixture (P1):** Use Adam with learning rate 1e-3 (35K parameters exceed LBFGS threshold).

**Spec Compliance:** LBFGS remains default for high-symmetry space groups (P432, etc.), Adam used when parameter count requires it.

**Implementation Priority:** Phase 6 implementation (next loop after planning approval).
