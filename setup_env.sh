#!/bin/bash
# diffBragg Example Environment Setup Script
# Source this file to activate the simtbx environment and get helper functions
#
# Usage:
#   source setup_env.sh
#   OR
#   . setup_env.sh

# Determine the script's directory (works with both source and execution)
if [[ -n "${BASH_SOURCE[0]}" ]]; then
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
else
    SCRIPT_DIR="$PWD"
fi

# Color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if script is being sourced (not executed)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo -e "${RED}Error: This script must be sourced, not executed.${NC}"
    echo "Usage: source setup_env.sh"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  diffBragg Example Environment Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Detect simtbx installation location
SIMFORGE_DIR="${SCRIPT_DIR}/simforge"
SIMTBX_ENV="${SIMFORGE_DIR}/envs/simtbx"

if [[ ! -d "$SIMFORGE_DIR" ]]; then
    echo -e "${YELLOW}Warning: simforge not found at ${SIMFORGE_DIR}${NC}"
    echo -e "${YELLOW}Have you run Step 1 of the setup?${NC}"
    echo ""
    echo "To install, run:"
    echo "  cd ${SCRIPT_DIR}"
    echo "  # Follow Step 1 instructions in README.md"
    return 1
fi

if [[ ! -d "$SIMTBX_ENV" ]]; then
    echo -e "${RED}Error: simtbx environment not found at ${SIMTBX_ENV}${NC}"
    echo "Expected: ${SIMTBX_ENV}"
    return 1
fi

# Save original PATH and CONDA_PREFIX if not already saved
if [[ -z "$DBEX_ORIGINAL_PATH" ]]; then
    export DBEX_ORIGINAL_PATH="$PATH"
    export DBEX_ORIGINAL_CONDA_PREFIX="$CONDA_PREFIX"
fi

# Set environment variables
export PATH="${SIMTBX_ENV}/bin:${DBEX_ORIGINAL_PATH}"
export CONDA_PREFIX="${SIMTBX_ENV}"
export DBEX_ROOT="${SCRIPT_DIR}"
export DBEX_SIMTBX_ENV="${SIMTBX_ENV}"

echo -e "${GREEN}✓ simtbx environment activated${NC}"
echo "  Location: ${SIMTBX_ENV}"
echo "  Python: $(which python)"
echo ""

# Helper function: Activate environment
dbex_activate() {
    export PATH="${SIMTBX_ENV}/bin:${DBEX_ORIGINAL_PATH}"
    export CONDA_PREFIX="${SIMTBX_ENV}"
    echo -e "${GREEN}✓ simtbx environment activated${NC}"
}

# Helper function: Deactivate environment
dbex_deactivate() {
    if [[ -n "$DBEX_ORIGINAL_PATH" ]]; then
        export PATH="$DBEX_ORIGINAL_PATH"
        export CONDA_PREFIX="$DBEX_ORIGINAL_CONDA_PREFIX"
        echo -e "${GREEN}✓ Environment deactivated${NC}"
    else
        echo -e "${YELLOW}Warning: Original PATH not saved${NC}"
    fi
}

# Helper function: Check environment status
dbex_status() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  diffBragg Environment Status${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    # Check Python
    if command -v python &> /dev/null; then
        echo -e "${GREEN}✓ Python:${NC} $(python --version) at $(which python)"
    else
        echo -e "${RED}✗ Python not found${NC}"
    fi

    # Check key Python packages
    echo ""
    echo "Python Packages:"

    if python -c "from simtbx.nanoBragg import nanoBragg" 2>/dev/null; then
        echo -e "  ${GREEN}✓ simtbx${NC}"
    else
        echo -e "  ${RED}✗ simtbx${NC}"
    fi

    if python -c "import dials" 2>/dev/null; then
        echo -e "  ${GREEN}✓ dials${NC}"
    else
        echo -e "  ${RED}✗ dials${NC}"
    fi

    if python -c "import xfel" 2>/dev/null; then
        echo -e "  ${GREEN}✓ xfel${NC}"
    else
        echo -e "  ${YELLOW}⚠ xfel (optional)${NC}"
    fi

    # Note: score_trainer may crash on import on some platforms (macOS)
    # Check if the module exists but don't import it
    if python -c "import sys; import importlib.util; sys.exit(0 if importlib.util.find_spec('score_trainer') else 1)" 2>/dev/null; then
        echo -e "  ${GREEN}✓ score_trainer${NC} (installed, may require GPU for some features)"
    else
        echo -e "  ${YELLOW}⚠ score_trainer (optional)${NC}"
    fi

    if python -c "import dbex" 2>/dev/null; then
        echo -e "  ${GREEN}✓ dbex${NC}"
    else
        echo -e "  ${YELLOW}⚠ dbex (run 'pip install -e .' from repo root)${NC}"
    fi

    # Check commands
    echo ""
    echo "Commands:"

    if command -v dials.stills_process &> /dev/null; then
        echo -e "  ${GREEN}✓ dials.stills_process${NC}"
    else
        echo -e "  ${RED}✗ dials.stills_process${NC}"
    fi

    if command -v score.getMod &> /dev/null; then
        echo -e "  ${GREEN}✓ score.getMod${NC}"
    else
        echo -e "  ${YELLOW}⚠ score.getMod (optional)${NC}"
    fi

    # Check GPU/CUDA availability
    echo ""
    echo "GPU Status:"
    if command -v nvidia-smi &> /dev/null; then
        GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | wc -l)
        if [[ $GPU_COUNT -gt 0 ]]; then
            echo -e "  ${GREEN}✓ NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)${NC}"
            nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | xargs -I {} echo -e "    Driver version: {}"
        else
            echo -e "  ${YELLOW}⚠ nvidia-smi found but no GPUs detected${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ No CUDA/GPU detected (CPU-only mode)${NC}"
        echo -e "    ${YELLOW}Note: Step 7 (diffBragg refinement) requires GPU${NC}"
    fi

    # Check easyBragg directory
    echo ""
    echo "Installation Directories:"
    if [[ -d "${DBEX_ROOT}/easyBragg" ]]; then
        echo -e "  ${GREEN}✓ easyBragg${NC} at ${DBEX_ROOT}/easyBragg"
    else
        echo -e "  ${YELLOW}⚠ easyBragg not found${NC} (run Step 1)"
    fi

    if [[ -d "${DBEX_ROOT}/dbex" ]]; then
        echo -e "  ${GREEN}✓ dbex${NC} at ${DBEX_ROOT}/dbex"
    else
        echo -e "  ${RED}✗ dbex not found${NC}"
    fi

    echo ""
}

# Helper function: Run basic tests
dbex_test() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Running Basic Tests${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""

    local FAILED=0

    # Test 1: simtbx import
    echo -n "Test 1: simtbx.nanoBragg import... "
    if python -c "from simtbx.nanoBragg import nanoBragg; N=nanoBragg()" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi

    # Test 2: DIALS import
    echo -n "Test 2: dials import... "
    if python -c "import dials" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi

    # Test 3: dials.stills_process command
    echo -n "Test 3: dials.stills_process command... "
    if command -v dials.stills_process &> /dev/null; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi

    # Test 4: Check for easyBragg extensions
    echo -n "Test 4: easyBragg extensions... "
    if [[ -f "${SIMTBX_ENV}/lib/python3.9/site-packages/simtbx_nanoBragg_ext.so" ]] && \
       [[ -f "${SIMTBX_ENV}/lib/python3.9/site-packages/simtbx_diffBragg_ext.so" ]]; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi

    echo ""
    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}${FAILED} test(s) failed${NC}"
        echo "Run 'dbex_status' for more details"
    fi
    echo ""
}

# Helper function: Show help
dbex_help() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  diffBragg Environment Helper Functions${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Available commands:"
    echo ""
    echo -e "  ${GREEN}dbex_activate${NC}     - Activate the simtbx environment"
    echo -e "  ${GREEN}dbex_deactivate${NC}   - Deactivate the simtbx environment"
    echo -e "  ${GREEN}dbex_status${NC}       - Check environment status and installed packages"
    echo -e "  ${GREEN}dbex_test${NC}         - Run basic verification tests"
    echo -e "  ${GREEN}dbex_help${NC}         - Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  DBEX_ROOT           = ${DBEX_ROOT}"
    echo "  DBEX_SIMTBX_ENV     = ${DBEX_SIMTBX_ENV}"
    echo "  CONDA_PREFIX        = ${CONDA_PREFIX}"
    echo ""
    echo "To deactivate and restore original PATH:"
    echo "  dbex_deactivate"
    echo ""
}

# Show quick status
echo "Available helper functions:"
echo "  dbex_status     - Check installation status"
echo "  dbex_test       - Run verification tests"
echo "  dbex_help       - Show all available functions"
echo ""
echo -e "Run ${GREEN}dbex_status${NC} to verify your installation"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
