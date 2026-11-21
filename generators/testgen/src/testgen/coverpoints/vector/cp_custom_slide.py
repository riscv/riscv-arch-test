##################################
# cp_custom_slide.py
#
# Slide tests at vl=VLMAX.
#
# david_harris@hmc.edu November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from typing import Literal

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params

# Slide offsets, as a constant or as an expression in VLMAX that the test computes at run time
SLIDE_OFFSETS: dict[str, int | Literal["vlmax/2", "vlmax-1", "vlmax"]] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "vlmaxd2": "vlmax/2",
    "vlmaxm1": "vlmax-1",
    "vlmax": "vlmax",
}


@add_coverpoint_generator("cp_custom_slideOffsets")
def make_slide_offsets(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Slide a register of random data by 0, 1, 2, VLMAX/2, VLMAX-1, and VLMAX at vl=VLMAX, checking every element.
    """
    test_chunks = []
    for bin_name, offset in SLIDE_OFFSETS.items():
        # Keep the exact offset, rather than reducing it to [0, 2*VLMAX)
        rs1val, rs1val_vlmax = (offset, None) if isinstance(offset, int) else (0, offset)

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=1,
            suite="length",
            vl="vlmax",
            ignore_vector_safety=True,
            rs1val=rs1val,
            rs1val_vlmax=rs1val_vlmax,
        )

        desc = f"{coverpoint} (Test slide offset = {offset} at vl = VLMAX)"
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks
