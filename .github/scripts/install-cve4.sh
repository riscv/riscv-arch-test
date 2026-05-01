#!/usr/nin/env bash
# SPDX-License-Identifier: Apache-2.0
# Install cv32e40p-dv testbench (Verilator) for CI                                                                                                          
# Usage: install-cve4.sh <install-dir>
# Cache key derives from sha256(this file)[:12]; bump versions/commits below to invalidate. 

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cve4.sh <install-dir>}"
CVE4_DV_REPO="https://github.com/karabambus/cv32e40p-dv-review.git"
CVE4_DV_BRANCH="feat/run-cve4-multi-config"                                                                                                                   
CVE4_DV_COMMIT="a1c4ec501e82f23987d1d74625b70a6cd1dfc2e1"                                                                                                   
VERILATOR_VERSION="v5.042"   

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source 
git clone https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(                                                                                                                                                           
  cd "$INSTALL_DIR/verilator-src"
  git checkout "$VERILATOR_VERSION"                                                                                                                         
  autoconf                                                                                                                                                  
  ./configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"                                                                                                                                         
  make install  
)                                                                                                                                                           
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. Clone the cv32e40p-dv testbench (ACT4 CI branch)
git clone --branch "$CVE4_DV_BRANCH" "$CVE4_DV_REPO" "$INSTALL_DIR/cv32e40p-dv"
(                                                                                                                                                           
  cd "$INSTALL_DIR/cv32e40p-dv"
  git checkout "$CVE4_DV_COMMIT"                                                                                                                         
)

# 3. Build the Verilator binary for rv32imcf (only one in CI matrix for now).                                                                               
make -C "$INSTALL_DIR/cv32e40p-dv/sim/core" \                                                                                                               
    verilate \
    CV_CORE_CONFIG=rv32imcf \                                                                                                                              
    TEST=certification_rv32imcf \
    -j"$(nproc)" 

# 4. Drop the per-test warapper into $INSTALL_DIR/bin for easy invocation from CI
install -m 0755 "$INSTALL_DIR/cv32e40p-dv/.github/scripts/run-cve4.sh" \ 
                "$INSTALL_DIR/bin/run-cve4.sh"


