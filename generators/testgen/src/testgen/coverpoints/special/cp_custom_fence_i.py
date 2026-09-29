##################################
# cp_custom_fence_i.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_fence_i coverpoint generator."""

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# The coverpoint bins are fixed encodings: nonzero rs1 is x2 and nonzero rd is x1.
FENCEI_RD = 1
FENCEI_RS1 = 2
RD_SENTINEL = "0x5A5A5A5A"
RS1_VALUE = "0x0F0F0F0F"


def encode_addi(rd: int, rs1: int, imm: int) -> int:
    """Encode addi instruction."""
    return (imm << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x13


def encode_fence_i(rd: int = 0, rs1: int = 0, imm: int = 0) -> int:
    """Encode fence.i with the given (reserved) rd, rs1 and imm fields."""
    return (imm << 20) | (rs1 << 15) | (0b001 << 12) | (rd << 7) | 0x0F


@add_coverpoint_generator("cp_custom_fencei")
def make_custom_fence_i(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fence.i coverpoints.

    Each testcase patches the instruction after the fence.i and checks that the patched one runs.
    rd, rs1 and imm are reserved and must be ignored (norm:fence_i_rsv), so the nonzero-rd case
    also checks that rd is not written.
    """
    if instr_name != "fence.i":
        raise ValueError(f"cp_custom_fencei generator only supports fence.i instruction, got {instr_name}")

    tc = test_data.begin_test_chunk()

    # Take x1 and x2 for the fixed encodings; this moves the signature pointer off x2.
    asm = test_data.int_regs.consume_registers([FENCEI_RD, FENCEI_RS1])
    if asm:
        tc.code.append(asm)

    # (bin name, description, fence.i encoding, addi immediate for the patched instruction)
    cases = [
        ("fencei", "normal fence.i", None, 5),
        ("fencei_nonzerors1", "fence.i with nonzero rs1", encode_fence_i(rs1=FENCEI_RS1), 7),
        ("fencei_nonzerord", "fence.i with nonzero rd", encode_fence_i(rd=FENCEI_RD), 9),
        ("fencei_nonzerof12", "fence.i with nonzero funct12", encode_fence_i(imm=1), 13),
    ]

    for bin_name, desc, fence_encoding, add_val in cases:
        # Get free registers
        reg1, reg2, reg3 = test_data.int_regs.get_registers(3, exclude_regs=[0])

        label = f"selfmodify_{test_data.test_count}"

        # Calculate encoded instruction: addi reg1, reg1, add_val
        encoded_instr = encode_addi(reg1, reg1, add_val)
        fence_instr = "fence.i" if fence_encoding is None else f".insn {fence_encoding:#010x}"

        tc.code.append(f"# Testcase {bin_name}: {desc}")
        if bin_name == "fencei_nonzerors1":
            tc.code.append(f"LI(x{FENCEI_RS1}, {RS1_VALUE}) # nonzero value in the ignored rs1")
        if bin_name == "fencei_nonzerord":
            tc.code.append(f"LI(x{FENCEI_RD}, {RD_SENTINEL}) # fence.i must not write the ignored rd")
        tc.code.extend(
            [
                f"LI(x{reg1}, 3)",
                f"LA(x{reg3}, {label})",
                load_int_reg(f"addi x{reg1}, x{reg1}, {add_val}", reg2, encoded_instr, test_data),
                f"sw x{reg2}, 0(x{reg3})",
                test_data.add_testcase(bin_name, "cp_custom_fencei"),
                f"{fence_instr} # {desc}",
                f"{label}:",
                f"addi x{reg1}, x{reg1}, 1 # original code",
                write_sigupd(reg1, test_data),
            ]
        )
        if bin_name == "fencei_nonzerord":
            tc.code.append(write_sigupd(FENCEI_RD, test_data))
        tc.code.append("")

        # Return registers
        test_data.int_regs.return_registers([reg1, reg2, reg3])

    test_data.int_regs.return_registers([FENCEI_RD, FENCEI_RS1])
    return [test_data.end_test_chunk()]
