##################################
# sig_modify.py
#
# jcarlin@hmc.edu 29 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Update signature file to be compatible with assembler
##################################

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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Modify signature file for assembly compatibility")
    parser.add_argument("sig_file", type=Path, help="Path to the signature file")
    parser.add_argument("xlen", type=int, choices=[32, 64], help="XLEN value (32 or 64)")
    args = parser.parse_args()

    add_datatype_to_signature(args.sig_file, args.xlen)
