#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install the VeeR EH1 testbench (Verilator) for CI.
# Usage: install-veer-eh1.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-veer-eh1.sh <install-dir>}"
VEER_EH1_REPO="https://github.com/chipsalliance/Cores-VeeR-EH1.git"
VEER_EH1_COMMIT="d04b1c7ae675a63dc4307cacfd10547ec937b928"
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

# 2. Clone VeeR EH1 at the pinned commit
git init "$INSTALL_DIR/Cores-VeeR-EH1"
(
  cd "$INSTALL_DIR/Cores-VeeR-EH1"
  git remote add origin "$VEER_EH1_REPO"
  git fetch --depth 1 origin "$VEER_EH1_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Verilate the default configuration
mkdir -p "$INSTALL_DIR/eh1"
(
  cd "$INSTALL_DIR/eh1"
  RV_ROOT="$INSTALL_DIR/Cores-VeeR-EH1" \
    make -f "$INSTALL_DIR/Cores-VeeR-EH1/tools/Makefile" verilator-build -j"$(nproc)"
)

# 4. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-veer-eh1.sh" "$INSTALL_DIR/bin/run-veer-eh1.sh"
