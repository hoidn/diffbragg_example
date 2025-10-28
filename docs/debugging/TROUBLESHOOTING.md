# DBEX Troubleshooting Playbook

> Purpose: Capture recurrent error signatures with actionable, copy‑pasteable remedies.
>
> How to use: When you fix a recurring bug, add an entry here. Keep it brief, reference sources with `path:line`, and include the exact command or code snippet that resolves it.

## Template

### Error Signature
- Symptom: <what is observed>
- Root Cause: <underlying cause>
- Solution: <minimal steps to resolve>
- References: <source:path:line>

---

## Entries

### Gradcheck fails when torch.compile is active
- Symptom: `torch.autograd.gradcheck` fails nondeterministically or throws graph/functionalization errors.
- Root Cause: `torch.compile`/Dynamo interferes with gradcheck’s numerical probing.
- Solution: Export `NANOBRAGG_DISABLE_COMPILE=1` for gradient tests; ensure tests parametrize device/dtype separately.
- References: docs/development/testing_strategy.md:1.6; docs/pytorch_runtime_checklist.md:1

### Pixel order mismatch between dxtbx and DBEX tensors
- Symptom: Low correlation and apparent misalignment of model vs data.
- Root Cause: dxtbx reports `(fast, slow)` while DBEX tensors are `[panel, slow, fast]`.
- Solution: Swap order when hydrating configs; assert shapes/order in fixtures before compute.
- References: docs/architecture.md:13

