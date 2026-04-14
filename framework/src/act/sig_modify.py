##################################
# sig_modify.py
#
# jcarlin@hmc.edu 29 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Update signature file to be compatible with assembler
##################################

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
