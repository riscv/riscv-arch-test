##################################
# cp_offset.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_offset coverpoint generator."""

from testgen.asm.helpers import load_int_reg, return_test_regs, write_sigupd
from testgen.constants import INDENT
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.testcase import TestCase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_offset")
def make_offset(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestCase]:
    """Generate tests for backward branch negative offsets."""
    tc = test_data.begin_testcase()

    test_lines: list[str] = ["# Testcase cp_offset negative bin (positive bin is covered by other coverpoints)"]
    if instr_name == "c.jalr":
        params = generate_random_params(test_data, instr_type, rd=1)
    elif instr_name == "c.jr":
        params = generate_random_params(test_data, instr_type, rd=0)
    else:
        params = generate_random_params(test_data, instr_type)

    if instr_type in ["B", "CB"]:
        assert params.rs1 is not None and params.temp_reg is not None and params.temp_val is not None
        if instr_type == "B":
            test_lines.extend(
                [
                    f"LI(x{params.rs1}, 1)",
                    f"LI(x{params.rs2}, {1 if instr_name in ['beq', 'bge', 'bgeu'] else 2}) # setup for taken branch",
                ]
            )
        else:  # CB
            branch_val = 0 if instr_name == "c.beqz" else 1  # set value to ensure branch is taken
            test_lines.append(f"LI(x{params.rs1}, {branch_val}) # initialize rs1 to {branch_val} for taken branch")

        test_lines.extend(
            [
                load_int_reg("branch check value", params.temp_reg, params.temp_val, test_data),
                "j 2f # jump past backward branch target",
                f"1: addi x{params.temp_reg}, x{params.temp_reg}, 4 # backward branch target, increment check value",
                "j 3f # jump past backward branch",
                test_data.add_testcase("neg", coverpoint),
                f"2: {instr_name} x{params.rs1}, {f'x{params.rs2},' if params.rs2 is not None else ''} 1b # backward branch",
                f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # branch not taken, decrement check value",
                "3:  # done with sequence",
                write_sigupd(params.temp_reg, test_data),
            ]
        )
    elif instr_type in ["JR", "CJR", "CJALR"]:
        assert (
            params.rs1 is not None
            and params.rd is not None
            and params.temp_reg is not None
            and params.temp_val is not None
        )
        test_lines.extend(
            [
                load_int_reg("jump check value", params.temp_reg, params.temp_val, test_data),
                "j 2f # jump past backward jump target",
                f"1: addi x{params.temp_reg}, x{params.temp_reg}, 4 # backward jump target, increment check value",
                "j 3f # jump past backward jump",
                f"2: LA(x{params.rs1}, 1b) # load backward jump target",
                test_data.add_testcase("neg", coverpoint),
                f"{instr_name} x{params.rd}, x{params.rs1}, 0 # backward jump"
                if instr_type == "JR"
                else f"{instr_name} x{params.rs1} # backward jump",
                f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # jump not taken, decrement check value",
                "3:  # done with sequence",
                write_sigupd(params.temp_reg, test_data),
                f"{INDENT}# check return address from {instr_name}",
                f"auipc x{params.temp_reg}, 0 # get current PC",
                f"sub x{params.rd}, x{params.rd}, x{params.temp_reg} # subtract PC to make position-independent",
                write_sigupd(params.rd, test_data),
            ]
        )
    elif instr_type in ["CJ", "CJAL"]:
        assert params.temp_reg is not None and params.temp_val is not None
        test_lines.extend(
            [
                load_int_reg("jump check value", params.temp_reg, params.temp_val, test_data),
                "j 2f # jump past backward jump target",
                f"1: addi x{params.temp_reg}, x{params.temp_reg}, 4 # backward jump target, increment check value",
                "j 3f # jump past backward jump",
                test_data.add_testcase("neg", coverpoint),
                f"2: {instr_name} 1b # backward jump",
                f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # jump not taken, decrement check value",
                "3:  # done with sequence",
                write_sigupd(params.temp_reg, test_data),
            ]
        )
    elif instr_type == "J":
        test_lines.append(
            "# cp_offset is covered by other tests for jal."
        )  # TODO: Maybe revisit this and implement it anyway for completeness.
    else:
        raise ValueError(f"cp_offset coverpoint not supported for instruction {instr_name} with type {instr_type}.")

    if coverpoint in {"cp_offset_c_jr", "cp_offset_jalr"}:
        test_lines.extend(make_offset_lsbs(instr_name, instr_type, test_data))
    elif coverpoint != "cp_offset":
        raise ValueError(f"Unknown variant {coverpoint} for cp_offset coverpoint.")

    return_test_regs(test_data, params)
    tc.code = "\n".join(test_lines)
    return [test_data.end_testcase()]


def make_offset_lsbs(instr_name: str, instr_type: str, test_data: TestData) -> list[str]:
    test_lines: list[str] = []
    if instr_type == "JR":
        # Loop over all 4 (rs1[0], imm[0]) combinations
        for rs1_lsb in (0, 1):
            for imm_lsb in (0, 1):
                params = generate_random_params(test_data, instr_type, exclude_regs=[0])
                assert (
                    params.rs1 is not None
                    and params.rd is not None
                    and params.temp_reg is not None
                    and params.temp_val is not None
                )
                label = f"jalrlsb_{rs1_lsb}{imm_lsb}"
                imm_val = -1 if (rs1_lsb == 1 and imm_lsb == 1) else imm_lsb
                test_lines.extend(
                    [
                        "",
                        f"# Testcase cp_offset_lsbs (rs1 LSB={rs1_lsb}, imm LSB={imm_lsb})",
                        load_int_reg("jump check value", params.temp_reg, params.temp_val, test_data),
                        f"LA(x{params.rs1}, {label}) # load address of label",
                        f"addi x{params.rs1}, x{params.rs1}, {rs1_lsb} # set rs1 LSB to {rs1_lsb}",
                        test_data.add_testcase(f"{rs1_lsb}_{imm_lsb}", "cp_offset_lsbs"),
                        f"{instr_name} x{params.rd}, x{params.rs1}, {imm_val} # jump with imm LSB = {imm_lsb}",
                        f"addi x{params.temp_reg}, x{params.temp_reg}, -4  # should not execute; branch not taken",
                        f"{label}: addi x{params.temp_reg}, x{params.temp_reg}, 2 # should execute; branch taken",
                        f"{INDENT}# check jump taken",
                        write_sigupd(params.temp_reg, test_data),
                        f"{INDENT}# check return address from {instr_name}",
                        f"auipc x{params.temp_reg}, 0 # get current PC",
                        f"sub x{params.rd}, x{params.rd}, x{params.temp_reg} # subtract PC to make position-independent",
                        write_sigupd(params.rd, test_data),
                    ]
                )
                return_test_regs(test_data, params)
    elif instr_type in ["CJR", "CJALR"]:
        # Loop over all 4 (rs1[1:0]) combinations
        for rs1_lsbs in range(4):
            params = generate_random_params(
                test_data, instr_type, exclude_regs=[0], rd=1 if instr_name == "c.jalr" else 0
            )
            assert (
                params.rs1 is not None
                and params.rd is not None
                and params.temp_reg is not None
                and params.temp_val is not None
            )
            label = f"jalrlsb_{rs1_lsbs}"
            test_lines.extend(
                [
                    "",
                    f"# Testcase cp_offset_lsbs (rs1 LSB={rs1_lsbs})",
                    load_int_reg("jump check value", params.temp_reg, params.temp_val, test_data),
                    f"LA(x{params.rs1}, {label}) # load address of label",
                    f"addi x{params.rs1}, x{params.rs1}, {rs1_lsbs} # set rs1 LSB to {rs1_lsbs}",
                    test_data.add_testcase(f"{rs1_lsbs:02b}", "cp_offset_lsbs"),
                    f"{instr_name} x{params.rs1} # jump",
                    f"addi x{params.temp_reg}, x{params.temp_reg}, -4  # should not execute; branch not taken",
                    ".align 2",
                    f"{label}: {'c.nop' if rs1_lsbs >= 2 else ''}",
                    f"addi x{params.temp_reg}, x{params.temp_reg}, 2 # should execute; branch taken",
                    f"{INDENT}# check jump taken",
                    write_sigupd(params.temp_reg, test_data),
                    f"{INDENT}# check return address from {instr_name}",
                    f"auipc x{params.temp_reg}, 0 # get current PC",
                    f"sub x{params.rd}, x{params.rd}, x{params.temp_reg} # subtract PC to make position-independent",
                    write_sigupd(params.rd, test_data),
                ]
            )
            return_test_regs(test_data, params)
    else:
        raise ValueError(f"cp_offset_lsbs coverpoint not supported for instruction type {instr_type}.")

    return test_lines
