#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the Chipyard Verilator simulator for BOOM (ACTMediumBoomV3Config) for CI.
# Usage: install-boom.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.
#
# Chipyard 1.14.0 with the BOOM and rocket-chip it pins, and one local patch from
# config/cores/boom/patches/ (see config/cores/boom/README.md) that removes a simulation-only
# assertion. The patch checksum is pinned here, so a changed patch also changes the cache key.
#
# Chipyard's own build-setup.sh installs a conda environment and a RISC-V toolchain; neither is
# needed to build a Verilator simulator, so this script installs only what the build uses:
# Verilator, a JDK for sbt, CIRCT firtool, espresso, and Spike's libfesvr/libriscv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:?Usage: install-boom.sh <install-dir>}"
mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
JOBS="${JOBS:-$(nproc)}"

CHIPYARD_REPO="https://github.com/ucb-bar/chipyard.git"
CHIPYARD_COMMIT="0acc1e1de2d3284bcd4d876956932a013ffe1949" # 1.14.0
BOOM_COMMIT="5223e44cfeb26f41380057a2eb4d651197475f69"     # generators/boom at Chipyard 1.14.0
VERILATOR_VERSION="v5.036"
FIRTOOL_VERSION="1.75.0" # conda-reqs/circt.json at the pinned Chipyard commit
JDK_URL="https://api.adoptium.net/v3/binary/version/jdk-17.0.16%2B8/linux/x64/jdk/hotspot/normal/eclipse"
CONFIG="ACTMediumBoomV3Config"

PATCH_DIR="$SCRIPT_DIR/../../config/cores/boom/patches"
# BOOM lsu/dcache.scala: drop the assertion that stops the simulation when 100 SCs in a row fail
# at one address. A failing SC is legal, and the Zalrsc tests retry SCs that must fail (outside
# the reservation set) 100 times.
SC_PATCH="boom-sc-fail-assert.patch"
SC_PATCH_SHA256="61032e1c79d0dde4fa5d5e4270e83980dd42336f74bdacc08a12f025c76ae7b5"

TOOLS="$INSTALL_DIR/tools"
mkdir -p "$TOOLS"

# 1. Verilator
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$TOOLS/verilator-src"
(
  cd "$TOOLS/verilator-src"
  autoconf
  ./configure --prefix="$TOOLS/verilator"
  make -j"$JOBS"
  make install
)
rm -rf "$TOOLS/verilator-src"

# 2. JDK 17 (sbt) and CIRCT firtool
mkdir -p "$TOOLS/jdk"
curl -fsSL "$JDK_URL" | tar -xz -C "$TOOLS/jdk" --strip-components=1
mkdir -p "$TOOLS/firtool"
curl -fsSL "https://github.com/llvm/circt/releases/download/firtool-$FIRTOOL_VERSION/firrtl-bin-linux-x64.tar.gz" |
  tar -xz -C "$TOOLS/firtool" --strip-components=1
export PATH="$TOOLS/verilator/bin:$TOOLS/jdk/bin:$TOOLS/firtool/bin:$TOOLS/espresso/bin:$PATH"

# 3. Chipyard at the pinned commit, with the default submodules (they include BOOM)
git init "$INSTALL_DIR/chipyard"
cd "$INSTALL_DIR/chipyard"
git remote add origin "$CHIPYARD_REPO"
git fetch --depth 1 origin "$CHIPYARD_COMMIT"
git checkout FETCH_HEAD
./scripts/init-submodules-no-riscv-tools.sh
test "$(git -C generators/boom rev-parse HEAD)" = "$BOOM_COMMIT"
(cd "$PATCH_DIR" && printf '%s  %s\n' "$SC_PATCH_SHA256" "$SC_PATCH" | sha256sum -c -)
git -C generators/boom apply "$PATCH_DIR/$SC_PATCH"
git submodule update --init --depth 1 toolchains/riscv-tools/riscv-isa-sim

# 4. espresso. Without it on PATH, Chisel falls back to its QMC minimizer, which can run out of
#    memory on large decoders.
git submodule update --init generators/constellation
git -C generators/constellation submodule update --init espresso
cmake -S generators/constellation/espresso -B "$TOOLS/espresso-build" -DBUILD_DOC=OFF \
  -DCMAKE_INSTALL_PREFIX="$TOOLS/espresso"
cmake --build "$TOOLS/espresso-build" --target install -j"$JOBS"
rm -rf "$TOOLS/espresso-build"

# 5. Spike's libfesvr and libriscv, which the simulator links against ($RISCV/lib)
export RISCV="$TOOLS/riscv"
mkdir -p toolchains/riscv-tools/riscv-isa-sim/build
(
  cd toolchains/riscv-tools/riscv-isa-sim/build
  ../configure --prefix="$RISCV"
  make -j"$JOBS"
  make install
)

# 6. The configuration: Chipyard's MediumBoomV3Config (2-wide BOOM v3). The broadcast coherence
#    manager (instead of the L2) and the removal of the debug module make the model faster and
#    do not change the core.
cat >generators/chipyard/src/main/scala/config/ACTConfigs.scala <<'EOF'
package chipyard

import org.chipsalliance.cde.config.Config

class ACTMediumBoomV3Config extends Config(
  new chipyard.config.WithBroadcastManager ++
  new chipyard.config.WithNoDebug ++
  new chipyard.MediumBoomV3Config)
EOF

# 7. Elaborate and verilate
make -C sims/verilator -j"$JOBS" CONFIG="$CONFIG" JAVA_HEAP_SIZE="${JAVA_HEAP_SIZE:-12G}"

install -m 0755 "sims/verilator/simulator-chipyard.harness-$CONFIG" "$INSTALL_DIR/bin/simulator-boom"
install -m 0755 "$SCRIPT_DIR/run-boom.sh" "$INSTALL_DIR/bin/run-boom.sh"

# The simulator needs only the shared libraries in $RISCV/lib at run time; drop everything else
# unless KEEP_BUILD is set (for local rebuilds).
[ -z "${KEEP_BUILD:-}" ] || exit 0
cd "$INSTALL_DIR"
rm -rf chipyard "$TOOLS/verilator" "$TOOLS/jdk" "$TOOLS/firtool" "$TOOLS/espresso" \
  "${RISCV:?}/bin" "${RISCV:?}/include" "${RISCV:?}/lib/pkgconfig" "${RISCV:?}"/lib/*.a
