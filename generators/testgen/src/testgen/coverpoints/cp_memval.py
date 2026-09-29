##################################
# cp_memval.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_memval coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import FLOAT_EDGES, MEMORY_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cp_memval")
def make_memval(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for memory value edge cases."""
    memvals = {
        "cp_memval_byte": MEMORY_EDGES.byte,
        "cp_memval_hword": MEMORY_EDGES.hword,
        "cp_memval_word": MEMORY_EDGES.word,
        "cp_memval_double": MEMORY_EDGES.double,
        "cp_memval_fp_single": FLOAT_EDGES.single,
        "cp_memval_fp_half": FLOAT_EDGES.half,
        "cp_memval_fp_double": FLOAT_EDGES.double,
    }[coverpoint]
    test_chunks: list[TestChunk] = []
    for val in memvals:
        if instr_type in {"FL", "CFL", "CFLS"}:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], temp_fval=val)
            value = test_data.flen_format_str.format(val)
        elif instr_type in {"L", "CL", "CILS"}:
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], temp_val=val)
            value = f"{val:#x}"
        elif instr_type == "A":
            # For AMOs, rs1val holds the value written to memory before the operation
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=val)
            value = f"{val:#x}"
        else:
            raise ValueError(f"cp_memval is not supported for instruction type: {instr_type} in {instr_name}")

        desc = f"{coverpoint} (memory value = {value})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{val:#x}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_memval_rs2_minmax")
def make_memval_rs2_minmax(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Pair the most negative and most positive memory and rs2 values for AMO min/max instructions."""
    if instr_type != "A":
        raise ValueError(f"cr_memval_rs2_minmax only supports A-type instructions, got {instr_type} for {instr_name}")
    width = {"cr_memval_rs2_minmax_word": 32, "cr_memval_rs2_minmax_double": 64}[coverpoint]
    int_min = 1 << (width - 1)
    int_max = int_min - 1
    # rs2 is sign-extended to XLEN so a W-form AMO on RV64 sees a well-formed word operand
    rs2_min = int_min | (((1 << test_data.xlen) - 1) ^ ((1 << width) - 1))
    test_chunks: list[TestChunk] = []
    for bin_name, memval, rs2val in (("mem_min_rs2_max", int_min, int_max), ("mem_max_rs2_min", int_max, rs2_min)):
        # For AMOs, rs1val holds the value written to memory before the operation
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs1val=memval, rs2val=rs2val)
        desc = f"{coverpoint} (memory value = {memval:#x}, rs2 = {rs2val:#x})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
