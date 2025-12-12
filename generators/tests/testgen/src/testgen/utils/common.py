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
    return f"0x{value:0{bits // 4}x}"


def load_int_reg(name: str, reg: int, val: int, test_data: TestData) -> str:
    """Generate assembly to load an integer register with a specific value."""
    test_data.add_test_data_value(val)
    return f"RVTEST_TESTDATA_LOAD_INT(x{test_data.int_regs.link_reg}, x{reg}) # load {name}: x{reg} = {to_hex(val, test_data.xlen)}"


def load_float_reg(name: str, reg: int, val: int, test_data: TestData) -> str:
    """Generate assembly to load a floating point register with a specific value."""
    test_data.add_test_data_value(val)
    return f"RVTEST_TESTDATA_LOAD_FLOAT(x{test_data.int_regs.link_reg}, f{reg}) # load {name}: f{reg} = {to_hex(val, test_data.flen)}"


def write_sigupd(check_reg: int, test_data: TestData, sig_type: Literal["int", "float"] = "int") -> str:
    """
    Generate assembly for SIGUPD and increment sigupd_count.
    """
    sig_reg = test_data.int_regs.sig_reg
    link_reg = test_data.int_regs.link_reg
    temp_reg = test_data.int_regs.temp_reg
    fp_temp_reg = test_data.float_regs.temp_reg
    if sig_type == "int":
        test_data.sigupd_count += 1
        return (
            f"# Check if x{check_reg} contains the expected result. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            + f'RVTEST_SIGUPD(x{sig_reg}, x{link_reg}, x{temp_reg}, x{check_reg}, "test_{test_data.test_count}")'
        )
    elif sig_type == "float":
        test_data.sigupd_count += 2
        return (
            f"# Check if f{check_reg} contains the expected result. Also checks fflags. x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            + f'RVTEST_SIGUPD_F(x{sig_reg}, x{link_reg}, x{temp_reg}, f{fp_temp_reg}, f{check_reg}, "test_{test_data.test_count}")'
        )


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


def generate_test_data_section(test_data: TestData) -> str:
    """
    Generate the .data section containing all test values.

    Args:
        test_data: TestData object containing the values to generate

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = []

    # Use .word for 32-bit, .dword for 64-bit
    directive = ".word" if max(test_data.xlen, test_data.flen) == 32 else ".dword"

    for value in test_data.test_data_values:
        hex_value = to_hex(value, test_data.xlen)
        lines.append(f"    {directive} {hex_value}")

    return "\n".join(lines)


def generate_test_data_string_section(test_data: TestData) -> str:
    """
    Generate the .data section containing all test strings.

    Args:
        test_data: TestData object containing the strings to generate

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = ['canary_mismatch: .string "Testcase signature canary mismatch!"']
    lines.extend(test_data.test_data_strings)

    return "\n".join(lines)
