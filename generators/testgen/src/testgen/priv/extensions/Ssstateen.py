# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CSR_OPS = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]


# RVTEST mode-switch macros, emitted as plain assembly
GOTO_UMODE = "RVTEST_GOTO_LOWER_MODE Umode  # enter U-mode"
GOTO_SMODE = "RVTEST_GOTO_LOWER_MODE Smode  # enter S-mode"
GOTO_MMODE = "RVTEST_GOTO_MMODE  # return to M-mode"

# Lower-mode dispatch for the priv_mode_maybes_u coverpoints. Each entry is
# (label, line that switches into the mode, whether an S_SUPPORTED guard is needed).
# GOTO_MMODE returns to M-mode afterward.
_LOWER_MODES = [
    ("smode", GOTO_SMODE, True),
    ("umode", GOTO_UMODE, False),
]


def _write_se0(temp_reg: int, *, enable: bool) -> list[str]:
    """Set (enable=True) or clear (enable=False) SE0 in mstateen0/mstateen0h."""
    action = "CSRS" if enable else "CSRC"
    description = "set SE0=1" if enable else "clear SE0=0"
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, 0x8000000000000000)  # SE0 = bit 63 of mstateen0",
        f"{action}(mstateen0, x{temp_reg})  # {description}",
        "#else",
        f"LI(x{temp_reg}, 0x80000000)  # SE0 = bit 31 of mstateen0h",
        f"{action}(mstateen0h, x{temp_reg})  # {description}",
        "#endif",
    ]


def _save_mstateen(save_reg: int, save_regh: int) -> list[str]:
    """Save mstateen0 (and mstateen0h on RV32) into separate registers."""
    return [
        f"CSRR(x{save_reg}, mstateen0)  # save mstateen0",
        "#if __riscv_xlen == 32",
        f"CSRR(x{save_regh}, mstateen0h)  # save mstateen0h on RV32",
        "#endif",
    ]


def _restore_mstateen(save_reg: int, save_regh: int) -> list[str]:
    """Restore mstateen0 (and mstateen0h on RV32) from separate registers."""
    return [
        f"CSRW(mstateen0, x{save_reg})  # restore mstateen0",
        "#if __riscv_xlen == 32",
        f"CSRW(mstateen0h, x{save_regh})  # restore mstateen0h on RV32",
        "#endif",
    ]


# ---------------------------------------------------------------------------
# cp_mstateen0_se0_{zero,one}_controls_sstateen0
#   Cross: csrops × priv_mode_s × se0_{zero,one} × sstateen_csrs
#   Must run from S-mode (priv_mode_s), not M-mode. With SE0=0 the sstateen0
#   access must trap; with SE0=1 it is permitted.
# ---------------------------------------------------------------------------


def _generate_se0_controls_sstateen0(test_data: TestData, *, se0: int) -> list[str]:
    state_word = "one" if se0 else "zero"
    coverpoint = f"cp_mstateen0_se0_{state_word}_controls_sstateen0"
    covergroup = "Ssstateen_cg"
    detail = "SE0=1 (access permitted)" if se0 else "SE0=0 (should trap)"

    lines = [comment_banner(coverpoint, f"CSR ops to sstateen0 from S-mode with mstateen0.{detail}")]

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, ones_reg = test_data.int_regs.get_registers(5)

    lines.extend(
        [
            f"CSRR(x{save_sstateen}, sstateen0)  # save sstateen0",
            f"LI(x{ones_reg}, -1)",
        ]
    )
    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    lines.extend(_write_se0(temp_reg, enable=bool(se0)))

    # Must sample from S-mode to hit the priv_mode_s bin
    lines.append(GOTO_SMODE)

    for op in CSR_OPS:
        insn = f"{op}(x{temp_reg}, sstateen0)" if op == "CSRR" else f"{op}(x{temp_reg}, sstateen0, x{ones_reg})"
        lines.extend(
            [
                "",
                test_data.add_testcase(f"sstateen0_{op.lower()}_se0_{se0}_smode", coverpoint, covergroup),
                insn,
                "nop",
            ]
        )

    lines.append(GOTO_MMODE)
    lines.extend(["", f"CSRW(sstateen0, x{save_sstateen})  # restore sstateen0"])
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, ones_reg])
    return lines


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
    lines.append(GOTO_UMODE)

    for csr in sstateen_csrs:
        for op in CSR_OPS:
            if op == "CSRR":
                insn = f"{op}(x{temp_reg}, {csr})  # illegal from U-mode"
            else:
                insn = f"{op}(x{temp_reg}, {csr}, x{temp_reg})  # illegal from U-mode"
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode_se0_1", coverpoint, covergroup),
                    insn,
                    "nop",
                ]
            )

    lines.append(GOTO_MMODE)
    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: priv_mode_s × sstateen_walk_csr × csrops × csr_walk × se0_one
#   Must run from S-mode with SE0=1. csr_walk_test covers csrw+csrs+csrc
#   internally (walking-1s uses CSRW+CSRS, walking-0s uses CSRW+CSRC).
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
            "#if __riscv_xlen == 64",
            f"CSRR(x{save_mstateen_se0}, mstateen0)  # save mstateen0 on RV64",
            "#elif __riscv_xlen == 32",
            f"CSRR(x{save_mstateen_se0}, mstateen0h)  # save mstateen0h on RV32",
            "#endif",
        ]
    )
    lines.extend(_write_se0(temp_reg, enable=True))

    # The walk must be sampled in S-mode so the priv_mode_s bin is hit. csr_walk_test
    # emits CSRW+CSRS (walking-1s) and CSRW+CSRC (walking-0s), satisfying the csrops
    # cross.
    lines.append(GOTO_SMODE)
    test_data.int_regs.return_registers([temp_reg])
    lines.extend(
        [
            "",
            test_data.add_testcase("sstateen0_walk_se0_1_smode", coverpoint, covergroup),
        ]
    )
    lines.extend(csr_walk_test(test_data, ("sstateen0", 0x7), covergroup, coverpoint))

    lines.append(GOTO_MMODE)
    lines.extend(
        [
            "#if __riscv_xlen == 64",
            f"CSRW(mstateen0, x{save_mstateen_se0})  # restore mstateen0 on RV64",
            "#elif __riscv_xlen == 32",
            f"CSRW(mstateen0h, x{save_mstateen_se0})  # restore mstateen0h on RV32",
            "#endif",
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
    for mode_label, enter_line, needs_guard in _LOWER_MODES:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for jvt_state in [0, 1]:
            jvt_action = "CSRC" if jvt_state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"{INDENT}# SE0=1, sstateen0.JVT={jvt_state}, {mode_label}",
                    f"CSRR(x{save_sstateen}, sstateen0)  # save sstateen0",
                    f"CSRR(x{save_jvt}, jvt)  # save jvt",
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
            lines.append(enter_line)
            for op in CSR_OPS:
                insn = f"{op}(x{temp_reg}, jvt)" if op == "CSRR" else f"{op}(x{temp_reg}, jvt, x{ones_reg})"
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"{op.lower()}_jvt_se0_1_jvt_{jvt_state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        insn,
                        "nop",
                    ]
                )
            lines.append(GOTO_MMODE)
            lines.extend(
                [
                    f"CSRW(sstateen0, x{save_sstateen})  # restore sstateen0",
                    f"CSRW(jvt, x{save_jvt})  # restore jvt",
                ]
            )
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

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
        fcsr_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_line, needs_guard in _LOWER_MODES:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(
                [
                    "",
                    f"{INDENT}# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"CSRR(x{save_sstateen}, sstateen0)",
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
            lines.append(enter_line)
            for csr in fp_csrs:
                for op in CSR_OPS:
                    insn = f"{op}(x{temp_reg}, {csr})" if op == "CSRR" else f"{op}(x{temp_reg}, {csr}, x{save_reg})"
                    lines.extend(
                        [
                            "",
                            test_data.add_testcase(
                                f"{op.lower()}_{csr}_se0_1_fcsr{fcsr_bit}_{mode_label}",
                                coverpoint,
                                covergroup,
                            ),
                            f"CSRR(x{save_reg}, {csr})  # read operand for write-back ops",
                            insn,
                            "nop",
                        ]
                    )
            lines.append(GOTO_MMODE)
            lines.append(f"CSRW(sstateen0, x{save_sstateen})  # restore sstateen0")
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

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
        fcsr_action = "CSRC" if fcsr_bit == 0 else "CSRS"
        for mode_label, enter_line, needs_guard in _LOWER_MODES:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(
                [
                    "",
                    f"{INDENT}# SE0=1, sstateen0.FCSR={fcsr_bit}, {mode_label}",
                    f"CSRR(x{save_sstateen}, sstateen0)",
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
                        "nop",
                    ]
                )
            lines.append(GOTO_MMODE)
            lines.append(f"CSRW(sstateen0, x{save_sstateen})  # restore sstateen0")
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg1, temp_reg2, temp_reg3, save_mstateen, save_mstatenh, save_sstateen])
    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Ssstateen",
    required_extensions=["S", "Zicsr", "Smstateen", "Ssstateen"],
    march_extensions=["Ssstateen", "Smstateen", "Zicsr", "Zcmt", "Zfinx"],
)
def make_ssstateen(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Ssstateen state-enable extension testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    # Unconditional coverpoints — required by all Ssstateen targets
    tc.code.extend(_generate_se0_controls_sstateen0(test_data, se0=0))
    tc.code.extend(_generate_se0_controls_sstateen0(test_data, se0=1))
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
