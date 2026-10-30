##################################
# cp_custom_amo_aqrl.py
#
# david_harris@hmc.edu Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_amo_aqrl coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cp_custom_amo_aqrl")
def make_custom_amo_aqrl(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for the acquire/release ordering bits of atomic memory operations."""
    if instr_type not in ("A", "AP"):
        raise ValueError(
            f"cp_custom_amo_aqrl coverpoint generator only supports A and AP-type instructions, "
            f"got {instr_type} for {instr_name}."
        )

    test_chunks: list[TestChunk] = []
    # All four orderings are legal on an AMO, unlike LR (no rl without aq) and SC (no aq without rl)
    for suffix in ["", ".aq", ".rl", ".aqrl"]:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
        desc = f"cp_custom_aqrl (ordering suffix = '{suffix}')"
        test_chunks.append(
            format_single_testcase(
                f"{instr_name}{suffix}", instr_type, test_data, params, desc, suffix, "cp_custom_aqrl"
            )
        )
        return_testcase_registers(test_data, params)

    return test_chunks
