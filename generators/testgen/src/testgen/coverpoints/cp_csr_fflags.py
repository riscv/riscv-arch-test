# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0

"""Floating-point flags coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction
from testgen.instructions.params import generate_random_params
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params

_FLAG_BITS = {"v": 0b10000, "d": 0b01000, "o": 0b00100, "u": 0b00010, "n": 0b00001}


@add_coverpoint_generator("cp_csr_fflags")
def make_fflags(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests with each applicable fflags bit already set."""
    suffix = coverpoint.removeprefix("cp_csr_fflags_")
    if not suffix or any(flag not in _FLAG_BITS for flag in suffix):
        raise ValueError(f"Unknown cp_csr_fflags coverpoint variant: {coverpoint} for {instr_name}")

    fflags = sum(_FLAG_BITS[flag] for flag in suffix)
    if instr_name.lower().startswith("v"):
        assert test_data.config.sew is not None, "SEW must be set for vector tests"
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=get_base_lmul(instr_name, instr_type, test_data.config.sew)
        )
    else:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])

    tc = test_data.begin_test_chunk()
    tc.code.append(f"# Testcase {coverpoint} (fflags = {fflags:05b})")
    label = test_data.add_testcase(f"b{fflags:05b}", coverpoint)
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)
    if setup:
        tc.code.append(setup)
    tc.code.extend([f"csrsi fcsr, 0b{fflags:05b} # set fflags", label, test])
    if check:
        tc.code.append(check)

    test_chunk = test_data.end_test_chunk()
    return_testcase_registers(test_data, params)
    return [test_chunk]
