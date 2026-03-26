#!/usr/bin/env bash
####################################################################################
#
# RISC-V Architectural Functional Coverage Testbench (VCS)
#
# SPDX-License-Identifier: Apache-2.0
#
####################################################################################

set -euo pipefail

# Input arguments
TRACEFILELIST="${1}"
VDB="${2}"
WKDIR="${3}"
FCOVDIR="${4}"
COVERPOINTDIR="${5}"
CONFIGDIR="${6}"
COVERAGELIST="${7}"

# Clean old coverage database
rm -rf "${WKDIR}" "${VDB}"
mkdir -p "${WKDIR}"

# Setup VCS arguments
COVERPOINTS=(
  "+incdir+${COVERPOINTDIR}"
  "+incdir+${COVERPOINTDIR}/unpriv"
  "+incdir+${COVERPOINTDIR}/priv"
)
INC_DIRS=(
  "+incdir+${CONFIGDIR}"
  "${COVERPOINTS[@]}"
  "+incdir+${FCOVDIR}"
)
COMPILE_FILES=(
  "${FCOVDIR}/rvviTrace.sv"
  "${FCOVDIR}/riscv_arch_test.sv"
  "${FCOVDIR}/testbench.sv"
)

DEFINE_ARGS=()
for def in ${COVERAGELIST}; do
  if [[ -n "${def}" ]]; then
    DEFINE_ARGS+=("+define+${def}")
  fi
done

pushd "${WKDIR}" > /dev/null

# Compile
if ! vlogan -q -full64 -sverilog "${INC_DIRS[@]}" "${DEFINE_ARGS[@]}" "${COMPILE_FILES[@]}" > vlogan.log 2>&1; then
  echo "ERROR collecting coverage. vlogan failed; see ${WKDIR}/vlogan.log" >&2
  exit 1
fi

# Elaborate
if ! vcs -q -full64 -sverilog testbench -o simv > vcs.log 2>&1; then
  echo "ERROR collecting coverage. vcs elaboration failed; see ${WKDIR}/vcs.log" >&2
  exit 1
fi

# Simulate
if ! ./simv -vcs_assert off +traceFileList="${TRACEFILELIST}" > simv.log 2>&1; then
  echo "ERROR collecting coverage. simv run failed; see ${WKDIR}/simv.log" >&2
  exit 1
fi

if [[ -d simv.vdb ]]; then
  mv simv.vdb "${VDB}"
else
  echo "ERROR collecting coverage. simv.vdb not found." >&2
  exit 1
fi

popd > /dev/null
