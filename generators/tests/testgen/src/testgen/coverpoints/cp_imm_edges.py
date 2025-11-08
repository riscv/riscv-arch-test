##################################
# cp_imm_edges.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges coverpoint generators."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_single_test
from testgen.utils.common import load_int_reg, write_sigupd
from testgen.utils.edges import IMMEDIATE_EDGES
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_imm_edges")
def make_cp_imm_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for immediate edge values."""
    if coverpoint == "cp_imm_edges":
        edges_imm = IMMEDIATE_EDGES.imm_12bit
    elif coverpoint.endswith("_20bit"):
        edges_imm = IMMEDIATE_EDGES.imm_20bit
    elif coverpoint.endswith("_6bit"):
        edges_imm = IMMEDIATE_EDGES.imm_6bit
    else:
        raise ValueError(f"Unknown cp_imm_edges coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    for edge_val in edges_imm:
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, immval=edge_val)
        desc = f"{coverpoint} (imm = {edge_val})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        test_data.int_regs.return_registers(params.used_int_regs)

    return test_lines


@add_coverpoint_generator("cp_imm_edges_branch")
def make_cp_imm_edges_branch(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for branch immediate edge values."""
    test_lines: list[str] = ["\n# Testcase cp_imm_edges_branch"]
    params = generate_random_params(test_data, instr_type)
    assert params.rs1 is not None and params.rs2 is not None
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
    test_data.int_regs.return_registers(params.used_int_regs)
    return test_lines


@add_coverpoint_generator("cp_imm_edges_jal", "cp_imm_edges_c_jal")
def make_cp_imm_edges_jal(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for JAL immediate edge values."""
    test_lines: list[str] = []
    if instr_name == "c.jal":
        # test_data.int_regs.consume_registers([1])
        # params = generate_random_params(test_data, instr_type, rd=1)  # c.jal always uses x1
        return []  # TODO: implement c.jal immediate edge tests
    elif instr_name == "c.j":
        # params = generate_random_params(test_data, instr_type, rd=0)  # c.j always uses x0
        return []  # TODO: implement c.j immediate edge tests
    else:
        params = generate_random_params(test_data, instr_type)
    assert params.rs1 is not None and params.rs2 is not None and params.rd is not None

    # Adjust min/max range based on instruction type
    if instr_name == "jal":
        minrng = 3
        maxrng = 14  # testing all 20 bits of immediate is too much code
    else:
        test_lines.append(".align 2 # Start at an address multiple of 4. Required for covering 2 byte jump.")
        minrng = 2
        maxrng = 13

    # Test smallest offset as a special case
    test_lines.extend(
        [
            "",
            f"# Testcase cp_imm_edges_jal (imm = {minrng - 1})",
            f".align {maxrng} # Start all tests on a multiple of the largest offset",
            f"{instr_name} {f'x{params.rs1},' if instr_name == 'jal' else ''} 1f # jump to aligned address to stress immediate",
            "1: # alignment too small to test with sigupd",
            f"{instr_name} {f'x{params.rs1},' if instr_name == 'jal' else ''} f{minrng}_{instr_name} # jump to aligned address to stress immediate",
        ]
    )

    # Test all other offsets
    for val in range(minrng, maxrng):
        test_lines.extend(
            [
                "",
                f"# Testcase cp_imm_edges_jal (imm = {val})",
                f".align {val - 1}",
                f"b{val - 1}_{instr_name}:",
            ]
        )
        if instr_name == "jal":
            if val >= 6:
                # Can only fit signature logic if jump is greater than 32 bytes (val + 1 = 6)
                test_lines.extend(
                    [
                        load_int_reg("rs1", params.rs1, val, test_data),
                        write_sigupd(params.rd, test_data),
                        write_sigupd(params.rs1, test_data),
                    ]
                )
            test_lines.append(
                f"{instr_name} x{params.rd}, f{val + 1}_{instr_name} # jump to aligned address to stress immediate"
            )
        else:  # c.jal, c.j
            if val >= 6:
                # Can only fit signature logic if jump is greater than 32 bytes (val + 1 = 6)
                test_lines.extend(
                    [
                        write_sigupd(params.rd, test_data),  # checking if return address is correct for c.jal
                        f"c.li x{params.rs1}, {val}",
                        write_sigupd(params.rs1, test_data),
                    ]
                )
            test_lines.append(f"{instr_name} f{val + 1}_{instr_name} # jump to aligned address to stress immediate")

        if val >= 6:
            test_lines.extend(
                [
                    f"LI(x{params.rs1}, {val})" if instr_name == "jal" else f"c.li x{params.rs1}, {val}",
                    write_sigupd(params.rd, test_data),
                    write_sigupd(params.rs1, test_data),
                ]
            )

        test_lines.extend(
            [
                f".align {val - 1}",
                f"f{val}_{instr_name}:",
            ]
        )

        if val >= 6:
            test_lines.extend(
                [
                    f"LI(x{params.rs1}, {val})" if instr_name == "jal" else f"c.li x{params.rs1}, {val}",
                    write_sigupd(params.rd, test_data),
                    write_sigupd(params.rs1, test_data),
                ]
            )

        if instr_name == "jal":
            test_lines.append(
                f"{instr_name} x{params.rd}, b{val - 1}_{instr_name} # jump to aligned address to stress immediate"
            )
            if val >= 6:
                # Can only fit signature logic if jump is greater than 32 bytes (val + 1 = 6)
                test_lines.extend(
                    [
                        load_int_reg("rs1", params.rs1, val, test_data),
                        write_sigupd(params.rd, test_data),
                        write_sigupd(params.rs1, test_data),
                    ]
                )
        else:  # c.jal, c.j
            if val == 12:  # temporary fix for bug in binutils
                if instr_name == "c.j":
                    test_lines.append(
                        ".half 0xB001 # backward c.j by -2048 to b12; GCC is not generating this compressed branch properly per https://github.com/riscv-collab/riscv-gnu-toolchain/issues/1647"
                    )
                elif instr_name == "c.jal":
                    test_lines.append(
                        ".half 0x3001 # backward jal by -2048 to b12; GCC is not generating this compressed branch properly per https://github.com/riscv-collab/riscv-gnu-toolchain/issues/1647"
                    )
            else:
                test_lines.append(f"{instr_name} b{val - 1}_{instr_name} # jump to aligned address to stress immediate")
            if val >= 6:
                # Can only fit signature logic if jump is greater than 32 bytes (val + 1 = 6)
                test_lines.extend(
                    [
                        f"c.li x{params.rs1}, {val}",
                        write_sigupd(params.rd, test_data),  # checking if return address is correct for c.jal
                        write_sigupd(params.rs1, test_data),
                    ]
                )

    # End of test
    test_lines.extend(
        [
            f".align {maxrng - 1}",
            f"f{maxrng}_{instr_name}:",
        ]
    )

    test_data.int_regs.return_registers(params.used_int_regs)
    return test_lines
