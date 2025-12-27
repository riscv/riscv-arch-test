##################################
# cp_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges coverpoint generators."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import return_test_regs, write_sigupd
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_imm_edges_branch")
def make_cp_imm_edges_branch(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for branch immediate edge values."""
    test_data.add_testcase_string(coverpoint)
    test_lines: list[str] = ["\n# Testcase cp_imm_edges_branch"]
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rs1 is not None and params.rs2 is not None
    # TODO: Improve checking logic. Add `addi` instructions between branches and check counter at the end.
    test_lines.extend(
        [
            f"LI(x{params.rs1}, 1)",
            f"LI(x{params.rs2}, {1 if instr_name in ['beq', 'bge', 'bgeu'] else 2}) # setup for taken branch",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 1f # branch forward by 4",
            f"1: {instr_name} x{params.rs1}, x{params.rs2}, 2f # branch forward by 8",
            "j 19f # shouldn't happen",
            f"2: {instr_name} x{params.rs1}, x{params.rs2}, 3f # branch forward by 16",
            "j 19f # shouldn't happen",
            "nop",
            "nop # shouldn't be executed",
            f"3: LI(x{params.rs1}, 1) # insignificant, just an action before the next align",
            ".align 11 # align to 2048 bytes",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 4f # branch forward by 2048",
            "j 19f # shouldn't happen",
            ".align 11 # align to 2048 bytes",
            f"4: LI(x{params.rs1}, 1) # insignificant, just an action before the next align",
            ".align 12 # align to 4096 bytes",
            "nop # use up 4 bytes",
            f"{instr_name} x{params.rs1}, x{params.rs2}, 5f # branch forward by 4092",
            "j 19f # shouldn't happen",
            ".align 12 # align to 4096 bytes",
            "5: j 7f # jump around to test backward branch",
            "6: j 9f # backward branch succeeded",
            f"7: {instr_name} x{params.rs1}, x{params.rs2}, 6b # backward branch by -4",
            "j 19f # shouldn't happen",
            "8: j 11f # backward branch succeeded",
            "nop",
            f"9: {instr_name} x{params.rs1}, x{params.rs2}, 8b # backward branch by -8",
            "j 19f # shouldn't happen",
            ".align 12 # align to 4096 bytes",
            "10: j 20f # backward branch succeeded",
            ".align 12 # align to 4096 bytes",
            f"11: {instr_name} x{params.rs1}, x{params.rs2}, 10b # backward branch by -4096",
            "j 19f # shouldn't happen",
            f"19: li x{params.rs1}, -1 # write failure code",
            write_sigupd(params.rs1, test_data),  # failure code
            f"20: li x{params.rs1}, 1 # write success code",
            write_sigupd(params.rs1, test_data),  # success code
        ]
    )
    return_test_regs(test_data, params)
    return test_lines
