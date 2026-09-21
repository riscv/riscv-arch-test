#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build a verilated XuanTie OpenC910 SoC testbench for CI.
# Usage: install-c910.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-c910.sh <install-dir>}"
C910_REPO="https://github.com/T-head-Semi/openc910.git"
C910_COMMIT="b91c90914c19f114d35c8f6b73408eb241ed847c"
VERILATOR_VERSION="v5.036"

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. Clone OpenC910 at the pinned commit
git init "$INSTALL_DIR/openc910"
(
  cd "$INSTALL_DIR/openc910"
  git remote add origin "$C910_REPO"
  git fetch --depth 1 origin "$C910_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Apply the three testbench patches ACT needs (see setup-c910.sh for what and why)
"$(dirname "$0")/setup-c910.sh" "$INSTALL_DIR" --patch-only

# 4. Verilate.
#
#    The vendor flow ("make compile SIM=verilator") does not work with Verilator 5:
#      * smart_run/Makefile passes -Os, which Verilator 5 rejects outright.
#      * Without it, twelve errors remain, all `assign #1` / `assign # 0.1` delays in
#        the SoC glue (soc.v, axi_slave128.v, ...).  --no-timing clears all twelve.
#    So the verilate step is spelled out here instead of going through that Makefile.
#
#    --threads 1 on purpose: a 4-thread model runs ~2.3x faster per test but uses four
#    cores to do it, so throughput across a parallel regression is better single
#    threaded (measured 1.05 k vs 1.8 k cycles/s per CPU).
#
#    MAX_RUN_TIME caps a runaway test at 4 M cycles (~19 min).  The vendor default is
#    50.3 M cycles, which at this model's speed is over seven hours.
mkdir -p "$INSTALL_DIR/openc910/smart_run/work"
(
  cd "$INSTALL_DIR/openc910/smart_run/work"
  export CODE_BASE_PATH="$INSTALL_DIR/openc910/C910_RTL_FACTORY"
  verilator --no-timing --threads 1 -x-assign 0 -Wno-fatal -cc --exe --top-module top \
    -f ../logical/filelists/sim_verilator.fl \
    +define+NO_DUMP +define+MAX_RUN_TIME=4000000
  cp ../logical/tb/Makefile_obj .
  make -j"$(nproc)" -C obj_dir -f ../Makefile_obj
)

# 5. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-c910.sh" "$INSTALL_DIR/bin/run-c910.sh"
