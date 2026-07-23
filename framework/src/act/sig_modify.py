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
# Appends 'trap_sigptr' label if TRAP_CANARY is present and marks the final canary.
def process_signature_file(sig_file: Path, xlen: int) -> None:
    """Add datatype directive to each line of the signature file."""
    datatype = ".word" if xlen == 32 else ".quad"
    trap_canary = "d3a91f6c" if xlen == 32 else "d3a91f6c8b47e25d"
    sig_data = sig_file.read_text()
    result_file = sig_file.with_suffix(".results")
    sig_lines = [line for line in sig_data.splitlines() if line.strip()]
    with result_file.open("w") as outfile:
        for line_number, line in enumerate(sig_lines):
            if line_number == len(sig_lines) - 1:
                outfile.write("sig_end_canary:\n")
            outfile.write(f"{datatype} 0x{line}\n")
            if trap_canary in line:
                outfile.write("trap_sigptr:\n")
