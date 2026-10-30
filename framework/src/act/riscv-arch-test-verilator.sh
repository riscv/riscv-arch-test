#!/usr/bin/env bash
####################################################################################
#
# RISC-V Architectural Functional Coverage Testbench (Verilator)
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
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
VERILATOR_BUILD_JOBS="${VERILATOR_BUILD_JOBS:-1}"

# Clean old coverage database
rm -rf "${WKDIR}" "${COVERAGEDAT}"
mkdir -p "${WKDIR}"

# Setup Verilator arguments
INC_DIRS=(
  "+incdir+${UDBHEADERDIR}"
  "+incdir+${ENVHEADERDIR}"
  "+incdir+${COVERPOINTDIR}"
  "+incdir+${COVERPOINTDIR}/unpriv"
  "+incdir+${COVERPOINTDIR}/priv"
  "+incdir+${FCOVDIR}"
)
COMPILE_FILES=(
  "${FCOVDIR}/rvviTrace.sv"
  "${FCOVDIR}/riscv_arch_test.sv"
  "${FCOVDIR}/testbench.sv"
)

DEFINE_ARGS=()
for def in ${COVERAGELIST}; do
  DEFINE_ARGS+=("+define+${def}")
done

pushd "${WKDIR}" >/dev/null

# Compile
if ! verilator --binary --timing --coverage-user --coverage-merge-instances \
  --coverage-max-bins 8192 --top-module testbench -j "${VERILATOR_BUILD_JOBS}" \
  -MAKEFLAGS OPT_FAST=-O1 -MAKEFLAGS OPT_SLOW=-O1 -MAKEFLAGS OPT_GLOBAL=-O1 \
  "${INC_DIRS[@]}" "${DEFINE_ARGS[@]}" "${COMPILE_FILES[@]}" --Mdir obj_dir >verilator.log 2>&1; then
  echo "ERROR collecting coverage. Verilator failed; see ${WKDIR}/verilator.log" >&2
  exit 1
fi

# Simulate
if ! ./obj_dir/Vtestbench +traceFileList="${TRACEFILELIST}" \
  +verilator+coverage+file+"${COVERAGEDAT}" >sim.log 2>&1; then
  echo "ERROR collecting coverage. Vtestbench failed; see ${WKDIR}/sim.log" >&2
  exit 1
fi

if [[ ! -f ${COVERAGEDAT} ]]; then
  echo "ERROR collecting coverage. ${COVERAGEDAT} not found." >&2
  exit 1
fi

popd >/dev/null
