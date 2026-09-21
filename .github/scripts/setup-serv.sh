#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Setup environment for SERV after install / cache restore
# Usage: setup-serv.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-serv.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "SERV_SNAPSHOT=$INSTALL_DIR/act" >>"$GITHUB_ENV"
