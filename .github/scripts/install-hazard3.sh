#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build the Hazard3 Verilator testbench for CI.
# Usage: install-hazard3.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-hazard3.sh <install-dir>}"
HAZARD3_REPO="https://github.com/Wren6991/Hazard3.git"
HAZARD3_COMMIT="ba0c83c657a21f2e9946cf02cbc6c8d3d9a7dab6" # develop
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

# 2. Clone Hazard3 at the pinned commit. The testbench Makefile needs the scripts submodule.
git init "$INSTALL_DIR/Hazard3"
(
  cd "$INSTALL_DIR/Hazard3"
  git remote add origin "$HAZARD3_REPO"
  git fetch --depth 1 origin "$HAZARD3_COMMIT"
  git checkout FETCH_HEAD
  git submodule update --init --depth 1 scripts
  # VerilatedVcdC::dump(unsigned long long) is ambiguous where uint64_t is unsigned long.
  sed -i 's/vcd->dump(\(2ull \* cycle[^)]*\))/vcd->dump((uint64_t)(\1))/' test/sim/tb_verilator/tb.cpp
)

# 3. Start from the testbench's default configuration and change only these parameters:
#    - RESET_VECTOR: the testbench loads the image at the base of RAM.
#    - PMP_REGIONS: all 16 regions.
#    - MVENDORID_VAL, MCONFIGPTR_VAL: the defaults are placeholders, and Sail's mconfigptr is
#      always 0.
#    - Zcmp, Zilsd, Zclsd, Zibi: not ratified. Sail does not model the first three, and UDB
#      does not define Zibi.
#    - Xh3irq, Xh3bextm, Xh3pmpm, Xh3power, Xh3sfx: custom. Xh3irq's interrupt controller
#      also changes when mip.MEIP is set.
HDL_DIR="$INSTALL_DIR/Hazard3/test/sim/tb_common/hdl"
CONFIG="$HDL_DIR/config_act.vh"
cp "$HDL_DIR/config_default.vh" "$CONFIG"
set_param() {
  sed -i "s/^\(localparam $1 *= \).*;/\1$2;/" "$CONFIG"
  grep -q "^localparam $1 *= $2;" "$CONFIG"
}
set_param RESET_VECTOR "32'h80000000"
set_param PMP_REGIONS 16
set_param MVENDORID_VAL "32'h00000000"
set_param MCONFIGPTR_VAL "32'h00000000"
for ext in ZCMP ZILSD ZCLSD ZIBI XH3IRQ XH3BEXTM XH3PMPM XH3POWER XH3SFX; do
  set_param "EXTENSION_$ext" 0
done

# 4. Verilate and build. The Makefile's vlib rule forces a precompiled header that makes
#    GCC spend over ten minutes in one cc1plus, so drive the generated Vtb.mk directly.
(
  cd "$INSTALL_DIR/Hazard3/test/sim/tb_verilator"
  make CONFIG=act vcc
  make -j"$(nproc)" -C build-tb-act/obj_dir -f Vtb.mk
  touch build-tb-act/vlib.touch
  make CONFIG=act
)

install -m 0755 "$INSTALL_DIR/Hazard3/test/sim/tb_verilator/tb-act" "$INSTALL_DIR/bin/hazard3-tb"
install -m 0755 "$(dirname "$0")/run-hazard3.sh" "$INSTALL_DIR/bin/run-hazard3.sh"
