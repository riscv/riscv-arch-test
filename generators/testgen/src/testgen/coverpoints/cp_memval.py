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
        elif instr_type in ("A", "AP"):
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
