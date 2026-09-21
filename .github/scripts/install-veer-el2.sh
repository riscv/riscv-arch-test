#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install the VeeR EL2 testbench (Verilator) for CI.
# Usage: install-veer-el2.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-veer-el2.sh <install-dir>}"
VEER_EL2_REPO="https://github.com/chipsalliance/Cores-VeeR-EL2.git"
VEER_EL2_COMMIT="925f3a34bdadc8f28b12a70cfb73e043b0f5ef3d"
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

# 2. Clone VeeR EL2 at the pinned commit
git init "$INSTALL_DIR/Cores-VeeR-EL2"
(
  cd "$INSTALL_DIR/Cores-VeeR-EL2"
  git remote add origin "$VEER_EL2_REPO"
  git fetch --depth 1 origin "$VEER_EL2_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Verilate at the maximum ratified feature set: user mode and 64 PMP entries on, Smepmp off,
#    and bit-manipulation off because VeeR's Zb* is the 0.94 draft rather than ratified B.
#    fast_interrupt_redirect must be off, or external interrupts vector through the meivt table
#    instead of mtvec and never reach the ACT trap handler.
mkdir -p "$INSTALL_DIR/el2"
(
  cd "$INSTALL_DIR/el2"
  RV_ROOT="$INSTALL_DIR/Cores-VeeR-EL2" \
    make -f "$INSTALL_DIR/Cores-VeeR-EL2/tools/Makefile" verilator-build -j"$(nproc)" \
      CONF_PARAMS='-set build_axi4 -set user_mode=1 -set pmp_entries=64 -set smepmp=0 -set bitmanip_zba=0 -set bitmanip_zbb=0 -set bitmanip_zbc=0 -set bitmanip_zbs=0 -set fast_interrupt_redirect=0'
)

# 4. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-veer-el2.sh" "$INSTALL_DIR/bin/run-veer-el2.sh"
