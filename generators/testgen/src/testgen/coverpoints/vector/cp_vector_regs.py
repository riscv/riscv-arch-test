##################################
# cp_vector_regs.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import re

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import guard_element_group_vlen
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector import get_base_lmul, get_element_group_register_lmul
from testgen.instructions.vector_params import generate_random_vector_params


def _get_element_group_size(coverpoint: str) -> int:
    match = re.search(r"egs(\d+)", coverpoint)
    return int(match.group(1)) if match is not None else 1


@add_coverpoint_generator("cp_vs2")
def make_vs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests for all valid registers for vs2.
    """

    assert test_data.config.sew is not None, "SEW Must be set for vector instruction"

    lower_limit, upper_limit = 0, test_data.vec_regs.reg_count
    emul = 1
    if coverpoint.startswith("cp_vs2_"):
        suffix = coverpoint[len("cp_vs2_") :]

        if suffix == "nv0":
            lower_limit = 1
        elif suffix.startswith("emul"):
            emul = int(suffix[len("emul") :])
    base_lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    egs = _get_element_group_size(coverpoint)

    test_chunks = []
    for v in range(lower_limit, upper_limit, emul):
        lmul = get_element_group_register_lmul(v, egs) if egs != 1 else base_lmul
        test_data.vec_regs.allocate_operand("vs2", v, int(max(lmul, 1)))
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, egs=egs, vl=egs, vs2=v
        )

        desc = f"cp_vs2 (Test source vs2 = v{v})"
        bin_name = f"cp_vs2_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        guard_element_group_vlen(tc, test_data.config.sew, egs, lmul)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vs1")
def make_vs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests for all valid registers for vs1.
    """

    assert test_data.config.sew is not None, "SEW Must be set for vector instruction"

    lower_limit, upper_limit = 0, test_data.vec_regs.reg_count
    emul = 1
    if coverpoint.startswith("cp_vs1_"):
        suffix = coverpoint[len("cp_vs1_") :]

        if suffix == "nv0":
            lower_limit = 1
        elif suffix.startswith("emul"):
            emul = int(suffix[len("emul") :])
    base_lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    egs = _get_element_group_size(coverpoint)

    test_chunks = []
    for v in range(lower_limit, upper_limit, emul):
        lmul = get_element_group_register_lmul(v, egs) if egs != 1 else base_lmul
        test_data.vec_regs.allocate_operand("vs1", v, int(max(lmul, 1)))
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, egs=egs, vl=egs, vs1=v
        )

        desc = f"cp_vs1 (Test source vs1 = v{v})"
        bin_name = f"cp_vs1_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        guard_element_group_vlen(tc, test_data.config.sew, egs, lmul)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vs3")
def make_vs3(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests for all valid registers for vs3.
    """

    assert test_data.config.sew is not None, "SEW Must be set for vector instruction"

    lower_limit, upper_limit = 0, test_data.vec_regs.reg_count
    emul = 1
    if coverpoint.startswith("cp_vs3_"):
        suffix = coverpoint[len("cp_vs3_") :]

        if suffix.startswith("lte"):
            upper_limit = int(suffix[len("lte") :]) + 1
        elif suffix == "nv0":
            lower_limit = 1
        elif suffix.startswith("emul"):
            emul = int(suffix[len("emul") :])
    base_lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    egs = _get_element_group_size(coverpoint)

    test_chunks = []
    for v in range(lower_limit, upper_limit, emul):
        lmul = get_element_group_register_lmul(v, egs) if egs != 1 else base_lmul
        test_data.vec_regs.allocate_operand("vs3", v, int(max(lmul, 1)))
        params = generate_random_vector_params(
            test_data, instr_name, instr_type, lmul=lmul, egs=egs, vl=egs, vs3=v
        )

        desc = "cp_vd (Test destination vs3 = v" + str(v) + ")"
        bin_name = f"cp_vd_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        guard_element_group_vlen(tc, test_data.config.sew, egs, lmul)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vd")
def make_vd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests for all valid registers for vd.
    """

    assert test_data.config.sew is not None, "SEW Must be set for vector instruction"

    lower_limit, upper_limit = 0, test_data.vec_regs.reg_count
    emul = 1
    if coverpoint.startswith("cp_vd_"):
        suffix = coverpoint[len("cp_vd_") :]

        if suffix.startswith("lte"):
            upper_limit = int(suffix[len("lte") :]) + 1
        elif suffix == "nv0":
            lower_limit = 1
        elif suffix.startswith("emul"):
            emul = int(suffix[len("emul") :])
    base_lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    egs = _get_element_group_size(coverpoint)

    test_chunks = []
    for v in range(lower_limit, upper_limit, emul):
        lmul = get_element_group_register_lmul(v, egs) if egs != 1 else base_lmul
        test_data.vec_regs.allocate_operand("vd", v, int(max(lmul, 1)))
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, egs=egs, vl=egs, vd=v)

        desc = "cp_vd (Test destination vd = v" + str(v) + ")"
        bin_name = f"cp_vd_b{v}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        guard_element_group_vlen(tc, test_data.config.sew, egs, lmul)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
