#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# run-cv32e40s.sh — run one ELF on the CV32E40S Verilator testbench built by install-cve4.sh
#
# The testbench (cv32e40x-dv's core testbench with cv32e40s_tb_wrapper.sv) reads the ELF
# header for the entry point and loads the sibling <base>.hex via $readmemh, so this
# wrapper generates the .hex (via objcopy) first. run_tests.py appends the ELF path as
# the final argument. Output goes through the testbench virtual printer (0x1000_0000).
#
# Usage:
#   run-cv32e40s.sh --cfg <rv32imc|rv32imc-pma|rv32imc-pma-pmp|rv32imcb-pma-pmp> --elf <elf-file>
#
# Environment:
#   CVE40S_TB_ROOT  — directory holding <cfg>/Vtb_top (default: ../cv32e40s-tb from this script)
#   CV_SW_PREFIX    — RISC-V toolchain prefix (default: riscv64-unknown-elf-)
#   CERT_MAXCYCLES  — per-test cycle bound (default: 200000)
set -euo pipefail

CFG=""
ELF=""

usage() {
  echo "Usage: run-cv32e40s.sh --cfg <config> --elf <elf-file>" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
  --cfg)
    CFG="$2"
    shift 2
    ;;
  --elf)
    ELF="$2"
    shift 2
    ;;
  -*)
    echo "Unknown argument: $1" >&2
    usage
    exit 2
    ;;
  *)
    ELF="$1"
    shift
    ;;
  esac
done

: "${CFG:?--cfg <config> is required}"
: "${ELF:?ELF file is required (pass --elf <file> or as final positional argument)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CVE40S_TB_ROOT="${CVE40S_TB_ROOT:-$(cd "$SCRIPT_DIR/../cv32e40s-tb" && pwd)}"
SIM="$CVE40S_TB_ROOT/$CFG/Vtb_top"
CV_SW_PREFIX="${CV_SW_PREFIX:-riscv64-unknown-elf-}"
CERT_MAXCYCLES="${CERT_MAXCYCLES:-200000}"

[[ -x $SIM ]] || {
  echo "Vtb_top not found for cfg=$CFG at $SIM; build it with .github/scripts/install-cve4.sh" >&2
  exit 2
}

# Generate <base>.hex if missing or older than the ELF; the testbench loads it.
HEX="${ELF%.*}.hex"
if [[ ! -f $HEX || $ELF -nt $HEX ]]; then
  "${CV_SW_PREFIX}objcopy" -O verilog "$ELF" "$HEX"
fi

exec "$SIM" "+maxcycles=$CERT_MAXCYCLES" "+elf_file=$ELF"
