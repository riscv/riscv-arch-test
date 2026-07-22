##################################
# cp_regs.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Register coverpoint handlers (cp_rd, cp_rs1, cp_rs2)"""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import get_base_lmul
from testgen.data.random import random_range
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params
from testgen.formatters.vector_params import generate_random_vector_params


def get_zacas_mask(instr_name: str, instr_type: str, test_data: TestData) -> int:
    """Helper function to calculate the correct all_ones bitmask for Zacas and standard instructions."""
    if instr_name.lower().startswith("amocas"):
        instr_lower = instr_name.lower()
        if instr_lower.endswith(".b"):
            bits = 8
        elif instr_lower.endswith(".h"):
            bits = 16
        elif instr_lower.endswith(".w"):
            bits = 32
        elif instr_lower.endswith(".d"):
            bits = 64
        elif instr_lower.endswith(".q"):
            bits = 128
        else:
            bits = test_data.xlen
        return (1 << bits) - 1
    else:
        val_is_pair = instr_type == "AP"
        return (1 << (2 * test_data.xlen)) - 1 if val_is_pair else (1 << test_data.xlen) - 1


@add_coverpoint_generator("cp_rd")
def make_rd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for destination register coverpoints covering both matching and non-matching states."""
    reg_is_pair = False
    if coverpoint == "cp_rd":
        rd_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith("_nx0"):
        rd_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("rd_p"):
        rd_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_pair"):
        rd_regs = list(range(0, test_data.int_regs.reg_count, 2))  # Only even registers
        reg_is_pair = True
    else:
        raise ValueError(f"Unknown cp_rd coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    is_zacas = instr_name.lower().startswith("amocas")
    equal_cases = [True, False] if is_zacas else [None]
    all_ones = get_zacas_mask(instr_name, instr_type, test_data)

    is_vector = instr_name.lower().startswith("v")
    if is_vector:
        assert test_data.config.sew is not None, "SEW must be set for vector tests"
        lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    else:
        lmul = 1  # Placeholder to keep the type-checker happy

    # Generate both matching and non-matching tests for every register
    for rd in rd_regs:
        for equal_case in equal_cases:
            if reg_is_pair:
                asm_setup = test_data.int_regs.consume_register_pair(rd)
            else:
                asm_setup = test_data.int_regs.consume_registers([rd])

            if is_zacas:
                rd_val = random_range(0, all_ones)
                rs2_val = random_range(0, all_ones)

                if equal_case:
                    rs1_val = rd_val
                    case_desc = "matching (rd_val == mem_val)"
                    bin_suffix = "equal"
                else:
                    rs1_val = random_range(0, all_ones)
                    while rs1_val == rd_val:
                        rs1_val = random_range(0, all_ones)
                    case_desc = "non-matching (rd_val != mem_val)"
                    bin_suffix = "not_equal"

                params = generate_random_params(
                    test_data, instr_type, rd=rd, rdval=rd_val, rs1val=rs1_val, rs2val=rs2_val
                )
                params.rdval = rd_val
                params.rs1val = rs1_val
                params.rs2val = rs2_val

                desc = f"{coverpoint} (Test destination rd = x{rd}, {case_desc})"
                bin_name = f"b{rd}_{bin_suffix}"
            else:
                if is_vector:
                    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, rd=rd)
                else:
                    params = generate_random_params(test_data, instr_type, rd=rd)
                desc = f"{coverpoint} (Test destination rd = x{rd})"
                bin_name = f"b{rd}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            if asm_setup:
                tc.code.insert(0, asm_setup)
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_rs1")
def make_rs1(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for source register 1 coverpoints covering both matching and non-matching states."""
    reg_is_pair = False
    if coverpoint == "cp_rs1":
        rs1_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith(("_nx0", "_nx0_pair")):
        rs1_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("_nx2"):
        rs1_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
        rs1_regs.remove(2)  # Exclude x2
    elif coverpoint.endswith("_p"):
        rs1_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_pair"):
        rs1_regs = list(range(0, test_data.int_regs.reg_count, 2))  # Only even registers
        reg_is_pair = True
    else:
        raise ValueError(f"Unknown cp_rs1 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    is_zacas = instr_name.lower().startswith("amocas")
    equal_cases = [True, False] if is_zacas else [None]
    all_ones = get_zacas_mask(instr_name, instr_type, test_data)

    is_vector = instr_name.lower().startswith("v")
    if is_vector:
        assert test_data.config.sew is not None, "SEW must be set for vector tests"
        lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
    else:
        lmul = 1  # Placeholder to keep the type-checker happy

    for rs1 in rs1_regs:
        for equal_case in equal_cases:
            if reg_is_pair:
                asm_setup = test_data.int_regs.consume_register_pair(rs1)
            else:
                asm_setup = test_data.int_regs.consume_registers([rs1])

            if is_zacas:
                rd_val = random_range(0, all_ones)
                rs2_val = random_range(0, all_ones)

                if equal_case:
                    rs1_val = rd_val
                    case_desc = "matching (rd_val == mem_val)"
                    bin_suffix = "equal"
                else:
                    rs1_val = random_range(0, all_ones)
                    while rs1_val == rd_val:
                        rs1_val = random_range(0, all_ones)
                    case_desc = "non-matching (rd_val != mem_val)"
                    bin_suffix = "not_equal"

                params = generate_random_params(
                    test_data, instr_type, rs1=rs1, rdval=rd_val, rs1val=rs1_val, rs2val=rs2_val
                )
                params.rdval = rd_val
                params.rs1val = rs1_val
                params.rs2val = rs2_val

                desc = f"{coverpoint} (Test source rs1 = x{rs1}, {case_desc})"
                bin_name = f"b{rs1}_{bin_suffix}"
            else:
                if is_vector:
                    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, rs1=rs1)
                else:
                    params = generate_random_params(test_data, instr_type, rs1=rs1)
                desc = f"{coverpoint} (Test source rs1 = x{rs1})"
                bin_name = f"b{rs1}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            if asm_setup:
                tc.code.insert(0, asm_setup)
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_rs2")
def make_rs2(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for source register 2 coverpoints covering both matching and non-matching states."""
    reg_is_pair = False
    if coverpoint == "cp_rs2":
        rs2_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith("_nx0"):
        rs2_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("_p"):
        rs2_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    elif coverpoint.endswith("_pair"):
        rs2_regs = list(range(0, test_data.int_regs.reg_count, 2))  # Only even registers
        reg_is_pair = True
    else:
        raise ValueError(f"Unknown cp_rs2 coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []

    is_zacas = instr_name.lower().startswith("amocas")
    equal_cases = [True, False] if is_zacas else [None]
    all_ones = get_zacas_mask(instr_name, instr_type, test_data)

    for rs2 in rs2_regs:
        for equal_case in equal_cases:
            if reg_is_pair:
                asm_setup = test_data.int_regs.consume_register_pair(rs2)
            else:
                asm_setup = test_data.int_regs.consume_registers([rs2])

            if is_zacas:
                rd_val = random_range(0, all_ones)
                rs2_val = random_range(0, all_ones)

                if equal_case:
                    rs1_val = rd_val
                    case_desc = "matching (rd_val == mem_val)"
                    bin_suffix = "equal"
                else:
                    rs1_val = random_range(0, all_ones)
                    while rs1_val == rd_val:
                        rs1_val = random_range(0, all_ones)
                    case_desc = "non-matching (rd_val != mem_val)"
                    bin_suffix = "not_equal"

                params = generate_random_params(
                    test_data, instr_type, rs2=rs2, rdval=rd_val, rs1val=rs1_val, rs2val=rs2_val
                )
                params.rdval = rd_val
                params.rs1val = rs1_val
                params.rs2val = rs2_val

                desc = f"{coverpoint} (Test source rs2 = x{rs2}, {case_desc})"
                bin_name = f"b{rs2}_{bin_suffix}"
            else:
                params = generate_random_params(test_data, instr_type, rs2=rs2)
                desc = f"{coverpoint} (Test source rs2 = x{rs2})"
                bin_name = f"b{rs2}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            if asm_setup:
                tc.code.insert(0, asm_setup)
            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks
