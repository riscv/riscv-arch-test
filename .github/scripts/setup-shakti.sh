#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Set up the environment for the Shakti cores after install / cache restore
# Usage: setup-shakti.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-shakti.sh <install-dir>}"

# run-shakti.sh finds shakti-eclass-sim and shakti-cclass-sim beside itself.
echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
