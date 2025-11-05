##################################
# cp_align.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_align coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.immediates import modify_imm
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_align")
def make_align(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for alignment coverpoints."""
    if coverpoint == "cp_align_byte":
        alignments = [0, 1, 2, 3, 4, 5, 6, 7]
    elif coverpoint == "cp_align_hword":
        alignments = [0, 2, 4, 6]
    elif coverpoint == "cp_align_word":
        alignments = [0, 4]
    else:
        raise ValueError(f"Unknown cp_align coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []
    for alignment in alignments:
        if instr_type == "S":
            params = generate_random_params(test_data, instr_type, immval=alignment, rs1=test_data.int_regs.sig_reg)
        else:
            params = generate_random_params(test_data, instr_type, immval=alignment)
        assert (
            params.rs2 is not None and params.rs2val is not None and params.immval is not None and params.rd is not None
        )
        scaled_imm = modify_imm(params.immval, 12)
        test_lines.extend(
            [
                f"# {coverpoint}: imm[2:0]={alignment:03b}",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            ]
        )
        if instr_type == "L":
            test_lines.extend(
                [
                    f"LA(x{params.rs1}, scratch) # load base address",
                    f"SREG x{params.rs2}, {params.immval - (params.immval % 4)}(x{params.rs1}) # store test value to memory",
                    f"{instr_name} x{params.rd}, {scaled_imm}(x{params.rs1}) # perform load",
                    write_sigupd(params.rd, test_data, "int"),
                ]
            )

        # Cleanup
        return_regs: list[int] = []
        for reg in params.used_int_regs:
            if reg != test_data.int_regs.sig_reg:
                return_regs.append(reg)
        test_data.int_regs.return_registers(return_regs)

    return test_lines

    #     test_lines.extend(
    #         [
    #             f"# {coverpoint}: imm[2:0]={alignment:03b}",
    #             load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    #         ]
    #     )
    #     if instr_type == "L":
    #         test_lines.extend(
    #             [
    #                 f"LA(x{params.rs1}, scratch) # load base address",
    #                 f"SREG x{params.rs2}, {params.immval - (params.immval % 4)}(x{params.rs1}) # store test value to memory",
    #             ]
    #         )
    #     _, test_specific_lines, check_lines = format_instruction(instr_name, instr_type, test_data, params)
    #     if instr_type == "S":
    #         # Remove offset adjustment line
    #         check_lines_list = check_lines.splitlines()[1:]
    #         check_lines_modified: list[str] = []
    #         for line in check_lines_list:
    #             if "# repeat store so it is available for checking" in line:
    #                 line = line.replace("0(", f"{alignment}(")
    #             elif "-REGWIDTH" in line:
    #                 line = line.replace("-REGWIDTH", f"(-REGWIDTH + {alignment})")
    #             check_lines_modified.append(line)
    #         check_lines = "\n".join(check_lines_modified)

    #     test_lines.append(test_specific_lines)
    #     test_lines.append(check_lines)
    #     test_lines.append("")  # blank line between tests

    # return test_lines
