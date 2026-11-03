#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build the NEORV32 Verilator testbench for CI.
# Usage: install-neorv32.sh <install-dir>
# Needs GNAT (to build GHDL) and the Verilator build dependencies; see ci.yaml.
# CI hashes this installer and the harness/runner files listed in neorv32/ci.yaml.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-neorv32.sh <install-dir>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NEORV32_REPO="https://github.com/stnolting/neorv32.git"
NEORV32_TAG="v1.13.7"
NEORV32_COMMIT="b1f307244928161a3fca1a010af11d5a736b5339"
GHDL_VERSION="v6.0.0"
VERILATOR_VERSION="v5.052"

mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
export PATH="$INSTALL_DIR/bin:$PATH"

# 1. GHDL, mcode backend, from source. It converts the VHDL processor to Verilog.
git clone --depth 1 --branch "$GHDL_VERSION" https://github.com/ghdl/ghdl.git "$INSTALL_DIR/ghdl-src"
(
  cd "$INSTALL_DIR/ghdl-src"
  mkdir build
  cd build
  ../configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"
  make install
)
rm -rf "$INSTALL_DIR/ghdl-src"

# 2. Verilator from source.
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"

# 3. NEORV32 at the pinned release.
git clone --depth 1 --branch "$NEORV32_TAG" "$NEORV32_REPO" "$INSTALL_DIR/neorv32"
if [ "$(git -C "$INSTALL_DIR/neorv32" rev-parse HEAD)" != "$NEORV32_COMMIT" ]; then
  echo "install-neorv32.sh: $NEORV32_TAG is not $NEORV32_COMMIT" >&2
  exit 1
fi

# 4. Convert the processor, configured by neorv32-act-top.vhd, to one Verilog module, as
#    NEORV32's own rtl/verilog flow does.
BUILD="$INSTALL_DIR/build"
mkdir -p "$BUILD"
cp "$SCRIPT_DIR/neorv32-act-top.vhd" "$SCRIPT_DIR/neorv32-act-tb.sv" "$BUILD/"
(
  cd "$BUILD"
  ghdl -i --std=08 --work=neorv32 --workdir=. "$INSTALL_DIR"/neorv32/rtl/core/*.vhd neorv32-act-top.vhd
  ghdl -m --std=08 --work=neorv32 --workdir=. neorv32_act_top
  ghdl synth --std=08 --work=neorv32 --workdir=. --out=verilog neorv32_act_top >neorv32_act_top.v
)

# 5. Verilate the testbench around it.
(
  cd "$BUILD"
  verilator --binary -O3 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style \
    -j "$(nproc)" --top-module neorv32_act_tb --Mdir obj_dir neorv32-act-tb.sv neorv32_act_top.v
)

install -m 0755 "$BUILD/obj_dir/Vneorv32_act_tb" "$INSTALL_DIR/bin/neorv32-tb"
install -m 0755 "$SCRIPT_DIR/run-neorv32.sh" "$INSTALL_DIR/bin/run-neorv32.sh"
