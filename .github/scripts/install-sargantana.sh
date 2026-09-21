#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install the BSC Sargantana core tile testbench (Verilator) for CI.
# Usage: install-sargantana.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-sargantana.sh <install-dir>}"
CORE_TILE_REPO="https://github.com/bsc-loca/core_tile.git"
# core_tile v3.1.0; rtl/core/sargantana is pinned by the superproject to
# bsc-loca/sargantana 403975c8a3c64c8eb369021a1ac2a374e5df441b (v3.0-47-g403975c).
CORE_TILE_COMMIT="2528e7df6507fa06d372f001e55cfd46efae4a4b"
# README: "| Verilator | 5.004 |" is the documented minimum.
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

# 2. Clone core_tile at the pinned commit. Only the submodules the Verilator
#    simulator needs are fetched; riscv-tests and riscv-torture are vendor test
#    suites that ACT does not use, and the fpga/ submodules are unused here.
git init "$INSTALL_DIR/core_tile"
(
  cd "$INSTALL_DIR/core_tile"
  git remote add origin "$CORE_TILE_REPO"
  git fetch --depth 1 origin "$CORE_TILE_COMMIT"
  git checkout FETCH_HEAD
  git submodule update --init --depth 1 \
    rtl/common_cells rtl/icache rtl/dcache rtl/core/sargantana \
    simulator/bsc-dm simulator/reference/riscv-isa-sim
)

# 3. Build the bootrom, the Spike disassembler helper library and the Verilator
#    model. The design is taken at its default drac_pkg::DracDefaultConfig; no
#    build-time knobs are set, so what is verified is the core as shipped.
(
  cd "$INSTALL_DIR/core_tile"
  make -j"$(nproc)" sim
)

# 4. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-sargantana.sh" "$INSTALL_DIR/bin/run-sargantana.sh"
