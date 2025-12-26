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

    return_test_regs(test_data, params)
    return test_lines
