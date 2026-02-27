##################################
# asm/helpers.py
#
# Assembly generation helpers for test code.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly generation helpers for test code."""

from typing import Literal

from testgen.data.params import InstructionParams
from testgen.data.state import TestData


def comment_banner(title: str, description: str | None = None) -> str:
    """
    Generate a comment banner for a test section.

    Args:
        title: The title of the section (e.g., coverpoint name)
        description: Optional multi-line description

    Returns:
        Formatted comment banner string
    """
    lines = [
        "",
        "",
        "/////////////////////////////////",
        f"// {title}",
    ]
    if description:
        lines.extend(f"//   {line}" for line in description.strip().split("\n"))
    lines.append("/////////////////////////////////")
    return "\n".join(lines)


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
    return f"\tRVTEST_TESTDATA_LOAD_INT(x{test_data.int_regs.data_reg}, x{reg}) # load {name}: x{reg} = {to_hex(val, test_data.xlen)}"


def load_float_reg(
    name: str,
    reg: int,
    val: int,
    test_data: TestData,
    fp_load_type: Literal["single", "double", "half", "quad"] | None = None,
) -> str:
    """Generate assembly to load a floating point register with a specific value."""
    if fp_load_type is None:
        fp_load_type = test_data.fp_load_size

    test_data.add_test_data_value(val)
    return f"\tRVTEST_TESTDATA_LOAD_FLOAT_{fp_load_type.upper()}(x{test_data.int_regs.data_reg}, f{reg}) # load {name}: f{reg} = {to_hex(val, test_data.flen)}"


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
            f"\t# Check if x{check_reg} contains the expected result. x{sig_reg} is the signature ptr, "
            + f"x{link_reg} is the link ptr, x{temp_reg} is a temp reg.\n"
            + f"\tRVTEST_SIGUPD(x{sig_reg}, x{link_reg}, x{temp_reg}, x{check_reg}, {test_data.current_testcase_label}, {test_data.current_testcase_label}_str)"
        )
    elif sig_type == "float":
        if test_data.flen > test_data.xlen:
            test_data.sigupd_count += 3
        else:
            test_data.sigupd_count += 2
        return (
            f"\t# Check if f{check_reg} contains the expected result. Also checks fflags. "
            + f"x{sig_reg} is the signature ptr, x{link_reg} is the link ptr, x{temp_reg} "
            + f"is a temp reg, f{fp_temp_reg} is a floating point temp reg.\n"
            + f"\tRVTEST_SIGUPD_F(x{sig_reg}, x{link_reg}, x{temp_reg}, f{fp_temp_reg}, f{check_reg}, {test_data.current_testcase_label}, {test_data.current_testcase_label}_str)"
        )
    else:
        raise ValueError(f"Unknown sig_type: {sig_type}")


def reproducible_hash(s: str) -> int:
    """Return a simple hash of a string for use as a random seed.

    Python randomizes hashes by default, but we need a repeatable hash for repeatable test cases.
    """
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return h


def return_test_regs(test_data: TestData, params: InstructionParams) -> None:
    """
    Return all registers used in a test case back to the pool.

    Args:
        test_data: TestData object managing the registers
        params: InstructionParams object containing used registers
    """
    test_data.int_regs.return_registers(params.used_int_regs)
    test_data.float_regs.return_registers(params.used_float_regs)
