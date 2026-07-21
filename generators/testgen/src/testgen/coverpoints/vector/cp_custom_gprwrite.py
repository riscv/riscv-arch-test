##################################
# cp_custom_gprwrite.py
#
# Tests for vector instructions that write to a GPR (vcpop.m, vfirst.m,
# vmv.x.s).  The edge case exercised here is vstart == vl == 0: with no active
# elements the instruction must return 0 (vcpop.m) or -1 (vfirst.m) rather
# than a stale register value.
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_gprWriting_vstart_eq_vl")
def make_gpr_writing_vstart_eq_vl(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Generates a test for instructions writing to GPRs, ensure that at even vl = 0 (where vstart = vl), the
    instruction still executes correctly.
    """
    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=1, suite="length", vl=0, vstart=0)
    desc = "cp_custom_gprWriting_vstart_eq_vl (vstart=vl=0)"
    bin_name = "cp_custom_gprWriting_vstart_eq_vl"
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_test_regs(test_data, params)
    return [tc]
