##################################
# cp_uimm.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_uimm coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import IMMEDIATE_EDGES
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params
from testgen.instructions.vector import get_base_lmul
from testgen.instructions.vector_params import generate_random_vector_params

# Memory data with a distinct byte in every lane, none equal to a byte of the 0xdeadbeef signature fill.
# A load or store that decodes a different offset then produces a different signature.
DISTINCT_BYTES = 0x8877665544332211


@add_coverpoint_generator("cp_uimm")
def make_cp_uimm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for unsigned immediate values."""

    is_vector = False
    lmul = 0

    if coverpoint == "cp_uimm":
        uimm_vals = range(test_data.xlen)
    elif coverpoint.endswith("_5"):
        uimm_vals = range(32)
    elif coverpoint.endswith("_n0"):
        uimm_vals = range(1, test_data.xlen)
    elif coverpoint.endswith("_2"):
        uimm_vals = range(4)  # c.lbu, c.sb byte offsets
    elif coverpoint.endswith("_2h"):
        uimm_vals = range(0, 4, 2)  # c.lh, c.lhu, c.sh halfword offsets
    elif coverpoint.endswith("_6bit_v"):
        is_vector = True
        assert test_data.config.sew is not None, "SEW must be set for vector tests"
        lmul = get_base_lmul(instr_name, instr_type, test_data.config.sew)
        uimm_vals = IMMEDIATE_EDGES.imm_6bit_u  # vror.vi edges
    else:
        raise ValueError(f"Unknown cp_uimm coverpoint variant: {coverpoint} for {instr_name}")

    # Load data (temp_val) and store data (rs2val) for the Zcb offset variants; None leaves them random.
    memval = DISTINCT_BYTES & ((1 << test_data.xlen) - 1) if coverpoint.endswith(("_2", "_2h")) else None

    test_chunks: list[TestChunk] = []
    for uimm in uimm_vals:
        if is_vector:
            params = generate_random_vector_params(test_data, instr_name, instr_type, lmul=lmul, immval=uimm)
        else:
            params = generate_random_params(test_data, instr_type, immval=uimm, temp_val=memval, rs2val=memval)
        desc = f"{coverpoint}: imm={uimm}"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, f"uimm{uimm}", coverpoint)
        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
