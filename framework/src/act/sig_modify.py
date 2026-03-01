##################################
# sig_modify.py
#
# jcarlin@hmc.edu 29 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Update signature file to be compatible with assembler
##################################

import argparse
from pathlib import Path


def add_datatype_to_signature(sig_file: Path, xlen: int) -> None:
    """Add datatype directive to each line of the signature file."""
    datatype = ".word" if xlen == 32 else ".quad"
    sig_data = sig_file.read_text()
    result_file = sig_file.with_suffix(".results")
    with result_file.open("w") as outfile:
        for line in sig_data.splitlines():
            if line.strip():  # Skip empty lines
                outfile.write(f"{datatype} 0x{line}\n")


def extract_trap_signatures(sig_file: Path, xlen: int) -> None:
    CANARY = "0x6f5ca309" if xlen == 32 else "0x6f5ca309e7d4b281"
    result_file = sig_file.with_suffix(".results")
    lines = result_file.read_text().splitlines()
    canary_indices = [i for i, line in enumerate(lines) if CANARY in line]
    if len(canary_indices) > 2:  # Indication of trap signatures
        start, end = canary_indices[1], canary_indices[2]
        trap_signatures = lines[start + 1 : end]
        trap_result_file = sig_file.with_suffix(".trap.results")
        with trap_result_file.open("w") as outfile:
            for line in trap_signatures:
                outfile.write(line + "\n")
        base_signatures = lines[:start] + lines[end + 1 :]  # Trap signatures excluded
        with result_file.open("w") as outfile:
            for line in base_signatures:
                outfile.write(line + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Modify signature file for assembly compatibility")
    parser.add_argument("sig_file", type=Path, help="Path to the signature file")
    parser.add_argument("xlen", type=int, choices=[32, 64], help="XLEN value (32 or 64)")
    args = parser.parse_args()

    add_datatype_to_signature(args.sig_file, args.xlen)
    extract_trap_signatures(args.sig_file, args.xlen)
