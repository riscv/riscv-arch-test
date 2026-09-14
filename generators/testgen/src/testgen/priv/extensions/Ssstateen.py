# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CSR_OPS = ["csrrw", "csrrs", "csrrc", "csrr"]


# Mode dispatch for the coverpoints that sample in both S- and U-mode. Each entry is
# (label, line entering the mode, line returning to S-mode). Ssstateen implies S-mode, and
# the suite boots there, so the S-mode leg needs no switch at all.
_LOWER_MODES = [
    ("smode", "", ""),
    ("umode", "RVTEST_TSBI_GOTO_UMODE", "RVTEST_TSBI_GOTO_SMODE"),
]


def _write_se0(temp_reg: int, *, enable: bool) -> list[str]:
    """Set (enable=True) or clear (enable=False) SE0 in mstateen0/mstateen0h.

    Skipped entirely where Smstateen is absent: mstateen0 does not exist there, and an
    illegal access made through T-SBI faults inside the handler rather than in test code,
    which aborts the run. Without Smstateen sstateen0 is simply ungated.
    """
    action = "csrs" if enable else "csrc"
    description = "set SE0=1" if enable else "clear SE0=0"
    return [
        "#ifdef SMSTATEEN_SUPPORTED",
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, 0x8000000000000000)  # SE0 = bit 63 of mstateen0",
        tsbi_call(f"{action} mstateen0, x{temp_reg}  # {description}"),
        "#else",
        f"LI(x{temp_reg}, 0x80000000)  # SE0 = bit 31 of mstateen0h",
        tsbi_call(f"{action} mstateen0h, x{temp_reg}  # {description}"),
        "#endif",
        "#endif  // SMSTATEEN_SUPPORTED",
    ]


def _save_mstateen(save_reg: int, save_regh: int) -> list[str]:
    """Save mstateen0 (and mstateen0h on RV32) into separate registers."""
    return [
        "#ifdef SMSTATEEN_SUPPORTED",
        tsbi_call(f"csrr x{save_reg}, mstateen0  # save mstateen0"),
        "#if __riscv_xlen == 32",
        tsbi_call(f"csrr x{save_regh}, mstateen0h  # save mstateen0h on RV32"),
        "#endif",
        "#endif  // SMSTATEEN_SUPPORTED",
    ]


def _restore_mstateen(save_reg: int, save_regh: int) -> list[str]:
    """Restore mstateen0 (and mstateen0h on RV32) from separate registers."""
    return [
        "#ifdef SMSTATEEN_SUPPORTED",
        tsbi_call(f"csrw mstateen0, x{save_reg}  # restore mstateen0"),
        "#if __riscv_xlen == 32",
        tsbi_call(f"csrw mstateen0h, x{save_regh}  # restore mstateen0h on RV32"),
        "#endif",
        "#endif  // SMSTATEEN_SUPPORTED",
    ]


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses
#   Cross: priv_mode_u × sstateen_csrs × csrops × se0_one
#   U-mode only.
# ---------------------------------------------------------------------------


def _generate_csr_illegal_accesses(test_data: TestData) -> list[str]:
    coverpoint = "cp_csr_illegal_accesses"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "Attempt CSR ops to sstateenN CSRs from U-mode with SE0=1 (should trap)",
        )
    ]

    temp_reg, save_mstateen, save_mstatenh = test_data.int_regs.get_registers(3)

    sstateen_csrs = ["sstateen0", "sstateen1", "sstateen2", "sstateen3"]

    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    lines.extend(_write_se0(temp_reg, enable=True))
    lines.append("RVTEST_TSBI_GOTO_UMODE")

    for csr in sstateen_csrs:
        for op in CSR_OPS:
            if op == "csrr":
                insn = f"{op} x{temp_reg}, {csr}  # illegal from U-mode"
            else:
                insn = f"{op} x{temp_reg}, {csr}, x{temp_reg}  # illegal from U-mode"
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode_se0_1", coverpoint, covergroup),
                    insn,
                ]
            )

    lines.append("RVTEST_TSBI_GOTO_SMODE")
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: priv_mode_s × sstateen_walk_csr × csrops × csr_walk × se0_one
#   Must run from S-mode with SE0=1. csr_walk_test covers csrw+csrs+csrc
#   internally (walking-1s uses csrw+csrs, walking-0s uses csrw+csrc).
# ---------------------------------------------------------------------------


def _generate_walking_ones(test_data: TestData) -> list[str]:
    coverpoint = "cp_walking_ones"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns on sstateen0 from S-mode with SE0=1",
        )
    ]

    save_mstateen_se0, temp_reg = test_data.int_regs.get_registers(2)

    # Only SE0 needs to be saved and restored for this test
    lines.extend(
        [
            "#ifdef SMSTATEEN_SUPPORTED",
            "#if __riscv_xlen == 64",
            tsbi_call(f"csrr x{save_mstateen_se0}, mstateen0  # save mstateen0 on RV64"),
            "#elif __riscv_xlen == 32",
            tsbi_call(f"csrr x{save_mstateen_se0}, mstateen0h  # save mstateen0h on RV32"),
            "#endif",
            "#endif  // SMSTATEEN_SUPPORTED",
        ]
    )
    lines.extend(_write_se0(temp_reg, enable=True))

    # The walk is sampled in S-mode, which the suite boots into, so the priv_mode_s bin is
    # hit without a mode switch. csr_walk_test emits csrw+csrs (walking-1s) and csrw+csrc
    # (walking-0s), satisfying the csrops cross.
    test_data.int_regs.return_registers([temp_reg])
    lines.extend(
        [
            "",
            test_data.add_testcase("sstateen0_walk_se0_1_smode", coverpoint, covergroup),
        ]
    )
    lines.extend(csr_walk_test(test_data, ("sstateen0", 0x7), covergroup, coverpoint))

    lines.extend(
        [
            "#ifdef SMSTATEEN_SUPPORTED",
            "#if __riscv_xlen == 64",
            tsbi_call(f"csrw mstateen0, x{save_mstateen_se0}  # restore mstateen0 on RV64"),
            "#elif __riscv_xlen == 32",
            tsbi_call(f"csrw mstateen0h, x{save_mstateen_se0}  # restore mstateen0h on RV32"),
            "#endif",
            "#endif  // SMSTATEEN_SUPPORTED",
        ]
    )
    test_data.int_regs.return_registers([save_mstateen_se0])

    return lines


# ---------------------------------------------------------------------------
# cp_jvt
#   Cross: priv_mode_maybes_u × csrops × jvt_csr × jvt_state × se0_one
#   priv_mode_maybes_u = S-mode + U-mode.
# ---------------------------------------------------------------------------


def _generate_jvt(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on jvt from S/U-mode with sstateen0.JVT enabled/disabled under SE0=1",
        )
    ]

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_jvt, ones_reg = test_data.int_regs.get_registers(6)

    JVT_BIT = 2

    # priv_mode_maybes_u = S-mode + U-mode
    for mode_label, enter_line, exit_line in _LOWER_MODES:
        for jvt_state in [0, 1]:
            jvt_action = "csrc" if jvt_state == 0 else "csrs"
            lines.extend(
                [
                    "",
                    f"{INDENT}# SE0=1, sstateen0.JVT={jvt_state}, {mode_label}",
                    f"csrr x{save_sstateen}, sstateen0  # save sstateen0",
                    f"csrr x{save_jvt}, jvt  # save jvt",
                    f"LI(x{ones_reg}, -1)",
                ]
            )
            lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
            lines.extend(_write_se0(temp_reg, enable=True))
            lines.extend(
                [
                    f"LI(x{temp_reg}, {1 << JVT_BIT})",
                    f"{jvt_action}(sstateen0, x{temp_reg})  # sstateen0.JVT = {jvt_state}",
                ]
            )
            if enter_line:
                lines.append(enter_line)
            for op in CSR_OPS:
                insn = f"{op}(x{temp_reg}, jvt)" if op == "csrr" else f"{op}(x{temp_reg}, jvt, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{op.lower()}_jvt_se0_1_jvt_{jvt_state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        insn,
                    ]
                )
            if exit_line:
                lines.append(exit_line)
            lines.extend(
                [
                    f"csrw sstateen0, x{save_sstateen}  # restore sstateen0",
                    f"csrw jvt, x{save_jvt}  # restore jvt",
                ]
            )
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_jvt, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower
#   Cross: priv_mode_maybes_u × misa_F × se0_one × sstateen0_fcsr_bit × csrops × fcsr_lower_mode_csrs
#   priv_mode_maybes_u = S-mode + U-mode.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on frm/fflags/fcsr from S/U-mode with SE0=1 and sstateen0.FCSR states",
        )
    ]

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_reg = test_data.int_regs.get_registers(5)
    fp_csrs = ["frm", "fflags", "fcsr"]
    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR

    for fcsr_bit in [0, 1]:
        fcsr_action = "csrc" if fcsr_bit == 0 else "csrs"
        for mode_label, enter_line, exit_line in _LOWER_MODES:
            lines.extend(
                [
                    "",
                    f"{INDENT}# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"csrr x{save_sstateen}, sstateen0",
                ]
            )
            lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
            lines.extend(_write_se0(temp_reg, enable=True))
            lines.extend(
                [
                    f"LI(x{temp_reg}, {1 << FCSR_BIT})",
                    f"{fcsr_action}(sstateen0, x{temp_reg})  # sstateen0.FCSR = {fcsr_bit}",
                ]
            )
            if enter_line:
                lines.append(enter_line)
            for csr in fp_csrs:
                for op in CSR_OPS:
                    insn = f"{op}(x{temp_reg}, {csr})" if op == "csrr" else f"{op}(x{temp_reg}, {csr}, x{save_reg})"
                    lines.extend(
                        [
                            "",
                            test_data.add_testcase(
                                f"{op.lower()}_{csr}_se0_1_fcsr{fcsr_bit}_{mode_label}",
                                coverpoint,
                                covergroup,
                            ),
                            f"csrr x{save_reg}, {csr}  # read operand for write-back ops",
                            insn,
                        ]
                    )
            if exit_line:
                lines.append(exit_line)
            lines.append(f"csrw sstateen0, x{save_sstateen}  # restore sstateen0")
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, save_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_fp_instrs
#   Cross: priv_mode_maybes_u × misa_F × se0_one × sstateen0_fcsr_bit × fp_instrs
#   priv_mode_maybes_u = S-mode + U-mode.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_fp_instrs"
    covergroup = "Ssstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "FP instructions from S/U-mode with SE0=1 and sstateen0.FCSR states",
        )
    ]

    (temp_reg1, temp_reg2, temp_reg3, save_mstateen, save_mstatenh, save_sstateen) = test_data.int_regs.get_registers(6)

    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR

    fp_instrs = [
        (f"fadd.s x{temp_reg1}, x{temp_reg2}, x{temp_reg3}", "fadd_s"),
        (f"fcvt.w.s x{temp_reg1}, x{temp_reg2}", "fcvt_w_s"),
        (f"fcvt.s.w x{temp_reg1}, x{temp_reg2}", "fcvt_s_w"),
        (f"fclass.s x{temp_reg1}, x{temp_reg2}", "fclass_s"),
    ]

    for fcsr_bit in [0, 1]:
        fcsr_action = "csrc" if fcsr_bit == 0 else "csrs"
        for mode_label, enter_line, exit_line in _LOWER_MODES:
            lines.extend(
                [
                    "",
                    f"{INDENT}# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"csrr x{save_sstateen}, sstateen0",
                ]
            )
            lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
            lines.extend(_write_se0(temp_reg1, enable=True))
            lines.extend(
                [
                    f"LI(x{temp_reg1}, {1 << FCSR_BIT})",
                    f"{fcsr_action}(sstateen0, x{temp_reg1})  # sstateen0.FCSR = {fcsr_bit}",
                ]
            )
            if enter_line:
                lines.append(enter_line)
            for insn, label in fp_instrs:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{label}_se0_1_fcsr{fcsr_bit}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        f"{insn}  # fp instr from {mode_label} fcsr={fcsr_bit}",
                    ]
                )
            if exit_line:
                lines.append(exit_line)
            lines.append(f"csrw sstateen0, x{save_sstateen}  # restore sstateen0")
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg1, temp_reg2, temp_reg3, save_mstateen, save_mstatenh, save_sstateen])
    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Ssstateen",
    required_extensions=["Ssstateen"],
    march_extensions=["Ssstateen", "Zcmt", "Zfinx"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssstateen(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Ssstateen state-enable extension testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    # Unconditional coverpoints — required by all Ssstateen targets
    tc.code.extend(_generate_csr_illegal_accesses(test_data))
    tc.code.extend(_generate_walking_ones(test_data))

    # cp_fcsr_lower, cp_fcsr_fp_instrs — only when Zfinx is supported
    tc.code.append("#ifdef ZFINX_SUPPORTED")
    tc.code.extend(_generate_fcsr_lower(test_data))
    tc.code.extend(_generate_fcsr_lower_fp_instrs(test_data))
    tc.code.append("#endif  // ZFINX_SUPPORTED")

    # cp_jvt — only when Zcmt is supported (covers both S-mode and U-mode)
    tc.code.append("#ifdef ZCMT_SUPPORTED")
    tc.code.extend(_generate_jvt(test_data))
    tc.code.append("#endif  // ZCMT_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
