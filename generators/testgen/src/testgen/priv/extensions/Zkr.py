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
    """Test csrrw seed in M/S/U mode for each of the 4 mseccfg (sseed x useed) combinations."""
    covergroup = "Zkr_cg"
    coverpoint = "cp_zkr_seed_csrrw"

    dest_reg, mseccfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[1, 6, 7, 9])

    lines = [
        comment_banner(
            coverpoint,
            "csrrw seed across privilege modes and mseccfg.sseed/useed",
        )
    ]

    for sseed in (0, 1):
        for useed in (0, 1):
            mseccfg_val = (sseed << 9) | (useed << 8)
            tag = f"sseed{sseed}_useed{useed}"

            lines.extend(
                [
                    f"\n# mseccfg: sseed={sseed}, useed={useed}",
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{mseccfg_reg}, {mseccfg_val})",
                    f"csrw mseccfg, x{mseccfg_reg}",
                ]
            )

            # legal access in M-mode: access always legal
            lines.extend(
                [
                    test_data.add_testcase(f"M_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                ]
            )

            # legal when ssead = 1 in S-mode
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(f"S_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                    "RVTEST_GOTO_MMODE",
                ]
            )

            # legal only when useed = 1 in U-mode
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(f"U_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                    "RVTEST_GOTO_MMODE",
                ]
            )

    # Restore mseccfg
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            f"LI(x{mseccfg_reg}, 0)",
            f"csrw mseccfg, x{mseccfg_reg}",
        ]
    )

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg])
    return lines


def _generate_seed_illegal_csr_op_tests(test_data: TestData) -> list[str]:
    """Test that non-CSRRW CSR ops on seed always cause illegal instruction."""
    covergroup = "Zkr_cg"
    coverpoint = "cp_zkr_seed_illegal_csr_op"

    dest_reg, mseccfg_reg = test_data.int_regs.get_registers(2, exclude_regs=[1, 6, 7, 9])

    lines = [
        comment_banner(
            coverpoint,
            "Non-CSRRW CSR ops on seed cause illegal instruction in every mode",
        )
    ]

    # Enable S-mode and U-mode access using mseccfg
    sseed_useed_enabled = (1 << 9) | (1 << 8)
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            f"LI(x{mseccfg_reg}, {sseed_useed_enabled})",
            f"csrw mseccfg, x{mseccfg_reg}",
        ]
    )

    # (op, funct3, is_immediate) for each illegal CSR op
    illegal_ops: list[tuple[str, bool]] = [
        ("csrrs", False),
        ("csrrc", False),
        ("csrrwi", True),
        ("csrrsi", True),
        ("csrrci", True),
    ]

    for op, is_imm in illegal_ops:
        for rs1_imm_val in (0, 1):
            tag = f"{op}_rs1imm{rs1_imm_val}"

            if is_imm:
                instr_zero = f"{op} x{dest_reg}, seed, 0"
                instr_nonzero = f"{op} x{dest_reg}, seed, 1"
            else:
                instr_zero = f"{op} x{dest_reg}, seed, x0"
                instr_nonzero = f"{op} x{dest_reg}, seed, x1"

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
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    test_data.add_testcase(f"S_{tag}", coverpoint, covergroup),
                    instr,
                    "RVTEST_GOTO_MMODE",
                ]
            )

            # U-mode
            lines.extend(
                [
                    "RVTEST_GOTO_LOWER_MODE Umode",
                    test_data.add_testcase(f"U_{tag}", coverpoint, covergroup),
                    instr,
                    "RVTEST_GOTO_MMODE",
                ]
            )

    # Restore mseccfg
    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            f"LI(x{mseccfg_reg}, 0)",
            f"csrw mseccfg, x{mseccfg_reg}",
        ]
    )

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg])
    return lines


@add_priv_test_generator(
    "Zkr",
    required_extensions=["I", "Zicsr", "Sm", "S", "Zkr"],
    march_extensions=["Zicsr", "Zkr", "I"],
)
def make_zkr(test_data: TestData) -> list[str]:
    """Generate tests for Zkr"""
    lines: list[str] = []

    lines.extend(_generate_seed_csrrw_tests(test_data))
    lines.extend(_generate_seed_illegal_csr_op_tests(test_data))

    return lines
