#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build NaxRiscv's own Verilator simulator (src/test/cpp/naxriscv) for CI.
# Usage: install-naxriscv.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate. The patch
# checksum is pinned here too, so a changed patch also changes the key.
#
# The core is NaxRiscv's standard RV64 configuration, the default target (rv64imafdcsu) of its
# Makefile:
#   sbt "runMain naxriscv.Gen64 --withRvc --withFloat --withDouble"
# config/cores/naxriscv/README.md describes the configuration. The simulator is built as
# NaxRiscv's Makefile builds it, with two changes listed below.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:?Usage: install-naxriscv.sh <install-dir>}"
mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
JOBS="${JOBS:-$(nproc)}"

NAXRISCV_REPO="https://github.com/SpinalHDL/NaxRiscv.git"
NAXRISCV_COMMIT="9f452d50560d02fb391bc8039f5453c54e0911af" # main, 2026-01-23
ELFIO_COMMIT="d251da09a07dff40af0b63b8f6c8ae71d2d1938d"    # ELFIO_VERSION in NaxRiscv's Makefile
VERILATOR_VERSION="v5.036"
JDK_URL="https://api.adoptium.net/v3/binary/version/jdk-17.0.16%2B8/linux/x64/jdk/hotspot/normal/eclipse"
SBT_VERSION="1.10.11"

PATCH_DIR="$SCRIPT_DIR/../../config/cores/naxriscv/patches"
# Simulator (src/test/cpp/naxriscv/src/main.cpp): mtime is writable and advances once every 10
# cycles instead of every cycle, and mip.MTIP is set when mtime >= mtimecmp instead of >.
# See config/cores/naxriscv/README.md.
SIM_PATCH="naxriscv-sim-mtime.patch"
SIM_PATCH_SHA256="16373f8e6b55a223675e71c708459f967cc141ec2224f416bd21cd731a615390"

TOOLS="$INSTALL_DIR/tools"
mkdir -p "$TOOLS"

# 1. Verilator, a JDK and sbt
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$TOOLS/verilator-src"
(
  cd "$TOOLS/verilator-src"
  autoconf
  ./configure --prefix="$TOOLS/verilator"
  make -j"$JOBS"
  make install
)
rm -rf "$TOOLS/verilator-src"
mkdir -p "$TOOLS/jdk"
curl -fsSL "$JDK_URL" | tar -xz -C "$TOOLS/jdk" --strip-components=1
curl -fsSL "https://github.com/sbt/sbt/releases/download/v$SBT_VERSION/sbt-$SBT_VERSION.tgz" | tar -xz -C "$TOOLS"
export JAVA_HOME="$TOOLS/jdk"
export PATH="$TOOLS/verilator/bin:$TOOLS/jdk/bin:$TOOLS/sbt/bin:$PATH"

# 2. NaxRiscv at the pinned commit, with the submodules the build uses (SpinalHDL, NaxRiscv's
#    Spike fork, which the simulator links for its optional lock-step check, and rvls, whose
#    JNI bindings build.sbt compiles). NaxSoftware (prebuilt test programs) is not needed.
NAXRISCV_DIR="$INSTALL_DIR/NaxRiscv"
git init "$NAXRISCV_DIR"
cd "$NAXRISCV_DIR"
git remote add origin "$NAXRISCV_REPO"
git fetch --depth 1 origin "$NAXRISCV_COMMIT"
git checkout FETCH_HEAD
git submodule update --init --recursive --depth 1 ext/SpinalHDL ext/riscv-isa-sim ext/rvls
(cd "$PATCH_DIR" && printf '%s  %s\n' "$SIM_PATCH_SHA256" "$SIM_PATCH" | sha256sum -c -)
git apply "$PATCH_DIR/$SIM_PATCH"

# 3. Generate the RTL (NaxRiscv.v and its C header)
sbt -J-Xmx8G "runMain naxriscv.Gen64 --withRvc --withFloat --withDouble"

# 4. NaxRiscv's Spike fork and ELFIO, as ci/install-libsdl-elfio-spikespinalhdl.sh builds them.
#    The system SDL2 replaces that script's SDL build.
SPIKE="$NAXRISCV_DIR/ext/riscv-isa-sim"
mkdir -p "$SPIKE/build" "$SPIKE/include" "$SPIKE/lib"
(
  cd "$SPIKE/build"
  ../configure --prefix="$SPIKE" --without-boost --without-boost-asio --without-boost-regex
  make -j"$JOBS"
)
git clone https://github.com/serge1/ELFIO.git "$TOOLS/elfio"
git -C "$TOOLS/elfio" checkout "$ELFIO_COMMIT"
cp -R "$TOOLS/elfio/elfio" "$SPIKE/include/"

# 5. Build the simulator (with the patch applied in step 2). Two changes to
#    src/test/cpp/naxriscv/makefile:
#    - Link Spike's static libraries only. The makefile also links package.so, a shared library
#      made from the same objects, and the second copy of Spike's device registry makes the
#      simulator abort at start with 'Plugin "clint" already registered'.
#    - TRACE=no: no FST waveform support, which also drops the libz dependency.
cd "$NAXRISCV_DIR/src/test/cpp/naxriscv"
# shellcheck disable=SC2016 # ${SPIKE_BUILD} is makefile text, not a shell expansion
sed -i 's|^SRCS+=${SPIKE_BUILD}/package.so|#&|' makefile
# shellcheck disable=SC2016
grep -q '^#SRCS+=${SPIKE_BUILD}/package.so' makefile
make compile TRACE=no THREAD_COUNT="$JOBS"

install -m 0755 obj_dir/VNaxRiscv "$INSTALL_DIR/bin/VNaxRiscv"
install -m 0755 "$SCRIPT_DIR/run-naxriscv.sh" "$INSTALL_DIR/bin/run-naxriscv.sh"

cd "$INSTALL_DIR"
rm -rf "$NAXRISCV_DIR" "$TOOLS"
