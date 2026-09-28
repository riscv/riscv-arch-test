##################################
# cp_imm_edges_branch.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges_branch coverpoint generator."""

from testgen.asm.helpers import write_sigupd
from testgen.constants import INDENT
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cp_imm_edges_branch")
def make_cp_imm_edges_branch(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for branch immediate edge values, one testcase per bin.

    Each taken branch skips a failure code, so the signature records whether the branch was taken.
    """
    tc = test_data.begin_test_chunk()
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rs1 is not None and params.rs2 is not None and params.temp_reg is not None
    rs1, rs2, check = params.rs1, params.rs2, params.temp_reg
    branch = f"{instr_name} x{rs1}, x{rs2}"
    tc.code.extend(
        [
            f"LI(x{rs1}, 1)",
            f"LI(x{rs2}, {1 if instr_name in ['beq', 'bge', 'bgeu'] else 2}) # setup for taken branch",
        ]
    )

    # Forward branches: the branch and its target are on consecutive 2^align boundaries.
    # The failure code and alignment padding lie between them.
    for offset, align in [(4, 2), (8, 3), (16, 4), (2048, 11), (4092, 12)]:
        bin_name = f"b_{offset}"
        tc.code.extend(
            [
                "",
                f"# {coverpoint}: branch forward by {offset}",
                f"LI(x{check}, 1) # success code",
                f".p2align {align}",
                *(["nop # start the branch 4 bytes after the boundary"] if offset == 4092 else []),
                test_data.add_testcase(bin_name, coverpoint),
                f"{branch}, 1f",
                f"LI(x{check}, 7) # failure code" if offset > 4 else f"{INDENT}# offset too small for failure code",
                f".p2align {align}",
                "1:",
                write_sigupd(check, test_data),
            ]
        )

    # Backward branches: jump past the target, branch back to it, and have the target skip the failure code.
    for offset, bin_name in [(4, "b_m4"), (8, "b_m8"), (4096, "b_m4096")]:
        if offset == 4096:
            target_align, source_align = [".p2align 12"], [".p2align 12"]
            # GCC turns a -4096 branch into a short branch and a jump, so encode it directly
            source = f".insn {encode_branch(instr_name, rs1, rs2, -4096):#x} # {branch}, -4096"
        else:
            target_align, source_align = [], []
            source = f"{branch}, 2b"
        tc.code.extend(
            [
                "",
                f"# {coverpoint}: branch backward by {offset}",
                f"LI(x{check}, 1) # success code",
                "j 3f # jump past backward branch target",
                *target_align,
                "2:",
                "j 4f # backward branch taken",
                *(["nop # offset 8"] if offset == 8 else []),
                *source_align,
                "3:",
                test_data.add_testcase(bin_name, coverpoint),
                source,
                f"LI(x{check}, 7) # failure code",
                "4:",
                write_sigupd(check, test_data),
            ]
        )

    return_testcase_registers(test_data, params)
    return [test_data.end_test_chunk()]


def encode_branch(instr_name: str, rs1: int, rs2: int, imm: int) -> int:
    """Encode a branch instruction with given parameters."""
    funct3_dict = {
        "beq": 0b000,
        "bne": 0b001,
        "blt": 0b100,
        "bge": 0b101,
        "bltu": 0b110,
        "bgeu": 0b111,
    }
    funct3 = funct3_dict[instr_name]
    opcode = 0b1100011

    imm12 = (imm >> 12) & 0x1
    imm10_5 = (imm >> 5) & 0x3F
    imm4_1 = (imm >> 1) & 0xF
    imm11 = (imm >> 11) & 0x1

    encoded = (
        (imm12 << 31)
        | (imm11 << 7)
        | (imm10_5 << 25)
        | (imm4_1 << 8)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | opcode
    )
    return encoded
