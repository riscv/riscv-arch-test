#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Setup environment for PicoRV32 after install / cache restore
# Usage: setup-picorv32.sh <install-dir>
#
# The testbench.v and testbench.cc patches this DUT needs are applied in
# install-picorv32.sh, not here: they have to happen before Verilator runs, and
# this script also runs on a cache hit, when the model is already built.

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-picorv32.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "PICORV32_SNAPSHOT=$INSTALL_DIR" >>"$GITHUB_ENV"
