##################################
# priv/extensions/Zkr.py
#
# Zkr privileged test generator
# jgong@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zkr extension test generator"""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_seed_csrrw_tests(test_data: TestData) -> list[str]:
    """Test csrrw seed in M/S/U mode for each of the 4 mseccfg (sseed x useed) combinations (3 x 4 bins)."""
    covergroup = "Zkr_cg"
    coverpoint = "cp_zkr_seed_csrrw"

    dest_reg, mseccfg_reg, src_reg, save_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "csrrw seed across privilege modes and mseccfg.sseed/useed",
        )
    ]

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            f"LI(x{src_reg}, 0)",
            "#ifdef U_SUPPORTED",
            f"csrr x{save_reg}, mseccfg",
            "#endif",
        ]
    )

    for sseed in (0, 1):
        for useed in (0, 1):
            mseccfg_val = (sseed << 9) | (useed << 8)
            tag = f"sseed{sseed}_useed{useed}"

            lines.extend(
                [
                    f"# mseccfg: sseed={sseed}, useed={useed}",
                    "RVTEST_GOTO_MMODE",
                    "#ifdef U_SUPPORTED",
                    f"LI(x{mseccfg_reg}, {mseccfg_val})",
                    f"csrw mseccfg, x{mseccfg_reg}",
                    "#endif",
                ]
            )

            # legal access in M-mode (nonzero and zero rs1 to cover both insn[19:15] bins)
            lines.extend(
                [
                    test_data.add_testcase(f"M_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x{src_reg}",
                    test_data.add_testcase(f"M_zero_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                ]
            )

            # legal when sseed = 1 in S-mode (nonzero and zero rs1)
            lines.extend(
                [
                    "#ifdef S_SUPPORTED",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(f"S_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x{src_reg}",
                    "nop",
                    test_data.add_testcase(f"S_zero_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                    "nop",
                    "RVTEST_GOTO_MMODE",
                    "#endif",
                ]
            )

            # legal only when useed = 1 in U-mode (nonzero and zero rs1)
            lines.extend(
                [
                    "#ifdef U_SUPPORTED",
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(f"U_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x{src_reg}",
                    "nop",
                    test_data.add_testcase(f"U_zero_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                    "nop",
                    "RVTEST_GOTO_MMODE",
                    "#endif",
                ]
            )

    # Restore mseccfg
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "#ifdef U_SUPPORTED",
            f"csrw mseccfg, x{save_reg}",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, src_reg, save_reg])
    return lines


def _generate_seed_illegal_csr_op_tests(test_data: TestData) -> list[str]:
    """Test CSR ops on seed for illegal instruction behavior in every mode."""
    covergroup = "Zkr_cg"
    coverpoint = "cp_zkr_seed_illegal_csr_op"

    dest_reg, mseccfg_reg, rs1_reg, save_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "CSR Read ops on seed cause illegal instruction in every mode",
        )
    ]

    sseed_useed_enabled = (1 << 9) | (1 << 8)
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "#ifdef U_SUPPORTED",
            f"csrr x{save_reg}, mseccfg",
            f"LI(x{mseccfg_reg}, {sseed_useed_enabled})",
            f"csrw mseccfg, x{mseccfg_reg}",
            "#endif",
            f"LI(x{rs1_reg}, 0)",
        ]
    )

    # (op, is_immediate) for each CSR op to test on seed
    csr_ops: list[tuple[str, bool]] = [
        ("csrrs", False),
        ("csrrc", False),
        ("csrrwi", True),
        ("csrrsi", True),
        ("csrrci", True),
        ("csrrw", False),
    ]

    for op, is_imm in csr_ops:
        for rs1_imm_val in (0, 1):
            tag = f"{op}_rs1imm{rs1_imm_val}"

            if is_imm:
                instr_zero = f"{op} x{dest_reg}, seed, 0"
                instr_nonzero = f"{op} x{dest_reg}, seed, 1"
            else:
                instr_zero = f"{op} x{dest_reg}, seed, x0"
                instr_nonzero = f"{op} x{dest_reg}, seed, x{rs1_reg}"

            instr = instr_zero if rs1_imm_val == 0 else instr_nonzero

            # M-mode
            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    test_data.add_testcase(f"M_{tag}", coverpoint, covergroup),
                    instr,
                ]
            )

            # S-mode
            lines.extend(
                [
                    "#ifdef S_SUPPORTED",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(f"S_{tag}", coverpoint, covergroup),
                    instr,
                    "nop",
                    "RVTEST_GOTO_MMODE",
                    "#endif",
                ]
            )

            # U-mode
            lines.extend(
                [
                    "#ifdef U_SUPPORTED",
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(f"U_{tag}", coverpoint, covergroup),
                    instr,
                    "nop",
                    "RVTEST_GOTO_MMODE",
                    "#endif",
                ]
            )

    # Restore mseccfg
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "#ifdef U_SUPPORTED",
            f"csrw mseccfg, x{save_reg}",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, rs1_reg, save_reg])
    return lines


@add_priv_test_generator(
    "Zkr",
    required_extensions=["Zkr"],
    extra_defines=[
        '#include "rvtest_config.h"',
        "#define rvtest_mtrap_routine",
        "#ifdef S_SUPPORTED",
        "#define rvtest_strap_routine",
        "#endif",
    ],
)
def make_zkr(test_data: TestData) -> list[str]:
    """Generate tests for Zkr"""
    lines: list[str] = []

    lines.extend(_generate_seed_csrrw_tests(test_data))
    lines.extend(_generate_seed_illegal_csr_op_tests(test_data))

    return lines
