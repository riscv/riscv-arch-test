#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install the VeeR EH2 testbench (Verilator) for CI.
# Usage: install-veer-eh2.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-veer-eh2.sh <install-dir>}"
VEER_EH2_REPO="https://github.com/chipsalliance/Cores-VeeR-EH2.git"
VEER_EH2_COMMIT="bd52450b144db1c2bb441e53b442c2af5a8e7b59"
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

# 2. Clone VeeR EH2 at the pinned commit
git init "$INSTALL_DIR/Cores-VeeR-EH2"
(
  cd "$INSTALL_DIR/Cores-VeeR-EH2"
  git remote add origin "$VEER_EH2_REPO"
  git fetch --depth 1 origin "$VEER_EH2_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Verilate at the maximum ratified feature set: atomics on, bit-manipulation off (VeeR's Zb*
#    is the 0.94 draft, not ratified B), and a single hart since ACT is single-hart.
mkdir -p "$INSTALL_DIR/eh2"
(
  cd "$INSTALL_DIR/eh2"
  RV_ROOT="$INSTALL_DIR/Cores-VeeR-EH2" \
    make -f "$INSTALL_DIR/Cores-VeeR-EH2/tools/Makefile" verilator-build -j"$(nproc)" \
    CONF_PARAMS='-set atomic_enable=1 -set num_threads=1 -set bitmanip_zba=0 -set bitmanip_zbb=0 -set bitmanip_zbc=0 -set bitmanip_zbs=0 -set bitmanip_zbkb=0 -set bitmanip_zbkx=0'
)

# 4. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-veer-eh2.sh" "$INSTALL_DIR/bin/run-veer-eh2.sh"
