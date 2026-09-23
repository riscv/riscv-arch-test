#!/usr/bin/env bash
####################################################################################
#
# RISC-V Architectural Functional Coverage Testbench (Verilator)
#
# Copyright (C) 2026 Harvey Mudd College
#
# SPDX-License-Identifier: Apache-2.0
#
####################################################################################

set -euo pipefail

# Input arguments
TRACEFILELIST="${1}"
COVERAGEDAT="${2}"
WKDIR="${3}"
FCOVDIR="${4}"
COVERPOINTDIR="${5}"
UDBHEADERDIR="${6}"
ENVHEADERDIR="${7}"
COVERAGELIST="${8}"

VERILATOR="${VERILATOR:-verilator}"

# Clean old coverage database
rm -rf "${WKDIR}" "${COVERAGEDAT}"
mkdir -p "${WKDIR}"

COVERPOINTS=(
  "+incdir+${COVERPOINTDIR}"
  "+incdir+${COVERPOINTDIR}/unpriv"
  "+incdir+${COVERPOINTDIR}/priv"
)
INC_DIRS=(
  "+incdir+${UDBHEADERDIR}"
  "+incdir+${ENVHEADERDIR}"
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
  if [[ -n ${def} ]]; then
    DEFINE_ARGS+=("+define+${def}")
  fi
done

pushd "${WKDIR}" >/dev/null

# Compile and build
if ! "${VERILATOR}" --binary --timing --coverage-user -Wno-fatal -Wno-lint --top-module testbench \
  "${INC_DIRS[@]}" "${DEFINE_ARGS[@]}" "${COMPILE_FILES[@]}" --Mdir obj_dir >verilator.log 2>&1; then
  echo "ERROR collecting coverage. verilator failed; see ${WKDIR}/verilator.log" >&2
  exit 1
fi

# Simulate
if ! ./obj_dir/Vtestbench +traceFileList="${TRACEFILELIST}" +verilator+coverage+file+"${COVERAGEDAT}" >sim.log 2>&1; then
  echo "ERROR collecting coverage. Vtestbench run failed; see ${WKDIR}/sim.log" >&2
  exit 1
fi

if [[ ! -f ${COVERAGEDAT} ]]; then
  echo "ERROR collecting coverage. ${COVERAGEDAT} not found." >&2
  exit 1
fi

popd >/dev/null
