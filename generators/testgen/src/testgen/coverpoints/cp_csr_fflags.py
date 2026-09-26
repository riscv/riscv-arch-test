# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0

"""Floating-point flags coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import make_and_register_edge_label
from testgen.data.edges import get_vector_edge
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction, format_single_testcase
from testgen.instructions.params import generate_random_params
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params

_FLAG_BITS = {"v": 0b10000, "d": 0b01000, "o": 0b00100, "u": 0b00010, "n": 0b00001}


@add_coverpoint_generator("cp_csr_fflags")
def make_fflags(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests with the applicable bit in fflags already set, and reach flags configurations otherwise not exercised"""

    test_chunks = []

    # This must come first due to how fflags is handled in the sail trace (otherwise coverage sees another 1->1 transition)
    if instr_name.lower().startswith("v"):
        # Some vector tests do not hit the underflow flag naturally
        test_chunks.extend(generate_vector_special_cases(instr_name, instr_type, coverpoint, test_data))

    test_chunks.extend(generate_preset_fflags_tests(instr_name, instr_type, coverpoint, test_data))

    return test_chunks


def generate_preset_fflags_tests(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
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


def generate_vector_special_cases(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generates a test hitting UF for the vector tests in need of it"""

    assert test_data.config.sew is not None, "SEW must be set for vector tests"

    kwargs = {}

    if instr_name in ["vfmacc.vf", "vfnmacc.vf", "vfmsac.vf", "vfnmsac.vf"]:
        vs2_label = make_and_register_edge_label("vs2", "min_subnorm", "f", test_data)
        vd_label = make_and_register_edge_label("vd", "pos0", "f", test_data)
        fs1_val = get_vector_edge("min_subnorm", "f", test_data.config.sew)

        kwargs = {
            "vs2_val_pointer": vs2_label,
            "vd_val_pointer": vd_label,
            "fs1val": fs1_val,
        }
    else:
        return []

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        get_base_lmul(instr_name, instr_type, test_data.config.sew),
        additional_no_overlap={("vd", "vs1"), ("vd", "vs2"), ("vs1", "vs2")},
        suite="base",
        masked=False,
        **kwargs,
    )

    desc = "fflags hardcoded test"
    bin_name = ""

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]
