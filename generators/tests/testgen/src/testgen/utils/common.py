##################################
# common.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Common utilities for riscv-arch-test test generation.
"""

from typing import Literal

from testgen.data.test_data import TestData


def to_hex(value: int, bits: int) -> str:
    """
    Convert an integer to a hex string for assembly output.

    Args:
        value: The integer value (should already be in correct range)
        bits: Number of bits (used to handle negative values)
    """
    # For negative values, convert to unsigned representation
    if value < 0:
        value = value + (2**bits)
    return f"0x{value:x}"


def load_int_reg(name: str, reg: int, val: int, test_data: TestData) -> str:
    """Generate assembly to load an integer register with a specific value."""
    hex_val = to_hex(val, test_data.xlen)
    return f"LI(x{reg}, {hex_val}) # initialize {name}"


def load_float_reg(name: str, reg: int, val: float, precision: Literal[16, 32, 64, 128], test_data: TestData) -> str:
    """Generate assembly to load a floating point register with a specific value."""
    if precision == 16:
        loadop = "flh"
    elif precision == 32:
        loadop = "flw"
    elif precision == 64:
        loadop = "fld"
    else:  # precision == 128
        loadop = "flq"
    storeop = "sw" if min(test_data.xlen, test_data.flen) == 32 else "sd"
    formatstr = test_data.flen_format_str
    fp_data_base_reg = 2  # Assumes that x2 is loaded with the base address to avoid repeated `la` instructions
    temp_reg = test_data.int_regs.get_register()
    test_lines = [f"LA(x{fp_data_base_reg}, scratch)"]
    if precision > test_data.xlen:
        test_lines.extend(
            [
                f"LI(x{temp_reg}, 0x{formatstr.format(val)[10:18]}) # load x{temp_reg} with 32 MSBs {formatstr.format(val)}\n"
                f"{storeop} x{temp_reg}, 0(x{fp_data_base_reg}) # store x{temp_reg} (0x{formatstr.format(val)[10:18]}) in memory\n"
                f"LI(x{temp_reg}, 0x{formatstr.format(val)[2:10]}) # load x{temp_reg} with 32 LSBs of {formatstr.format(val)}\n"
                f"{storeop} x{temp_reg}, 4(x{fp_data_base_reg}) # store x{temp_reg} (0x{formatstr.format(val)[2:10]}) in memory 4 bytes after x{fp_data_base_reg}\n"
                f"{loadop} f{reg}, 0(x{fp_data_base_reg}) # load {formatstr.format(val)} from memory into f{reg}"
            ]
        )
    else:
        test_lines.extend(
            [
                f"LI(x{temp_reg}, {formatstr.format(val)}) # load x{temp_reg} with value {formatstr.format(val)}\n"
                f"{storeop} x{temp_reg}, 0(x{fp_data_base_reg}) # store {formatstr.format(val)} in memory\n"
                f"{loadop} f{reg}, 0(x{fp_data_base_reg}) # load {formatstr.format(val)} from memory into f{reg}"
            ]
        )
    test_data.int_regs.return_registers([temp_reg])
    return "\n".join(test_lines)


def write_sigupd(rd: int, test_data: TestData, sig_type: Literal["int", "float"] = "int") -> str:
    """
    Generate assembly for SIGUPD and increment sigupd_count.
    """
    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    if sig_type == "int":
        test_data.sigupd_count += 1
        return (
            f"# Check if x{rd} contians the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            + f"RVTEST_SIGUPD(x{sig_reg}, x{link_reg}, x{temp_reg}, x{rd})"
        )
    elif sig_type == "float":
        raise NotImplementedError("Floating point signature updates are not yet implemented.")
        # test_data.sigupd_count_float += 2
        # temp_reg = test_data.int_regs.get_register()
        # sigupd_str = f"csrr x{temp_reg}, fcsr\n"  # Get fcsr into a temp register
        # sigupd_str += f"RVTEST_SIGUPD_F(x{sig_reg}, f{rd}, x{temp_reg})"
        # test_data.int_regs.return_registers([temp_reg])
        # return sigupd_str
    else:
        raise ValueError("Invalid sig_type specified.")


def get_sig_space(test_data: TestData) -> int:
    """Get the space needed for signature region taking xlen and flen into account."""
    xlen = test_data.xlen
    flen = test_data.flen
    # Integer sigup space
    sig_words = test_data.sigupd_count
    # Floating point sigup space
    if test_data.sigupd_count_float > 0:
        if flen > xlen:
            float_scale_factor = flen // xlen
            sig_words += test_data.sigupd_count_float * float_scale_factor
        else:
            sig_words += test_data.sigupd_count_float
    # Account for offset overflow adjustment
    sig_words += (4 // (xlen // 32)) * (((sig_words * (xlen // 32)) * 4) // 2016)
    return sig_words


def myhash(s: str) -> int:
    """Return a simple hash of a string for use as a random seed.

    Python randomizes hashes by default, but we need a repeatable hash for repeatable test cases.
    """
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h
