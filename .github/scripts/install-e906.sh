#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build a verilated XuanTie OpenE906 smart_run SoC testbench for CI.
# Usage: install-e906.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-e906.sh <install-dir>}"
E906_REPO="https://github.com/T-head-Semi/opene906.git"
E906_COMMIT="c5b878958e73e0b8f324a8132943f184a7831c07"
VERILATOR_VERSION="v5.052"
JOBS="${JOBS:-$(nproc)}"

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$JOBS"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. Clone OpenE906 at the pinned commit
git init "$INSTALL_DIR/opene906"
(
  cd "$INSTALL_DIR/opene906"
  git remote add origin "$E906_REPO"
  git fetch --depth 1 origin "$E906_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Apply the testbench patch ACT needs (see setup-e906.sh for what and why)
"$(dirname "$0")/setup-e906.sh" "$INSTALL_DIR" --patch-only

# 4. Verilate.
#
#    The vendor smart_run/Makefile supports only iverilog, VCS and irun, so the verilate
#    step is spelled out here.  The testbench uses delays, wait and force, so it needs
#    --timing.  sim.fl names the RTL through ${CODE_BASE_PATH} and the testbench
#    relative to smart_run/work.
#
#    NO_MONITOR drops mnt.v, which writes every retired instruction and the whole register
#    file to a log.  MAX_RUN_TIME caps a runaway test at 20 M cycles (10 ns each).
mkdir -p "$INSTALL_DIR/opene906/smart_run/work"
(
  cd "$INSTALL_DIR/opene906/smart_run/work"
  export CODE_BASE_PATH="$INSTALL_DIR/opene906/E906_RTL_FACTORY"
  verilator --timing --binary -j "$JOBS" -Wno-fatal -Wno-lint -Wno-style --top-module tb \
    -f ../logical/filelists/sim.fl \
    +define+NO_DUMP +define+NO_MONITOR +define+MAX_RUN_TIME=200000000 -o Vtb
)

# 5. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-e906.sh" "$INSTALL_DIR/bin/run-e906.sh"
