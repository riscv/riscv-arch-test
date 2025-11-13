##################################
# cp_offset.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_offset coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import write_sigupd
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_offset")
def make_offset(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for backward branch negative offsets."""
    if instr_type == "J":
        return make_offset_j(instr_name, instr_type, coverpoint, test_data)

    # TODO: implement support for compressed instructions
    if instr_type in ["CJ", "CB", "CJR"]:
        return []

    return []  # TODO

    params = generate_random_params(test_data, instr_type)
    assert params.rs1 is not None and params.rs2 is not None and params.rd is not None
    check_reg = test_data.int_regs.get_register()

    # Generate instruction-specific test line
    if instr_type == "B":
        # B-type: beq, bne, blt, bge, bltu, bgeu - always branches when comparing x0 with x0
        branch_instr = f"{instr_name} x0, x0, 1b # backward branch"
    elif instr_type in ["JR"]:
        branch_instr = f"{instr_name} x{params.rs2} # backward jump"
    elif instr_type in ["CR"]:
        # Compressed register jumps
        if instr_name == "c.jalr":
            test_data.int_regs.return_register(params.rd)
            test_data.int_regs.consume_registers([1])  # c.jalr always uses x1
            params.rd = 1
        branch_instr = f"{instr_name} x{params.rs2}"
    elif instr_type == "CJ":
        # Compressed unconditional jump
        branch_instr = f"{instr_name} 1b"
    elif instr_type == "CB":
        branch_instr = f"{instr_name} x{params.rs1}, 1b"
    else:
        raise ValueError(f"cp_offset coverpoint not supported for instruction {instr_name} with type {instr_type}")

    test_lines = [
        "\n# Testcase cp_offset negative bin",
        "j 2f # jump past backward branch target",
        "1: j 3f # backward branch target: jump past backward branch",
        "2:",
    ]
    if instr_type in ["JR", "CJR", "CJALR"]:
        test_lines.append(f"LA(x{params.rs2}, 1b) # load backward branch target")
    elif instr_type == "CB":
        branch_val = 0 if instr_name == "c.beqz" else 1  # set value to ensure branch is taken
        test_lines.append(f"LI(x{params.rs1}, {branch_val}) # initialize {params.rs1} to {branch_val} for taken branch")
    test_lines.extend(
        [
            f"LI(x{check_reg}, 1) # branch is taken",
            branch_instr,
            f"LI(x{check_reg}, 0) # branch is not taken",
            "3: # done with sequence",
            write_sigupd(check_reg, test_data),
        ]
    )
    # For jalr, check return address too
    if instr_type in ["JR", "CJR", "CJALR"]:
        temp_reg = test_data.int_regs.get_register(exclude_regs=[0])
        test_lines.extend(
            [
                f"auipc x{temp_reg}, 0 # get current PC",
                f"sub x{params.rd}, x{params.rd}, x{temp_reg} # subtract PC to make position-independent",
                write_sigupd(params.rd, test_data),
            ]
        )
        test_data.int_regs.return_register(temp_reg)

    test_data.int_regs.return_register(check_reg)
    test_data.int_regs.return_registers(params.used_int_regs)

    if coverpoint == "cp_offset_jalr":
        test_lines.extend(make_offset_lsbs(instr_name, instr_type, coverpoint, test_data))

    return test_lines


def make_offset_j(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for J-type forward and backward offsets."""
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rd is not None
    check_reg = test_data.int_regs.get_register(exclude_regs=[0])

    test_lines = [
        "\n# Testcase cp_offset",
        f"LI(x{check_reg}, 2)  # initialize check register",
        "j 2f # jump past backward jump update",
        f"5: addi x{check_reg}, x{check_reg}, 13 # increment check register if backward jump taken",
        "j 4f # jump past forward jump test",
        "# cp_offset forward jump",
        f"2: {instr_name} x{params.rd}, 3f # forward jump",
        f"addi x{check_reg}, x{check_reg}, -6 # decrement check register if forward jump not taken",
        "3:",
        f"addi x{check_reg}, x{check_reg}, 7 # increment check register if forward jump taken",
        write_sigupd(params.rd, test_data),
        write_sigupd(check_reg, test_data),
        "# cp_offset backward jump",
        f"{instr_name} x{params.rd}, 5b # backward jump",
        f"addi x{check_reg}, x{check_reg}, -3 # decrement check register if backward jump not taken",
        "4:",
        write_sigupd(params.rd, test_data),
        write_sigupd(check_reg, test_data),
    ]
    test_data.int_regs.return_register(check_reg)
    test_data.int_regs.return_registers(params.used_int_regs)
    return test_lines


def make_offset_lsbs(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rs1 is not None and params.rd is not None
    test_lines = ["# Testcase cp_offset_lsbs"]
    if instr_type == "JR":
        test_lines.extend(
            [
                "LA(x3, jalrlsb1) # load address of label",
                f"LI(x{params.rs1}, 1)" + " # branch is taken",
                f"{instr_name} x1, x3, 1 # jump to label + 1, extra plus 1 should be discarded",
                f"LI(x{params.rs1}, 0)" + " # branch is not taken",
                "jalrlsb1:",
                write_sigupd(params.rs1, test_data),
                write_sigupd(params.rd, test_data),  # check return value in jalr
                "LA(x3, jalrlsb2) # load address of label",
                "addi x3, x3, 3 # add 3 to address",
                f"LI(x{params.rs1},1)" + " # branch is taken",
                f"{instr_name} x1, x3, -2 # jump to label + 1, extra plus 1 should be discarded",
                f"LI(x{params.rs1}, 0)" + " # branch is not taken",
                "jalrlsb2:",
                write_sigupd(params.rs1, test_data),
                write_sigupd(params.rd, test_data),  # check return value in jalr
            ]
        )
    else:  # c.jalr / c.jr
        test_lines.extend(
            [
                f"LA(x3, {instr_name}lsb00) # load address of label",
                f"c.li x{params.rs1}, 1" + " # branch is taken",
                f"{instr_name} x3 # jump to address with bottom two lsbs = 00",
                f"c.li x{params.rs1}, 0" + " # branch is not taken & used as something to jump over",
                ".align 2",
                f"{instr_name}lsb00: ",
                write_sigupd(params.rs1, test_data),
                write_sigupd(1, test_data) if instr_name == "c.jalr" else "",  # check return value in c.jalr
                f"LA(x3, {instr_name}lsb01) # load address of label",
                "addi x3, x3, 1 # add 1 to address",
                f"c.li x{params.rs1}, 1" + " # branch is taken",
                f"{instr_name} x3 # jump to address with bottom two lsbs = 01",
                f"c.li x{params.rs1}, 0" + " # branch is not taken & used as something to jump over",
                ".align 2",
                f"{instr_name}lsb01: ",
                write_sigupd(params.rs1, test_data),
                write_sigupd(1, test_data) if instr_name == "c.jalr" else "",  # check return value in c.jalr
                f"LA(x3, {instr_name}lsb10) # load address of label",
                "addi x3, x3, 2 # add 2 to address",
                f"c.li x{params.rs1}, 1" + " # branch is taken",
                f"{instr_name} x3 # jump to address with bottom two lsbs = 10",
                f"c.li x{params.rs1}, 0" + " # branch is not taken & used as something to jump over",
                ".align 2",
                f"{instr_name}lsb10: nop",
                write_sigupd(params.rs1, test_data),
                write_sigupd(1, test_data) if instr_name == "c.jalr" else "",  # check return value in c.jalr
                "nop",  # c.jalr does not support 2 byte jumps, so this is a noop
                f"LA(x3, {instr_name}lsb11) # load address of label",
                "addi x3, x3, 3 # add 3 to address",
                f"c.li x{params.rs1}, 1" + " # branch is taken",
                f"{instr_name} x3 # jump to address with bottom two lsbs = 11",
                f"c.li x{params.rs1}, 0" + " # branch is not taken & used as something to jump over",
                ".align 2",
                f"{instr_name}lsb11: nop",
                write_sigupd(params.rs1, test_data),
                write_sigupd(1, test_data) if instr_name == "c.jalr" else "",  # check return value in c.jalr
            ]
        )

    test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines
