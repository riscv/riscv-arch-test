#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the XiangShan Kunminghu V2 difftest emulator (Verilator).
# Usage: install-xiangshan.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.
#
# Needs a JDK 11 or newer on PATH (mill), clang, and about 24 GB of memory for Chisel elaboration.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="${1:?Usage: install-xiangshan.sh <install-dir>}"
XIANGSHAN_REPO="https://github.com/OpenXiangShan/XiangShan.git"
XIANGSHAN_COMMIT="e7bab53e66dfb3c4a1d11cf9519b0396f8576cae" # kunminghu-v2
MILL_VERSION="0.12.3"
VERILATOR_VERSION="v5.036"

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"

# 2. mill, at the version XiangShan pins in .mill-version
curl -fsSL -o "$INSTALL_DIR/bin/mill" \
  "https://repo1.maven.org/maven2/com/lihaoyi/mill-dist/$MILL_VERSION/mill-dist-$MILL_VERSION.jar"
chmod +x "$INSTALL_DIR/bin/mill"
export PATH="$INSTALL_DIR/bin:$PATH"

# 3. XiangShan and its submodules at the pinned commit
git init "$INSTALL_DIR/XiangShan"
(
  cd "$INSTALL_DIR/XiangShan"
  git remote add origin "$XIANGSHAN_REPO"
  git fetch --depth 1 origin "$XIANGSHAN_COMMIT"
  git checkout FETCH_HEAD
  make init
)

# 4. Elaborate DefaultConfig and build the single-threaded emulator. The Makefile's default
#    OPT_FAST contains a clang-only flag, so the C++ is compiled with clang.
(
  cd "$INSTALL_DIR/XiangShan"
  NOOP_HOME="$PWD" make emu CONFIG=DefaultConfig EMU_THREADS=0 CXX=clang++ -j"$(nproc)"
)
cp -L "$INSTALL_DIR/XiangShan/build/emu" "$INSTALL_DIR/bin/emu"
install -m 0755 "$SCRIPT_DIR/run-xiangshan.sh" "$INSTALL_DIR/bin/run-xiangshan.sh"
