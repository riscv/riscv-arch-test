#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Setup environment for CVW after installation
# Usage: setup-cvw.sh <install-dir>
# Writes to $GITHUB_PATH and $GITHUB_ENV for GitHub Actions

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-cvw.sh <install-dir>}"

echo "$INSTALL_DIR/cvw/bin" >> "$GITHUB_PATH"
echo "WALLY=$INSTALL_DIR/cvw" >> "$GITHUB_ENV"
