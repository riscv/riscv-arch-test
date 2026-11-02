#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build a verilated XuanTie OpenE902 smart_run SoC testbench for CI.
# Usage: install-e902.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-e902.sh <install-dir>}"
E902_REPO="https://github.com/T-head-Semi/opene902.git"
E902_COMMIT="991836411b405ac6a0a8d7668f2f5de6fa2a5b8c"
VERILATOR_VERSION="v5.052"

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

# 2. Clone OpenE902 at the pinned commit
git init "$INSTALL_DIR/opene902"
(
  cd "$INSTALL_DIR/opene902"
  git remote add origin "$E902_REPO"
  git fetch --depth 1 origin "$E902_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Apply the testbench patch ACT needs (see setup-e902.sh for what and why)
"$(dirname "$0")/setup-e902.sh" "$INSTALL_DIR" --patch-only

# 4. Verilate.
#
#    The vendor smart_run/Makefile supports only iverilog, VCS and irun, so the verilate
#    step is spelled out here.  The testbench uses delays, wait and force, so it needs
#    --timing.  The filelists name files relative to smart_run/work.  The RTL filelist
#    ends with a bare directory, ${CODE_BASE_PATH}/gen_rtl, which Verilator would read as
#    a source file, so only its file entries are passed.
#
#    NO_MONITOR drops mnt.v, which writes every retired instruction and the whole register
#    file to GPR.log.  MAX_RUN_TIME caps a runaway test at 20 M cycles (10 ns each).
mkdir -p "$INSTALL_DIR/opene902/smart_run/work"
(
  cd "$INSTALL_DIR/opene902/smart_run/work"
  export CODE_BASE_PATH="$INSTALL_DIR/opene902/E902_RTL_FACTORY"
  sed -n '/gen_rtl\//p' "$CODE_BASE_PATH/gen_rtl/filelists/E902_asic_rtl.fl" >e902_rtl.fl
  verilator --timing --binary -j "$(nproc)" -Wno-fatal -Wno-lint -Wno-style --top-module tb \
    -f e902_rtl.fl -f ../logical/filelists/smart.fl -f ../logical/filelists/tb.fl \
    +define+NO_DUMP +define+NO_MONITOR +define+MAX_RUN_TIME=200000000 -o Vtb
)

# 5. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-e902.sh" "$INSTALL_DIR/bin/run-e902.sh"
