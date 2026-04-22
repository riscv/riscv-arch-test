#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Install CVW (CORE-V Wally) and Verilator for CI
# Usage: install-cvw.sh <install-dir>
# Update commits/versions to rebuild (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cvw.sh <install-dir>}"
CVW_COMMIT="fa19687ea37314d7eb08bcb720a68e6fb79711c6"
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
