##################################
# cmp_fp_regs.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Compare floating register coverpoint generators (cmp_fd_fs1, cmp_fd_fs2, cmp_fs1_fs2, cmp_fd_fs1_fs2)."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cmp_fd_fs1")
def make_cmp_fd_fs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests where fd = fs1."""
    # Determine which fd registers to test based on coverpoint variant
    if coverpoint == "cmp_fd_fs1":
        regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    else:
        raise ValueError(f"Unknown cmp_fd_fs1 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    # Generate tests
    for reg in regs:
        test_data.float_regs.consume_registers([reg])
        params = generate_random_params(test_data, instr_type, fd=reg, fs1=reg)
        desc = f"{coverpoint} (Test fd = fs1 = f{reg})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_fd_fs2")
def make_cmp_fd_fs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests where fd = fs2."""
    # Determine which fd registers to test based on coverpoint variant
    if coverpoint == "cmp_fd_fs2":
        regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    else:
        raise ValueError(f"Unknown cmp_fd_fs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    # Generate tests
    for reg in regs:
        test_data.float_regs.consume_registers([reg])
        params = generate_random_params(test_data, instr_type, fd=reg, fs2=reg)
        desc = f"{coverpoint} (Test fd = fs2 = f{reg})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_fd_fs3")
def make_cmp_fd_fs3(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests where fd = fs3."""
    # Determine which fd registers to test based on coverpoint variant
    if coverpoint == "cmp_fd_fs3":
        regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    else:
        raise ValueError(f"Unknown cmp_fd_fs3 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    # Generate tests
    for reg in regs:
        test_data.float_regs.consume_registers([reg])
        params = generate_random_params(test_data, instr_type, fd=reg, fs3=reg)
        desc = f"{coverpoint} (Test fd = fs3 = f{reg})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_fs1_fs2")
def make_cmp_fs1_fs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests where fd = fs2."""
    # Determine which fd registers to test based on coverpoint variant
    if coverpoint == "cmp_fs1_fs2":
        regs = range(test_data.float_regs.reg_count)
    elif coverpoint.endswith("_c"):
        regs = range(8, 16)  # x8-x15 for compressed instructions
    else:
        raise ValueError(f"Unknown cmp_fs1_fs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    # Generate tests
    for reg in regs:
        test_data.float_regs.consume_registers([reg])
        params = generate_random_params(test_data, instr_type, fs1=reg, fs2=reg)
        desc = f"{coverpoint} (Test fs1 = fs2 = f{reg})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cmp_fd_fs1_fs2")
def make_cmp_fd_fs1_fs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests where fd = fs1 = fs2."""
    # Determine which rd registers to test based on coverpoint variant
    if coverpoint == "cmp_fd_fs1_fs2":
        regs = range(test_data.int_regs.reg_count)
    elif coverpoint.endswith("_nx0"):
        regs = range(1, test_data.int_regs.reg_count)  # Exclude x0
    else:
        raise ValueError(f"Unknown cmp_fd_fs1_fs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    # Generate tests
    for reg in regs:
        test_data.float_regs.consume_registers([reg])
        params = generate_random_params(test_data, instr_type, fd=reg, fs1=reg, fs2=reg)
        desc = f"{coverpoint} (Test fd = fs1 = fs2 = f{reg})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"b{reg}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
