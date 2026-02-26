##################################
# cp_fp_regs.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Register coverpoint handlers (cp_fd, cp_fs1, cp_fs2, cp_fs3)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters import format_single_test
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_fd")
def make_fd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for destination floating-point register coverpoints."""
    # Determine which fd registers to test based on coverpoint variant
    if coverpoint == "cp_fd":
        fd_regs = list(range(test_data.float_regs.reg_count))
    elif coverpoint.endswith("fd_p"):
        fd_regs = list(range(8, 16))  # f8-f15 for compressed instructions
    else:
        raise ValueError(f"Unknown cp_fd coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for fd in fd_regs:
        test_data.float_regs.consume_registers([fd])
        params = generate_random_params(test_data, instr_type, fd=fd)
        desc = f"{coverpoint} (Test destination fd = f{fd})"
        test_lines.extend(
            [
                test_data.add_testcase(f"b{fd}", coverpoint),
                format_single_test(instr_name, instr_type, test_data, params, desc),
            ]
        )
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs1")
def make_fs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for source floating-point register 1 coverpoints."""
    # Determine which fs1 registers to test based on coverpoint variant
    if coverpoint == "cp_fs1":
        fs1_regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_p"):
        fs1_regs = range(8, 16)  # f8-f15 for compressed instructions
    else:
        raise ValueError(f"Unknown cp_fs1 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for fs1 in fs1_regs:
        test_data.float_regs.consume_registers([fs1])
        params = generate_random_params(test_data, instr_type, fs1=fs1)
        desc = f"{coverpoint} (Test source fs1 = f{fs1})"
        test_lines.extend(
            [
                test_data.add_testcase(f"b{fs1}", coverpoint),
                format_single_test(instr_name, instr_type, test_data, params, desc),
            ]
        )
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs2")
def make_fs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for source floating-point register 1 coverpoints."""
    # Determine which fs2 registers to test based on coverpoint variant
    if coverpoint == "cp_fs2":
        fs2_regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_p"):
        fs2_regs = range(8, 16)  # f8-f15 for compressed instructions
    else:
        raise ValueError(f"Unknown cp_fs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for fs2 in fs2_regs:
        test_data.float_regs.consume_registers([fs2])
        params = generate_random_params(test_data, instr_type, fs2=fs2)
        desc = f"{coverpoint} (Test source fs2 = f{fs2})"
        test_lines.extend(
            [
                test_data.add_testcase(f"b{fs2}", coverpoint),
                format_single_test(instr_name, instr_type, test_data, params, desc),
            ]
        )
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs3")
def make_fs3(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for source floating-point register 1 coverpoints."""
    # Determine which fs3 registers to test based on coverpoint variant
    if coverpoint == "cp_fs3":
        fs3_regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_p"):
        fs3_regs = range(8, 16)  # f8-f15 for compressed instructions
    else:
        raise ValueError(f"Unknown cp_fs3 coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Generate tests
    for fs3 in fs3_regs:
        test_data.float_regs.consume_registers([fs3])
        params = generate_random_params(test_data, instr_type, fs3=fs3)
        desc = f"{coverpoint} (Test source fs2 = f{fs3})"
        test_lines.extend(
            [
                test_data.add_testcase(f"b{fs3}", coverpoint),
                format_single_test(instr_name, instr_type, test_data, params, desc),
            ]
        )
        return_test_regs(test_data, params)

    return test_lines
