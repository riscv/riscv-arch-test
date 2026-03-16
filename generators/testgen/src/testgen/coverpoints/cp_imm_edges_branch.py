##################################
# cp_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges coverpoint generators."""

from testgen.asm.helpers import load_int_reg, return_test_regs, write_sigupd
from testgen.constants import INDENT
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.testcase import TestCase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_imm_edges_branch")
def make_cp_imm_edges_branch(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestCase]:
    """Generate tests for branch immediate edge values."""
    tc = test_data.begin_testcase()
    test_lines: list[str] = []
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rs1 is not None and params.rs2 is not None and params.temp_reg is not None
    test_lines.extend(
        [
            load_int_reg("branch check value", params.temp_reg, 4096, test_data),
            f"LI(x{params.rs1}, 1)",
            f"LI(x{params.rs2}, {1 if instr_name in ['beq', 'bge', 'bgeu'] else 2}) # setup for taken branch",
            "",
            test_data.add_testcase("all", coverpoint),
            "",
            "# branch forward by 4",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 1f",
            f"{INDENT}# offset too small to modify counter for checking",
            "1:",
            "nop",
            "",
            "# branch forward by 8",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 2f",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # shouldn't happen",
            "2:",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 4 # should happen",
            "",
            "# branch forward by 16",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 3f",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -8 # shouldn't happen",
            "j 19f # shouldn't happen",
            "nop # use up 4 bytes",
            "3:",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 16 # should happen",
            "",
            "# branch forward by 2048",
            ".align 11 # align to 2048 bytes",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 4f",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -32 # shouldn't happen",
            "j 19f # shouldn't happen",
            ".align 11 # align to 2048 bytes",
            "4:",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 64 # should happen",
            "",
            "# branch forward by 4092",
            ".align 12 # align to 4096 bytes",
            "nop # use up 4 bytes",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 5f",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -128 # shouldn't happen",
            "j 19f # shouldn't happen",
            ".align 12 # align to 4096 bytes",
            "5:",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 256 # should happen",
            "",
            "# backward branch by -4",
            "j 7f # jump around to test backward branch",
            "6:",
            "j 9f # backward branch succeeded",
            f"{INDENT}# offset too small to modify counter for checking",
            "7:",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 6b",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -512 # shouldn't happen",
            "j 19f # shouldn't happen",
            "",
            "# backward branch by -8",
            "8:",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 1024 # should happen",
            "j 11f # backward branch succeeded",
            "9:",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 8b",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -2048 # shouldn't happen",
            "j 19f # shouldn't happen",
            "",
            "# backward branch by 4096",
            ".align 12 # align to 4096 bytes",
            "10:",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 1 # should happen",
            "j 20f # backward branch succeeded",
            ".align 12 # align to 4096 bytes",
            "11:",
            f".insn {encode_branch(instr_name, params.rs1, params.rs2, 4096):#x} # {instr_name} x{params.rs1}, x{params.rs2}, -4096; GCC is turning this into a small branch and a jump",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 300 # shouldn't happen",
            "j 19f # shouldn't happen",
            "",
            "# Shouldn't reach here, write failure code",
            "19:",
            f"LI(x{params.temp_reg}, -1)",
            "",
            "# end of branches",
            "20:",
            "",
            write_sigupd(params.temp_reg, test_data),
        ]
    )
    return_test_regs(test_data, params)
    tc.code = "\n".join(test_lines)
    return [test_data.end_testcase()]


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
