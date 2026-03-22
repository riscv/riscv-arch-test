##################################
# cp_custom_fence.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_fence coverpoint generator."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.testcase import TestCase


@add_coverpoint_generator("cp_custom_fence")
def make_custom_fence(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestCase]:
    """Generate tests for fence coverpoints."""
    if instr_name != "fence":
        raise ValueError(f"cp_custom_fence generator only supports fence instruction, got {instr_name}")

    tc = test_data.begin_testcase()
    # Regular fences
    test_lines = [
        "# Testcase cp_custom_fence (regular fences)",
        test_data.add_testcase("fence", "cp_custom_fence"),
        "fence",
        test_data.add_testcase("fence_rw_rw", "cp_custom_fence"),
        "fence rw, rw",
        "",
    ]

    # fence.tso
    test_lines.extend(
        [
            "# Testcase cp_custom_fence (fence.tso)",
            test_data.add_testcase("fence_tso_rw_rw", "cp_custom_fence"),
            "fence.tso",
            "",
        ]
    )

    # Reserved fence encodings
    test_lines.extend(
        [
            "# Testcase cp_custom_fence (reserved fence encodings)",
            test_data.add_testcase("reserved_fences", "cp_custom_fence"),
            ".word 0x0331000f    # fence with nonzero rs1 behaves normally",
            ".word 0x0330008f    # fence with nonzero rd  behaves normally",
            ".word 0x1330000f    # fence with reserved fm behaves as fence with fm = 0000",
            ".word 0x8110000f    # fence.TSO with R,R rather than RW, RW behaves as fence",
            "",
            "# Testcase cp_custom_fence (hint fence encodings)",
            test_data.add_testcase("hint_fences", "cp_custom_fence"),
            ".word 0x0031000f    # fence with rd = x0, rs1 != x0, fm = 0, pred = 0 is a hint",
            ".word 0x0301000f    # fence with rd = x0, rs1 != x0, fm = 0, succ = 0 is a hint",
            ".word 0x0030008f    # fence with rd != x0, rs1 = x0, fm = 0, pred = 0 is a hint",
            ".word 0x0300008f    # fence with rd != x0, rs1 = x0, fm = 0, succ = 0 is a hint",
            ".word 0x0020000f    # fence with rd = x0, rs1 = x0, fm = 0, pred = 0, succ != 0 is a hint",
            ".word 0x0200000f    # fence with rd = x0, rs1 = x0, fm = 0, pred != W, succ = 0 is a hint",
        ]
    )

    tc.code = "\n".join(test_lines)
    return [test_data.end_testcase()]
