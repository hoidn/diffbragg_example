#! /bin/sh
# LIBTBX_DISPATCHER DO NOT EDIT
#
# THIS IS AN AUTOMATICALLY GENERATED FILE.
# DO NOT EDIT! CHANGES WILL BE LOST.
# To customize this auto-generated script create
#
#   dispatcher_include*.sh
#
# files in "/home/ollie/Documents/diffbragg_example_2/diffbragg_example/simforge/envs/simtbx" and run
#
#   libtbx.refresh
#
# to re-generate the dispatchers (libtbx.refresh is a subset
# of the functionality of the libtbx/configure.py command).
#
# See also:
#   "/home/ollie/Documents/diffbragg_example_2/diffbragg_example/simforge/envs/simtbx/dispatcher_include_template.sh"
#

# ----------------------------------------------------------------------------
# The shellrealpath function resolves an absolute physical path of its
# first argument and stores it in a global shell variable RESULT.
# The function returns nonzero for unreadable or invalid symlinks
# and resets the RESULT to an empty string.

shellrealpath() {
    local ORGDIR="$PWD"
    local TARGET="$1"
    RESULT=""
    # This test fails for a symlink loop.  We can do without resolution
    # of symlinks that point to existing unreadable files.
    [ -r "$TARGET" ] || return $?
    # Check if the readlink command exists.
    type readlink >/dev/null || return $?
    while true; do
        cd "$(dirname "$TARGET")"
        TARGET="$(basename "$TARGET")"
        if [ -L "$TARGET" ]; then
            TARGET="$(readlink "$TARGET")"
            continue
        fi
        RESULT="$(pwd -P)/$TARGET"
        break
    done
    cd "$ORGDIR"
}
# ----------------------------------------------------------------------------

LIBTBX_PREFIX="$(shellrealpath "$0" && cd "$(dirname "$RESULT")/.." && pwd)"
export LIBTBX_PREFIX
LIBTBX_PYEXE_BASENAME="python"
export LIBTBX_PYEXE_BASENAME
# Set the CCTBX_CONDA_USE_ENVIRONMENT_VARIABLES environment variable
# if you want python to use the following environment variables.
# Otherwise, this environment takes priority at runtime.
if [ -z "${CCTBX_CONDA_USE_ENVIRONMENT_VARIABLES}" ]; then
  unset PYTHONHOME
  unset PYTHONPATH
  unset LD_LIBRARY_PATH
  unset DYLD_LIBRARY_PATH
  unset DYLD_FALLBACK_LIBRARY_PATH
  export PATH="${LIBTBX_PREFIX}/bin:${PATH}"
fi
LIBTBX_DISPATCHER_NAME="libtbx.sh"
export LIBTBX_DISPATCHER_NAME
# ---------------------------------------------
# lines marked LIBTBX_PRE_DISPATCHER_INCLUDE_SH
# ---------------------------------------------
# ----------------------------------------------
# lines marked LIBTBX_POST_DISPATCHER_INCLUDE_SH
# ----------------------------------------------
LIBTBX_PYEXE="$LIBTBX_PREFIX/bin/$LIBTBX_PYEXE_BASENAME"
export LIBTBX_PYEXE
if [ -n "$LIBTBX__VALGRIND_FLAG__" ]; then
  exec $LIBTBX_VALGRIND "$LIBTBX_PREFIX/lib/python3.9/site-packages/libtbx/command_line/sh.sh" "$@"
elif [ $# -eq 0 ]; then
  exec "$LIBTBX_PREFIX/lib/python3.9/site-packages/libtbx/command_line/sh.sh"
else
  exec "$LIBTBX_PREFIX/lib/python3.9/site-packages/libtbx/command_line/sh.sh" "$@"
fi
