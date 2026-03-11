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


# Adds datatype to signatures.
# Appends 'mtrap_sigptr' label if TRAP_CANARY is present
def process_signature_file(sig_file: Path, xlen: int) -> None:
    """Add datatype directive to each line of the signature file."""
    datatype = ".word" if xlen == 32 else ".quad"
    trap_canary = "d3a91f6c" if xlen == 32 else "d3a91f6c8b47e25d"
    sig_data = sig_file.read_text()
    result_file = sig_file.with_suffix(".results")
    with result_file.open("w") as outfile:
        for line in sig_data.splitlines():
            if line.strip():  # Skip empty lines
                outfile.write(f"{datatype} 0x{line}\n")
                if trap_canary in line:
                    outfile.write("mtrap_sigptr:\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Modify signature file for assembly compatibility")
    parser.add_argument("sig_file", type=Path, help="Path to the signature file")
    parser.add_argument("xlen", type=int, choices=[32, 64], help="XLEN value (32 or 64)")
    args = parser.parse_args()

    process_signature_file(args.sig_file, args.xlen)
