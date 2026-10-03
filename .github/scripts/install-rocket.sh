#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the Chipyard Verilator simulator for Rocket + Saturn + H (ACTRocketSaturnHConfig) for CI.
# Usage: install-rocket.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate. The patch
# checksums are pinned here too, so a changed patch also changes the key.
#
# Chipyard 1.14.0 with its rocket-chip, Saturn master instead of Chipyard's Saturn pin, and three
# local patches from config/cores/rocket/patches/ (see config/cores/rocket/README.md):
#  - rocket-chip PR #3820 (open), which Saturn master's .vf scalar NaN-box check (Saturn PR #88)
#    depends on;
#  - a one-line rocket-chip TLB fix for a livelock on a guest-page fault behind a VS-stage
#    superpage, so that the hypervisor suites run to completion;
#  - a one-line Saturn fix for the permute/reduction sequencer deadlock (Saturn issue #74), so
#    that the vector suites run to completion.
#
# Chipyard's own build-setup.sh installs a conda environment and a RISC-V toolchain; neither is
# needed to build a Verilator simulator, so this script installs only what the build uses:
# Verilator, a JDK for sbt, CIRCT firtool, espresso, and Spike's libfesvr/libriscv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:?Usage: install-rocket.sh <install-dir>}"
mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
JOBS="${JOBS:-$(nproc)}"

CHIPYARD_REPO="https://github.com/ucb-bar/chipyard.git"
CHIPYARD_COMMIT="0acc1e1de2d3284bcd4d876956932a013ffe1949" # 1.14.0
VERILATOR_VERSION="v5.036"
FIRTOOL_VERSION="1.75.0" # conda-reqs/circt.json at the pinned Chipyard commit
JDK_URL="https://api.adoptium.net/v3/binary/version/jdk-17.0.16%2B8/linux/x64/jdk/hotspot/normal/eclipse"
SATURN_COMMIT="8ef05c9c6044f05750c49e166a784ef8fbdcb883" # saturn-vectors master, 2026-09-02
CONFIG="ACTRocketSaturnHConfig"

PATCH_DIR="$SCRIPT_DIR/../../config/cores/rocket/patches"
# rocket-chip PR #3820 at its head commit d1d2c5e78138ddda9d439be0bb3081f107416ab9
# (https://github.com/chipsalliance/rocket-chip/pull/3820): the FPU hands .vf scalars to the vector
# unit as the full 64-bit register, so NaN-boxed single and half values keep their box. Without it,
# Saturn master turns every NaN-boxed single or half .vf scalar into the canonical NaN.
RC_PATCH="rocket-chip-pr3820-d1d2c5e7.patch"
RC_PATCH_SHA256="cc402d03d5d1f8f057231c237c78d2ee0b4d6fd89bd5b990082da9135c1385a7"
# rocket-chip rocket/TLB.scala: the superpage refill writes the entry that hit (waddr), as the
# sectored refill does. Without it, a VS/VU access whose VS-stage leaf is a 2 MiB or 1 GiB page
# and whose G-stage translation faults neither retires nor traps. No upstream issue or PR.
TLB_PATCH="rocket-chip-tlb-superpage-gpa.patch"
TLB_PATCH_SHA256="a0adf68d71ccf5caba8dc4674384eceaa2fd3421ebcce2bce8fed59928658d00"
# Saturn backend/SpecialSequencer.scala: clear the permute sequencer's valid on acc_done only
# while it holds an instruction (https://github.com/ucb-bar/saturn-vectors/issues/74). Without it,
# a stale acc/acc_done pair drops a slide or reduction at dispatch and the vector unit deadlocks.
SATURN_PATCH="saturn-acc-done-valid.patch"
SATURN_PATCH_SHA256="17a31e3bcef3e556f34b1ae362862e29b15dad579e39890e766b1b79398d73a1"

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

# 3. Chipyard at the pinned commit, with the submodules a Rocket + Saturn build needs
git init "$INSTALL_DIR/chipyard"
cd "$INSTALL_DIR/chipyard"
git remote add origin "$CHIPYARD_REPO"
git fetch --depth 1 origin "$CHIPYARD_COMMIT"
git checkout FETCH_HEAD
./scripts/init-submodules-no-riscv-tools.sh --saturn
git -C generators/saturn fetch origin "$SATURN_COMMIT"
git -C generators/saturn checkout --detach "$SATURN_COMMIT"
(
  cd "$PATCH_DIR"
  printf '%s  %s\n' "$RC_PATCH_SHA256" "$RC_PATCH" "$TLB_PATCH_SHA256" "$TLB_PATCH" \
    "$SATURN_PATCH_SHA256" "$SATURN_PATCH" | sha256sum -c -
)
git -C generators/rocket-chip apply "$PATCH_DIR/$RC_PATCH" "$PATCH_DIR/$TLB_PATCH"
git -C generators/saturn apply "$PATCH_DIR/$SATURN_PATCH"
git submodule update --init --depth 1 toolchains/riscv-tools/riscv-isa-sim

# 4. espresso. Without it on PATH, Chisel falls back to its QMC minimizer, which runs out of
#    memory on Saturn's instruction decoder.
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

# 6. The configuration: Saturn's MINV128D64RocketConfig with the hypervisor extension, Sv48 and
#    29 HPM counters. The broadcast coherence manager (instead of the L2) and the removal of the
#    debug module make the model about 1.7x faster than the REFV256D128 SoC and do not change
#    the core.
cat >generators/chipyard/src/main/scala/config/ACTConfigs.scala <<'EOF'
package chipyard

import org.chipsalliance.cde.config.Config

class ACTRocketSaturnHConfig extends Config(
  new chipyard.config.WithNPerfCounters(29) ++
  new freechips.rocketchip.rocket.WithHypervisor ++
  new freechips.rocketchip.rocket.WithSV48 ++
  new chipyard.config.WithBroadcastManager ++
  new chipyard.config.WithNoDebug ++
  new chipyard.MINV128D64RocketConfig)
EOF

# 7. Elaborate and verilate
make -C sims/verilator -j"$JOBS" CONFIG="$CONFIG" JAVA_HEAP_SIZE="${JAVA_HEAP_SIZE:-12G}"

install -m 0755 "sims/verilator/simulator-chipyard.harness-$CONFIG" "$INSTALL_DIR/bin/simulator-rocket-saturn-h"
install -m 0755 "$SCRIPT_DIR/run-rocket.sh" "$INSTALL_DIR/bin/run-rocket.sh"

# The simulator needs only the shared libraries in $RISCV/lib at run time; drop everything else.
cd "$INSTALL_DIR"
rm -rf chipyard "$TOOLS/verilator" "$TOOLS/jdk" "$TOOLS/firtool" "$TOOLS/espresso" \
  "${RISCV:?}/bin" "${RISCV:?}/include" "${RISCV:?}/lib/pkgconfig" "${RISCV:?}"/lib/*.a
