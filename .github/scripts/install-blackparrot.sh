#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build the BlackParrot bp_tethered testbench (Verilator) for CI.
# Usage: install-blackparrot.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="${1:?Usage: install-blackparrot.sh <install-dir>}"
BP_REPO="https://github.com/black-parrot/black-parrot.git"
BP_COMMIT="909619a68f3541a4cd0973767daf2a561d1f8c95" # master, 2026-11-10
VERILATOR_VERSION="v5.052"
# The default unicore configuration: bp_unicore_cfg_p = bp_default_cfg_p
BP_CFG="e_bp_unicore_cfg"

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

# 2. black-parrot at the pinned commit with the two submodules the RTL needs (basejump_stl and
#    HardFloat). The bedrock submodule holds the coherence-engine microcode, which the unicore's
#    UCE does not use.
git init "$INSTALL_DIR/black-parrot"
(
  cd "$INSTALL_DIR/black-parrot"
  git remote add origin "$BP_REPO"
  git fetch --depth 1 origin "$BP_COMMIT"
  git checkout FETCH_HEAD
  git submodule update --init --depth 1 external/basejump_stl external/HardFloat
  # Makefile.common includes bsg_cadenv/cadenv.mk, a BSG-internal tool environment; an empty
  # one makes the tools default to those on PATH.
  mkdir -p bsg_cadenv
  touch bsg_cadenv/cadenv.mk
)

# 3. Build the testbench. No waveform tracing (TRACE=0) and no commit log; the watchdog and the
#    performance monitor keep their defaults except that the cycle and instruction limits are
#    raised for the longest tests.
make -C "$INSTALL_DIR/black-parrot/bp_top/verilator" build.verilator \
  CFG="$BP_CFG" VERILATOR="$INSTALL_DIR/bin/verilator" VERILATOR_THREADS="$(nproc)" \
  MAX_CYCLE_P=200000000 MAX_INSTR_P=200000000
SIM="$INSTALL_DIR/black-parrot/bp_top/verilator/results/bp_tethered.$BP_CFG/simsc"
[ -x "$SIM" ] || {
  echo "install-blackparrot.sh: build did not produce $SIM" >&2
  exit 1
}
ln -sf "$SIM" "$INSTALL_DIR/bin/blackparrot-simsc"

# 4. Install the per-test runner
install -m 0755 "$SCRIPT_DIR/run-blackparrot.sh" "$INSTALL_DIR/bin/run-blackparrot.sh"
