##################################
# cp_custom_fence.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_fence coverpoint generator."""

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

SENTINEL = "0x5A5A5A5A"

# (bin name, instruction, checks rd)
RESERVED_FENCES = [
    ("fence_nonzerors1", ".word 0x0331000f    # fence with nonzero rs1 behaves normally", False),
    ("fence_nonzerord", ".word 0x0330008f    # fence with nonzero rd behaves normally", True),
    ("fence_fm", ".word 0x1330000f    # fence with reserved fm behaves as fence with fm = 0000", False),
    ("fence_tso_r_r", ".word 0x8110000f    # fence.TSO with R,R rather than RW behaves as fence", False),
]

HINT_FENCES = [
    ("fence_hint0a", ".word 0x0031000f    # fence with rd = x0, rs1 != x0, fm = 0, pred = 0 is a hint", False),
    ("fence_hint0b", ".word 0x0301000f    # fence with rd = x0, rs1 != x0, fm = 0, succ = 0 is a hint", False),
    ("fence_hint1a", ".word 0x0030008f    # fence with rd != x0, rs1 = x0, fm = 0, pred = 0 is a hint", True),
    ("fence_hint1b", ".word 0x0300008f    # fence with rd != x0, rs1 = x0, fm = 0, succ = 0 is a hint", True),
    ("fence_hint2", ".word 0x0020000f    # fence with rd = x0, rs1 = x0, fm = 0, pred = 0, succ != 0 is a hint", False),
    ("fence_hint3", ".word 0x0200000f    # fence with rd = x0, rs1 = x0, fm = 0, pred != W, succ = 0 is a hint", False),
]


def add_fence_tests(cases: list[tuple[str, str, bool]], test_data: TestData) -> list[str]:
    """Add one testcase for each fixed FENCE encoding."""
    lines: list[str] = []
    for bin_name, instruction, checks_rd in cases:
        if checks_rd:
            lines.append(f"LI(x1, {SENTINEL})")
        lines.extend([test_data.add_testcase(bin_name, "cp_custom_fence"), instruction])
        if checks_rd:
            lines.append(write_sigupd(1, test_data))
        lines.append("")
    return lines


def fence_set(bits: int) -> str:
    """Return the IORW mnemonic for a 4-bit FENCE predecessor or successor set."""
    return "".join(c for c, b in zip("iorw", (8, 4, 2, 1)) if bits & b) or "0"


def add_pred_succ_tests(test_data: TestData) -> list[str]:
    """Add one FENCE with fm = 0 and rd = rs1 = x0 for every pred x succ combination.

    Reserved settings execute as a FENCE, and pred = 0 or succ = 0 are HINTs, so none may trap.
    Encoded as .word because the assembler rejects empty sets.
    """
    lines = ["# Testcase cp_custom_fence_pred_succ (all pred x succ with fm = 0, rd = rs1 = x0)"]
    for pred_succ in range(256):
        pred, succ = pred_succ >> 4, pred_succ & 0xF
        lines.extend(
            [
                test_data.add_testcase(f"pred_succ[{pred_succ}]", "cp_custom_fence_pred_succ"),
                f".word {(pred_succ << 20) | 0x0F:#010x}    # pred = {fence_set(pred)}, succ = {fence_set(succ)}",
            ]
        )
    return lines


@add_coverpoint_generator("cp_custom_fence")
def make_custom_fence(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fence coverpoints."""
    if instr_name != "fence":
        raise ValueError(f"cp_custom_fence generator only supports fence instruction, got {instr_name}")

    tc = test_data.begin_test_chunk()
    # Regular fences
    tc.code.extend(
        [
            "# Testcase cp_custom_fence (regular fences)",
            test_data.add_testcase("fence", "cp_custom_fence"),
            "fence",
            test_data.add_testcase("fence_rw_rw", "cp_custom_fence"),
            "fence rw, rw",
            "",
        ]
    )

    # fence.tso
    tc.code.extend(
        [
            "# Testcase cp_custom_fence (fence.tso)",
            test_data.add_testcase("fence_tso_rw_rw", "cp_custom_fence"),
            "fence.tso",
            "",
        ]
    )

    # Fixed encodings use x1 for rd and x2 for rs1.
    asm = test_data.int_regs.consume_registers([1, 2])
    if asm:
        tc.code.append(asm)

    tc.code.append("# Testcase cp_custom_fence (reserved fence encodings)")
    tc.code.extend(add_fence_tests(RESERVED_FENCES, test_data))

    tc.code.append("# Testcase cp_custom_fence (hint fence encodings)")
    tc.code.extend(add_fence_tests(HINT_FENCES, test_data))

    test_data.int_regs.return_registers([1, 2])
    fixed_chunk = test_data.end_test_chunk()

    tc = test_data.begin_test_chunk()
    tc.code.extend(add_pred_succ_tests(test_data))

    return [fixed_chunk, test_data.end_test_chunk()]
