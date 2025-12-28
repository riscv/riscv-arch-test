##################################
# cp_offset.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_offset coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import load_int_reg, return_test_regs, write_sigupd
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_offset")
def make_offset(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for backward branch negative offsets."""

    test_lines: list[str] = ["# Testcase cp_offset negative bin (positive bin is covered by other coverpoints)"]
    if instr_name == "c.jalr":
        params = generate_random_params(test_data, instr_type, rd=1)
    elif instr_name == "c.jr":
        params = generate_random_params(test_data, instr_type, rd=0)
    else:
        params = generate_random_params(test_data, instr_type)

    test_data.add_testcase_string(coverpoint)

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
                f"{instr_name} x{params.rd}, x{params.rs1}, 0 # backward jump"
                if instr_type == "JR"
                else f"{instr_name} x{params.rs1} # backward jump",
                f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # jump not taken, decrement check value",
                "3:  # done with sequence",
                write_sigupd(params.temp_reg, test_data),
                f"# check return address from {instr_name}",
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
                f"2: {instr_name} 1b # backward jump",
                f"addi x{params.temp_reg}, x{params.temp_reg}, -2 # jump not taken, decrement check value",
                "3:  # done with sequence",
                write_sigupd(params.temp_reg, test_data),
            ]
        )
    elif instr_type == "J":
        pass  # cp_offset is covered by other tests for jal. TODO: Maybe revisit this and implement it anyway for completeness.
    else:
        raise ValueError(f"cp_offset coverpoint not supported for instruction {instr_name} with type {instr_type}.")

    if coverpoint == "cp_offset_c_jr" or coverpoint == "cp_offset_jalr":
        ...
        # test_lines.extend(make_offset_lsbs(instr_name, instr_type, coverpoint, test_data))
    elif coverpoint != "cp_offset":
        raise ValueError(f"Unknown variant {coverpoint} for cp_offset coverpoint.")

    return_test_regs(test_data, params)
    return test_lines
