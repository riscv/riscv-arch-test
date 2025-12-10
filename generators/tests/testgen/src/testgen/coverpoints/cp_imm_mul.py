##################################
# cp_imm_mul.py
#
# harris@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_imm_mul coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_imm_mul")
def make_cp_uimm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for compressed immediate values that are multiples."""
    exclude_regs: list[int] = []
    if coverpoint == "cp_imm_mul":
        imm_mul = range(0, 128, 4)
    elif coverpoint.endswith("_4sp"):
        imm_mul = range(0, 256, 4)
    elif coverpoint.endswith("_8"):
        imm_mul = range(0, 256, 8)
    elif coverpoint.endswith("_8sp"):
        imm_mul = range(0, 512, 8)
    elif coverpoint.endswith("_addi4spn"):
        imm_mul = range(4, 1024, 4)
        exclude_regs = [2]  # Exclude sp
    elif coverpoint.endswith("_addi16sp"):
        imm_mul = [i for i in range(-512, 512, 16) if i != 0]
    else:
        raise ValueError(f"Unknown cp_uimm coverpoint variant: {coverpoint} for {instr_name}")
    test_lines: list[str] = []
    for imm in imm_mul:
        test_data.add_testcase_string(coverpoint)
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, immval=imm, exclude_regs=exclude_regs)
        desc = f"{coverpoint}: imm={imm}"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines
