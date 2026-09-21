#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the lowRISC Ibex "Simple System" testbench (Verilator) for CI.
# Usage: install-ibex.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-ibex.sh <install-dir>}"
IBEX_REPO="https://github.com/lowRISC/ibex.git"
IBEX_COMMIT="e9f55342edbd27e9e17a0e41b1c95a81abb5eac8"
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

# 2. Clone Ibex at the pinned commit
git init "$INSTALL_DIR/ibex"
(
  cd "$INSTALL_DIR/ibex"
  git remote add origin "$IBEX_REPO"
  git fetch --depth 1 origin "$IBEX_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Ibex's build flow is FuseSoC driven and needs its Python dependencies
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/ibex/python-requirements.txt"
export PATH="$INSTALL_DIR/venv/bin:$PATH"

# 4. Verilate the "opentitan" configuration - the largest one lowRISC runs nightly
#    regressions against - with BaseIsa forced to plain RV32I.
#
#    Two details matter here:
#      * examples/simple_system/ibex_simple_system.core does NOT declare a BaseIsa
#        parameter at this commit (every other .core file does), so the --BaseIsa
#        option ibex_config.py emits has to be stripped or FuseSoC errors out.
#        BaseIsa is instead selected through the BASE_ISA define the wrapper honours:
#          `ifndef BASE_ISA
#            `define BASE_ISA ibex_pkg::BaseIsaRV32IorCHERIoT
#      * cheriot_enable_i is tied to IbexMuBiOff in Simple System, so the core runs as
#        RV32I either way; forcing BaseIsaRV32I removes the CHERIoT logic entirely and
#        makes the configuration match what the UDB config claims.
mkdir -p "$INSTALL_DIR/ot-rv32i"
(
  cd "$INSTALL_DIR/ibex"
  opts="$(./util/ibex_config.py opentitan fusesoc_opts | sed 's/--BaseIsa=[^ ]*//')"
  # shellcheck disable=SC2086 # $opts is a list of FuseSoC flags that must word-split
  fusesoc --cores-root=. run --target=sim --setup --build \
    --build-root="$INSTALL_DIR/ot-rv32i" lowrisc:ibex:ibex_simple_system \
    $opts --verilator_options="-DBASE_ISA=ibex_pkg::BaseIsaRV32I"
)

# 5. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-ibex.sh" "$INSTALL_DIR/bin/run-ibex.sh"
