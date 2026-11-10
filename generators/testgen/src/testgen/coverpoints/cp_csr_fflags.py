# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0

"""Floating-point flags coverpoint generator."""

from typing import Any

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews, make_and_register_edge_label
from testgen.data.edges import get_vector_edge
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction, format_single_testcase, get_instruction_type_config
from testgen.instructions.params import generate_random_params
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params

_FLAG_BITS = {"v": 0b10000, "d": 0b01000, "o": 0b00100, "u": 0b00010, "n": 0b00001}


@add_coverpoint_generator("cp_csr_fflags")
def make_fflags(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests with the applicable bit in fflags already set, and reach flags configurations otherwise not exercised"""

    test_chunks = []

    # This must come first due to how fflags is handled in the sail trace (otherwise coverage sees another 1->1 transition)
    if instr_name in [
        "vfmacc.vf",
        "vfnmacc.vf",
        "vfmsac.vf",
        "vfnmsac.vf",
        "vfmacc.vv",
        "vfmsac.vv",
        "vfnmacc.vv",
        "vfnmsac.vv",
        "vfwmaccbf16.vf",
        "vfwmaccbf16.vv",
    ]:
        # Some vector tests do not hit the underflow flag naturally
        test_chunks.extend(generate_vector_special_cases(instr_name, instr_type, coverpoint, test_data))

    test_chunks.extend(generate_preset_fflags_tests(instr_name, instr_type, coverpoint, test_data))

    return test_chunks


def generate_preset_fflags_tests(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate tests with each applicable fflags bit already set."""
    if get_instruction_type_config(instr_type).vector_data is not None:
        # Then we are a vector test
        sews, coverpoint = extract_coverpoint_sews(coverpoint)
    else:
        sews = [None]

    suffix = coverpoint.removeprefix("cp_csr_fflags_")
    if not suffix or any(flag not in _FLAG_BITS for flag in suffix):
        raise ValueError(f"Unknown cp_csr_fflags coverpoint variant: {coverpoint} for {instr_name}")

    fflags = sum(_FLAG_BITS[flag] for flag in suffix)
    test_chunks: list[TestChunk] = []
    for sew in sews:
        if sew is not None:
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul=get_base_lmul(instr_name, instr_type, sew), sew=sew
            )
        else:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0])

        tc = test_data.begin_test_chunk()
        sew_desc = f", sew={sew}" if sew is not None else ""
        sew_bin = f"_sew{sew}" if sew is not None else ""
        tc.code.append(f"# Testcase {coverpoint} (fflags = {fflags:05b}{sew_desc})")
        label = test_data.add_testcase(f"b{fflags:05b}{sew_bin}", coverpoint)
        setup, test, check = format_instruction(instr_name, instr_type, test_data, params)
        if setup:
            tc.code.append(setup)
        tc.code.extend([f"csrsi fcsr, 0b{fflags:05b} # set fflags", label, test])
        if check:
            tc.code.append(check)

        test_chunk = test_data.end_test_chunk()
        return_testcase_registers(test_data, params)
        test_chunks.append(test_chunk)

    return test_chunks


def generate_vector_special_cases(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generates a test hitting UF for the vector tests in need of it"""
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks: list[TestChunk] = []
    for sew in sews:
        kwargs: dict[str, Any] = {}

        if instr_name in ["vfwmaccbf16.vf", "vfwmaccbf16.vv"]:
            vs2_label = make_and_register_edge_label("vs2", "min_subnorm", "f_bf16", test_data, sew)
            vd_label = make_and_register_edge_label("vd", "pos0", "f", test_data, sew * 2)

            kwargs = {
                "vs2_val_pointer": vs2_label,
                "vd_val_pointer": vd_label,
            }

            if instr_name.endswith("vv"):
                kwargs["vs1_val_pointer"] = make_and_register_edge_label("vs1", "min_subnorm", "f_bf16", test_data, sew)
            else:
                kwargs["fs1val"] = get_vector_edge("min_subnorm", "f_bf16", sew)
        elif instr_name.endswith("vf"):
            # Only is verified to work for variants of vmacc-style instructions
            vs2_label = make_and_register_edge_label("vs2", "min_subnorm", "f", test_data, sew)
            vd_label = make_and_register_edge_label("vd", "pos0", "f", test_data, sew)
            fs1_val = get_vector_edge("min_subnorm", "f", sew)

            kwargs = {
                "vs2_val_pointer": vs2_label,
                "vd_val_pointer": vd_label,
                "fs1val": fs1_val,
            }
        elif instr_name.endswith("vv"):
            # Only is verified to work for variants of vmacc-style instructions
            vs2_label = make_and_register_edge_label("vs2", "min_subnorm", "f", test_data, sew)
            vs1_label = make_and_register_edge_label("vs1", "min_subnorm", "f", test_data, sew)
            vd_label = make_and_register_edge_label("vd", "pos0", "f", test_data, sew)

            kwargs = {
                "vs2_val_pointer": vs2_label,
                "vs1_val_pointer": vs1_label,
                "vd_val_pointer": vd_label,
            }
        else:
            raise ValueError(f"Unsupported vector special case for cp_csr_fflags: {instr_name}")

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            get_base_lmul(instr_name, instr_type, sew),
            sew=sew,
            additional_no_overlap={("vd", "vs1"), ("vd", "vs2"), ("vs1", "vs2")},
            suite="base",
            masked=False,
            **kwargs,
        )

        desc = f"fflags hardcoded test (sew={sew})"
        bin_name = f"underflow_sew{sew}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks
