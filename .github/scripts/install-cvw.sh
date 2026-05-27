#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Install CVW (CORE-V Wally) and Verilator for CI
# Usage: install-cvw.sh <install-dir>
# Update commits/versions to rebuild (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cvw.sh <install-dir>}"
CVW_COMMIT="392f49293d6c9f060c00258c1c4fd8dd36bd2cdc"
VERILATOR_VERSION="v5.036"

# Install Verilator from source
git clone https://github.com/verilator/verilator.git
cd verilator
git checkout "$VERILATOR_VERSION"
autoconf
./configure --prefix="$INSTALL_DIR"
make -j"$(nproc)"
make install
cd ..

# Clone CVW repo
git clone https://github.com/openhwgroup/cvw.git "$INSTALL_DIR/cvw"
cd "$INSTALL_DIR/cvw"
git checkout "$CVW_COMMIT"
git submodule update --init addins/verilog-ethernet

# Prebuild the Verilator simulation model for every CVW config used in CI so
# the compiled wkdir/<cfg>_testbench/Vtestbench uses the existing per-simulator
# cache (cache key = sha256 of this script).
# Command mirrors exactly what `wsim --sim verilator` runs (bin/wsim,
# runVerilator) so the up-to-date check skips recompilation at run time.
export WALLY="$INSTALL_DIR/cvw"
export PATH="$INSTALL_DIR/bin:$PATH"   # Verilator was just `make install`ed here

for WALLYCONF in rv32gc rv32imc rv64gc; do
  echo "Prebuilding Verilator model for $WALLYCONF ..."
  make -j"$(nproc)" -C "$WALLY/sim/verilator" \
    WALLYCONF="$WALLYCONF" \
    TESTBENCH=testbench \
    PARAM_ARGS="" \
    DEFINE_ARGS="" \
    BUILD_HASH=""
  test -x "$WALLY/sim/verilator/wkdir/${WALLYCONF}_testbench/Vtestbench" \
    || { echo "ERROR: Vtestbench not produced for $WALLYCONF"; exit 1; }
  # wsim's up-to-date check is mtime-based; ensure the prebuilt model stays
  # newer than all CVW sources after the GitHub Actions cache is restored so
  # it is reused instead of silently rebuilding.
  touch "$WALLY/sim/verilator/wkdir/${WALLYCONF}_testbench/Vtestbench"
done
