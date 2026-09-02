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
# Appends labels for trap diagnostic regions and marks the final canary.
def process_signature_file(sig_file: Path, xlen: int) -> None:
    """Add datatype directive to each line of the signature file."""
    datatype = ".word" if xlen == 32 else ".quad"
    trap_canary = "d3a91f6c" if xlen == 32 else "d3a91f6c8b47e25d"
    final_sig_offset_canary = "4b8e2d17" if xlen == 32 else "4b8e2d17a6c0f953"
    final_trap_offset_canary = "7a110ff5" if xlen == 32 else "7a110ff5c0def00d"
    sig_data = sig_file.read_text()
    result_file = sig_file.with_suffix(".results")
    sig_lines = [line for line in sig_data.splitlines() if line.strip()]
    with result_file.open("w") as outfile:
        for line_number, line in enumerate(sig_lines):
            if line_number == len(sig_lines) - 1:
                outfile.write("sig_end_canary:\n")
            outfile.write(f"{datatype} 0x{line}\n")
            if final_sig_offset_canary in line:
                outfile.write("final_sig_offset:\n")
            if final_trap_offset_canary in line:
                outfile.write("final_trap_sig_offset:\n")
            if trap_canary in line:
                outfile.write("trap_sigptr:\n")
