# diffBragg Forward Crash – Patch & Rebuild Record

**Date**: 2025-10-29  
**Loop**: NANOBRAG-GOLDEN-001 / 2025-10-29T063817Z  
**Finding**: DIFFBRAGG-001 (Resolved)  
**Policy**: POLICY-001 (Environment Freeze bugfix exception)

---

## 1. Problem Statement
- `diffBragg_forward` crashed on both CPU (`device_Id=-1`) and GPU (`device_Id=0`) with `GPUassert: invalid argument diffBraggCUDA.cu:708`.
- Root cause: `gpu_free_all()` unconditionally freed `cp.cu_sourceI_scale/grad`; double free or free-before-alloc corrupted CUDA cleanup.

## 2. Patches Applied
| Patch | File | Purpose | Artifact |
| --- | --- | --- | --- |
| `diffBraggCUDA_cu_line708_fix.patch` | `simtbx/diffBragg/src/diffBraggCUDA.cu` | Guard `cudaFree` calls with `cp.previous_nsource` and reset flag to prevent double freeing | `.../diffBraggCUDA_cu_line708_fix.patch` |
| `diffuse_util_assert_include.patch` | `simtbx/diffBragg/src/diffuse_util.h` | Add `<cassert>` so NVCC recognises `assert` during rebuild | `.../diffuse_util_assert_include.patch` |

Both patches live under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/`.

## 3. Rebuild Procedure
Executed with the `simtbx` Conda environment active.

```bash
# Refresh CMake cache
cmake -S /home/ollie/Documents/easyBragg \
      -B /home/ollie/Documents/easyBragg/build_ext \
      -DCMAKE_BUILD_TYPE=Release

# Rebuild CUDA/C++ extension (clean to force new objects)
cmake --build /home/ollie/Documents/easyBragg/build_ext \
      --target simtbx_diffBragg_ext \
      --clean-first -- -j$(nproc)

# Deploy rebuilt shared library
cp /home/ollie/Documents/easyBragg/build_ext/simtbx_diffBragg_ext.so \
   /home/ollie/Documents/easyBragg/ext/simtbx_diffBragg_ext.so
cp /home/ollie/Documents/easyBragg/build_ext/simtbx_diffBragg_ext.so \
   /home/ollie/miniconda3/envs/simtbx/lib/python3.9/site-packages/simtbx_diffBragg_ext.so
```

Build notes:
- Initial attempt failed (`identifier "assert" is undefined`) until `<cassert>` was added to `diffuse_util.h`.
- Final artifact hash: `1506a48bee414ffcec041083b1496a44`.

## 4. Verification
```bash
python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/logs/diffBragg_forward_smoke.log
```
The captured script runs `diffBragg_forward` twice:
- CPU path (`device_Id=-1`, `cuda=False`)
- GPU path (`device_Id=0`, `cuda=True`)

Both complete without assertions. Importing `simtbx_diffBragg_ext` succeeds implicitly during the run.

## 5. Environment Tag
`environment_tag.txt` records the state tag: `simtbx-patched-diffBraggCUDA708`, timestamp, and artifact hash.

## 6. Follow-up Actions
- `docs/findings.md` updated (DIFFBRAGG-001 → Resolved; references new patches and logs).
- `rebuild_status.md` and `patch_progress.md` capture the command log and verification checklist.
- Proceed with canonical capture tasks; the runtime now includes patched cleanup.

## 7. Rollback
To revert if needed:
```bash
cd /home/ollie/Documents/easyBragg/simtbx_project
patch -R -p1 < .../diffBraggCUDA_cu_line708_fix.patch
patch -R -p1 < .../diffuse_util_assert_include.patch

cmake --build /home/ollie/Documents/easyBragg/build_ext --target simtbx_diffBragg_ext --clean-first -- -j$(nproc)
cp build_ext/simtbx_diffBragg_ext.so ext/simtbx_diffBragg_ext.so
cp build_ext/simtbx_diffBragg_ext.so $CONDA_PREFIX/lib/python3.9/site-packages/simtbx_diffBragg_ext.so
```

Remove or update `environment_tag.txt` accordingly.
