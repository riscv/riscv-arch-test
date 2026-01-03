##################################
# cp_custom_fence_i.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_fence_i coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import load_int_reg, write_sigupd


def encode_addi(rd: int, rs1: int, imm: int) -> int:
    """Encode addi instruction."""
    return (imm << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x13


@add_coverpoint_generator("cp_custom_fencei")
def make_custom_fence_i(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for fence.i coverpoints."""
    if instr_name != "fence.i":
        raise ValueError(f"cp_custom_fencei generator only supports fence.i instruction, got {instr_name}")

    test_lines: list[str] = []

    cases = [
        ("normal fence.i", "fence.i", 5),
        ("fence.i with nonzero rs1", ".insn 0x0001100f", 7),
        ("fence.i with nonzero rd", ".insn 0x0000108f", 9),
        ("fence.i with nonzero funct12", ".insn 0x0010100f", 13),
    ]

    for desc, fence_instr, add_val in cases:
        # Get free registers
        reg1, reg2, reg3 = test_data.int_regs.get_registers(3, exclude_regs=[0])

        label = f"selfmodify_{test_data.test_count}"

        # Calculate encoded instruction: addi reg1, reg1, add_val
        encoded_instr = encode_addi(reg1, reg1, add_val)

        test_lines.extend(
            [
                test_data.add_testcase("cp_custom_fencei"),
                f"# Testcase: {desc}",
                f"LI(x{reg1}, 3)",
                f"LA(x{reg3}, {label})",
                load_int_reg(f"addi x{reg1}, x{reg1}, {add_val}", reg2, encoded_instr, test_data),
                f"sw x{reg2}, 0(x{reg3})",
                f"{fence_instr} # {desc}",
                f"{label}:",
                f"addi x{reg1}, x{reg1}, 1 # original code",
                write_sigupd(reg1, test_data),
                "",
            ]
        )

        # Return registers
        test_data.int_regs.return_registers([reg1, reg2, reg3])

    return test_lines
