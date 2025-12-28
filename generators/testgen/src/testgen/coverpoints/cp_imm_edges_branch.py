##################################
# cp_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges coverpoint generators."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import load_int_reg, return_test_regs, write_sigupd
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_imm_edges_branch")
def make_cp_imm_edges_branch(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for branch immediate edge values."""
    test_data.add_testcase_string(coverpoint)
    test_lines: list[str] = ["\n# Testcase cp_imm_edges_branch"]
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rs1 is not None and params.rs2 is not None and params.temp_reg is not None
    test_lines.extend(
        [
            load_int_reg("branch check value", params.temp_reg, 4096, test_data),
            f"LI(x{params.rs1}, 1)",
            f"LI(x{params.rs2}, {1 if instr_name in ['beq', 'bge', 'bgeu'] else 2}) # setup for taken branch",
            "",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 1f # branch forward by 4",
            "# offset too small to modify counter for checking",
            "1: nop",
            "",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 2f # branch forward by 8",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # shouldn't happen",
            f"2: addi x{params.temp_reg}, x{params.temp_reg}, 4 # should happen",
            "",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 3f # branch forward by 16",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -8 # shouldn't happen",
            "j 19f # shouldn't happen",
            "nop # use up 4 bytes",
            f"3: addi x{params.temp_reg}, x{params.temp_reg}, 16 # should happen",
            "",
            ".align 11 # align to 2048 bytes",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 4f # branch forward by 2048",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -32 # shouldn't happen",
            "j 19f # shouldn't happen",
            ".align 11 # align to 2048 bytes",
            f"4: addi x{params.temp_reg}, x{params.temp_reg}, 64 # should happen",
            "",
            ".align 12 # align to 4096 bytes",
            "nop # use up 4 bytes",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 5f # branch forward by 4092",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -128 # shouldn't happen",
            "j 19f # shouldn't happen",
            ".align 12 # align to 4096 bytes",
            f"5: addi x{params.temp_reg}, x{params.temp_reg}, 256 # should happen",
            "",
            "j 7f # jump around to test backward branch",
            "6: j 9f # backward branch succeeded",
            "# offset too small to modify counter for checking",
            f"7: {instr_name} x{params.rs1}, x{params.rs2}, 6b # backward branch by -4",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -512 # shouldn't happen",
            "j 19f # shouldn't happen",
            "",
            f"8: addi x{params.temp_reg}, x{params.temp_reg}, 1024 # should happen",
            "j 11f # backward branch succeeded",
            f"9: {instr_name} x{params.rs1}, x{params.rs2}, 8b # backward branch by -8",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -2048 # shouldn't happen",
            "j 19f # shouldn't happen",
            "",
            ".align 12 # align to 4096 bytes",
            f"10: addi x{params.temp_reg}, x{params.temp_reg}, 1 # should happen",
            "j 20f # backward branch succeeded",
            ".align 12 # align to 4096 bytes",
            f"11: .insn {encode_branch(instr_name, params.rs1, params.rs2, 4096):#x} # {instr_name} x{params.rs1}, x{params.rs2}, -4096; GCC is turning this into a small branch and a jump",
            f"addi x{params.temp_reg}, x{params.temp_reg}, 300 # shouldn't happen",
            "j 19f # shouldn't happen",
            "",
            f"19: li x{params.temp_reg}, -1 # Shouldn't reach here, write failure code",
            "20: # end of branches",
            write_sigupd(params.temp_reg, test_data),
        ]
    )
    return_test_regs(test_data, params)
    return test_lines


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
