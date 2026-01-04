##################################
# cp_fp_badNB.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Floating point bad NaN-Box value coverpoint generators (cp_fs1_badNB, cp_fs2_badNB, cp_fs3_badNB)."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.common import return_test_regs
from testgen.utils.edges import FLOAT_EDGES
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_fs1_badNB")
def make_fs1_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs1 bad NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        edges = FLOAT_EDGES.bad_NaN_double_single
        load_size = "double"
    elif coverpoint.endswith("D_H"):
        edges = FLOAT_EDGES.bad_NaN_double_half
        load_size = "double"
    elif coverpoint.endswith("S_H"):
        edges = FLOAT_EDGES.bad_NaN_single_half
        load_size = "single"
    else:
        raise ValueError(f"Unsupported coverpoint for fs1 bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    test_lines: list[str] = []
    for edge_val in edges:
        test_lines.append(test_data.add_testcase(coverpoint))
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fs1val=edge_val, fp_load_type=load_size
        )
        desc = f"{coverpoint} (Test source fs1 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs2_badNB")
def make_fs2_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs2 bad NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        edges = FLOAT_EDGES.bad_NaN_double_single
        load_size = "double"
    elif coverpoint.endswith("D_H"):
        edges = FLOAT_EDGES.bad_NaN_double_half
        load_size = "double"
    elif coverpoint.endswith("S_H"):
        edges = FLOAT_EDGES.bad_NaN_single_half
        load_size = "single"
    else:
        raise ValueError(f"Unsupported coverpoint for fs2 bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    test_lines: list[str] = []
    for edge_val in edges:
        test_lines.append(test_data.add_testcase(coverpoint))
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fs2val=edge_val, fp_load_type=load_size
        )
        desc = f"{coverpoint} (Test source fs2 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines


@add_coverpoint_generator("cp_fs3_badNB")
def make_fs3_badNB(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fs3 bad NaN-Box values."""
    if coverpoint.endswith("_D_S"):
        edges = FLOAT_EDGES.bad_NaN_double_single
        load_size = "double"
    elif coverpoint.endswith("D_H"):
        edges = FLOAT_EDGES.bad_NaN_double_half
        load_size = "double"
    elif coverpoint.endswith("S_H"):
        edges = FLOAT_EDGES.bad_NaN_single_half
        load_size = "single"
    else:
        raise ValueError(f"Unsupported coverpoint for fs1 bad NaN-Box tests: {coverpoint} for instr {instr_name}.")

    test_lines: list[str] = []
    for edge_val in edges:
        test_lines.append(test_data.add_testcase(coverpoint))
        params = generate_random_params(
            test_data, instr_type, exclude_regs=[0], fs3val=edge_val, fp_load_type=load_size
        )
        desc = f"{coverpoint} (Test source fs3 value = {test_data.flen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines
