##################################
# cp_memval.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_memval coverpoint generator."""

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import MEMORY_EDGES
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_memval")
def make_memval(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for memory value edge cases."""
    if coverpoint == "cp_memval_byte":
        memvals = MEMORY_EDGES.byte
    elif coverpoint == "cp_memval_hword":
        memvals = MEMORY_EDGES.hword
    elif coverpoint == "cp_memval_word":
        memvals = MEMORY_EDGES.word
    elif coverpoint == "cp_memval_double":
        memvals = MEMORY_EDGES.double
    else:
        raise ValueError(f"Unknown cp_memval coverpoint variant: {coverpoint} for {instr_name}")

    test_chunks: list[TestChunk] = []
    for val in memvals:
        if instr_type == "S":
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], rs2val=val)
        elif instr_type == "L":
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], temp_val=val)
        else:
            raise ValueError(f"cp_memval coverpoint not supported for instruction type: {instr_type} in {instr_name}")
        desc = f"{coverpoint} (memory value = {val:#x})"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{val:#x}", coverpoint)
        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
