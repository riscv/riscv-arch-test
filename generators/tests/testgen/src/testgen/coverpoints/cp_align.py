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
        test_data.add_testcase_string(coverpoint)
        if instr_type == "L":
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], immval=alignment)
            assert params.rs1 is not None, "rs1 must be provided for L-type instruction"
            assert params.rd is not None, "rd must be provided for L-type instruction"
            assert params.immval is not None and params.temp_val is not None and params.temp_reg is not None, (
                "immval, temp_val, and temp_reg must be provided for L-type instruction"
            )

            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (imm[2:0] = {params.immval:03b})",
                    f"LA(x{params.rs1}, scratch) # load base address",
                    load_int_reg("temp_reg", params.temp_reg, params.temp_val, test_data),
                    f"SREG x{params.temp_reg}, 0(x{params.rs1}) # store test value to memory",
                    f"SREG x{params.temp_reg}, REGWIDTH(x{params.rs1}) # store test value to memory",
                    f"{instr_name} x{params.rd}, {params.immval}(x{params.rs1}) # perform load",
                    write_sigupd(params.rd, test_data, "int"),
                    "",
                ]
            )

        elif instr_type == "S":
            params = generate_random_params(test_data, instr_type, exclude_regs=[0], immval=alignment)
            assert params.rs1 is not None, "rs1 must be provided for S-type instructions"
            assert params.rs2 is not None and params.rs2val is not None, (
                "rs2 and rs2val must be provided for S-type instructions"
            )
            assert params.temp_reg is not None, "temp_reg must be provided for S-type instructions"
            assert params.immval is not None, "immval must be provided for S-type instructions"

            test_data.sigupd_count += 3  # extra space in signature region is needed
            offset = 8
            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (imm[2:0] = {params.immval:03b})",
                    load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                    f"{instr_name} x{params.rs2}, {params.immval}(x{test_data.int_regs.sig_reg}) # perform store",
                    f"addi x{test_data.int_regs.sig_reg}, x{test_data.int_regs.sig_reg}, {offset} # increment signature pointer",
                    "#ifdef SELFCHECK",
                    f"LREG x{params.temp_reg}, -{offset}(x{test_data.int_regs.sig_reg}) # load stored value for checking",
                    write_sigupd(params.temp_reg, test_data),
                    # For XLEN == 32, two sigupds are needed to handle alignments up to 7 that enter a second word
                    f"LREG x{params.temp_reg}, -{offset}(x{test_data.int_regs.sig_reg}) # load stored value for checking"
                    if test_data.xlen == 32
                    else "",
                    write_sigupd(params.temp_reg, test_data) if test_data.xlen == 32 else "",
                    "#else",
                    f"{instr_name} x{params.rs2}, {params.immval}(x{test_data.int_regs.sig_reg}) # repeat store so it is available for checking",
                    f"addi x{test_data.int_regs.sig_reg}, x{test_data.int_regs.sig_reg}, {offset} # adjust base address for offset",
                    "# nops to ensure length matches SELFCHECK",
                    "nop",
                    "nop",
                    "nop",
                    "#endif",
                    "",
                ]
            )

        else:
            raise ValueError(f"Unknown instruction type: {instr_type} for cp_align.")

        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines
