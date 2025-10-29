# simtbx diffBragg Rebuild Log (2025-10-29T063817Z)

## Status Snapshot — 2025-10-29T00:25Z
- **Environment tag**: `simtbx-patched-diffBraggCUDA708`
- **Source patches**:
  - `diffBraggCUDA.cu`: guard `cudaFree` cleanup with `cp.previous_nsource`
  - `diffuse_util.h`: add `<cassert>` so NVCC recognises `assert`
- **Runtime artifact**: `simtbx_diffBragg_ext.so` rebuilt (size 3.6 MB, md5 `1506a48bee414ffcec041083b1496a44`)
- **Verification**:
  - CPU smoke: `diffBragg_forward(..., device_Id=-1, cuda=False)` ✅
  - GPU smoke: `diffBragg_forward(..., device_Id=0, cuda=True)` ✅
  - Log: `logs/diffBragg_forward_smoke.log`

## Rebuild Commands
Executed from the diffbragg_example root with the `simtbx` Conda environment active.

```bash
# 1) Configure (refreshes build_ext with current sources)
cmake -S /home/ollie/Documents/easyBragg \
      -B /home/ollie/Documents/easyBragg/build_ext \
      -DCMAKE_BUILD_TYPE=Release

# 2) Build fresh copy of the CUDA extension
cmake --build /home/ollie/Documents/easyBragg/build_ext \
      --target simtbx_diffBragg_ext \
      --clean-first -- -j$(nproc)

# 3) Deploy rebuilt .so to both staging and runtime locations
cp /home/ollie/Documents/easyBragg/build_ext/simtbx_diffBragg_ext.so \
   /home/ollie/Documents/easyBragg/ext/simtbx_diffBragg_ext.so
cp /home/ollie/Documents/easyBragg/build_ext/simtbx_diffBragg_ext.so \
   /home/ollie/miniconda3/envs/simtbx/lib/python3.9/site-packages/simtbx_diffBragg_ext.so
```

> Note: The first build attempt failed because `diffuse_util.h` lacked an `#include <cassert>` for NVCC. Adding the header (patch `diffuse_util_assert_include.patch`) resolved the compilation error.

## Artifact Verification
- **Timestamps**: both `ext/` and site-packages copies updated to `2025-10-29 00:21`
- **Hashes**:
  ```
  1506a48bee414ffcec041083b1496a44  easyBragg/ext/simtbx_diffBragg_ext.so
  1506a48bee414ffcec041083b1496a44  miniconda3/envs/simtbx/.../simtbx_diffBragg_ext.so
  ```
- **Python import**: `python -c "import simtbx_diffBragg_ext"` (implicit during smoke test) succeeded

## Tests
```
python plans/.../logs/diffBragg_forward_smoke.log  # captured command output
```
- CPU path (`device_Id=-1`, `cuda=False`) completes without assertions
- GPU path (`device_Id=0`, `cuda=True`) completes without assertions

## Patch Inventory
| Patch | File | Rationale | Artifact |
| --- | --- | --- | --- |
| `diffBraggCUDA_cu_line708_fix.patch` | `simtbx/diffBragg/src/diffBraggCUDA.cu` | Prevent double `cudaFree` on unallocated `cp.cu_sourceI_*` buffers | `.../diffBraggCUDA_cu_line708_fix.patch` |
| `diffuse_util_assert_include.patch` | `simtbx/diffBragg/src/diffuse_util.h` | Provide `<cassert>` so NVCC sees `assert` | `.../diffuse_util_assert_include.patch` |

## Follow-up
- `docs/findings.md` updated (DIFFBRAGG-001 → Resolved)
- Environment tag recorded in `environment_tag.txt`
- Smoke test log stored for parity harness ingestion
