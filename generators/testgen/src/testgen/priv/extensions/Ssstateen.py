# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import arch_block, comment_banner, gated
from testgen.asm.tsbi import tsbi_call
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.Smstateen import (
    CSR_OPS,
    HSTATEEN0_WALK_MASK,
    SAIL_UNMODELED_TESTS,
    STATEEN0_SKIP_BITS,
    bit_controlled_tests,
    stateen_walk,
)
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The sstateen0 bits the walks leave out (STATEEN0_SKIP_BITS in Smstateen.py)
SSTATEEN0_SKIP_BITS = STATEEN0_SKIP_BITS & 0xFFFFFFFF


def _write_mstateen_bit(n: int, bit: int, temp_reg: int, *, enable: bool) -> list[str]:
    """Set (enable=True) or clear (enable=False) bit ``bit`` of mstateen<n> (bit ``bit - 32`` of mstateen<n>h on RV32).

    Skipped entirely where Smstateen is absent: mstateenN does not exist there, and an
    illegal access made through T-SBI faults inside the handler rather than in test code,
    which aborts the run. Without Smstateen sstateenN is simply ungated.
    """
    action = "csrs" if enable else "csrc"
    description = f"set bit {bit}" if enable else f"clear bit {bit}"
    return [
        "#ifdef SMSTATEEN_SUPPORTED",
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, {1 << bit:#x})",
        tsbi_call(f"{action} mstateen{n}, x{temp_reg}  # {description}"),
        "#else",
        f"LI(x{temp_reg}, {1 << (bit - 32):#x})",
        tsbi_call(f"{action} mstateen{n}h, x{temp_reg}  # {description} of mstateen{n}"),
        "#endif",
        "#endif  // SMSTATEEN_SUPPORTED",
    ]


def _write_se(n: int, temp_reg: int, *, enable: bool) -> list[str]:
    """Set (enable=True) or clear (enable=False) SE<n>, bit 63 of mstateen<n> (bit 31 of mstateen<n>h on RV32)."""
    return _write_mstateen_bit(n, 63, temp_reg, enable=enable)


def _write_se0(temp_reg: int, *, enable: bool) -> list[str]:
    """Set (enable=True) or clear (enable=False) SE0 in mstateen0/mstateen0h."""
    return _write_se(0, temp_reg, enable=enable)


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
#   Cross: priv_mode_u × sstateen_csrs × csrops × mstateen_se_n_one
#   U-mode only.
# ---------------------------------------------------------------------------


def _generate_csr_illegal_accesses(
    test_data: TestData,
    *,
    covergroup: str = "Ssstateen_cg",
    csrs: list[str] | None = None,
    csrs_rv32: list[str] | None = None,
    modes: tuple[tuple[str, str], ...] = (("umode", "RVTEST_TSBI_GOTO_UMODE"),),
) -> list[str]:
    """CSR ops on ``csrs`` (sstateen0-3 by default) from each of ``modes`` (U-mode by default) with SE0-SE3=1.

    The H group uses it for hstateen0-3 from VS-mode and VU-mode, which always raise virtual instruction.
    """
    coverpoint = "cp_csr_illegal_accesses"
    csrs = csrs or [f"sstateen{n}" for n in range(4)]
    rv32 = csrs_rv32 or []
    mode_names = "/".join(f"{label[:-4].upper()}-mode" for label, _ in modes)

    lines = [
        comment_banner(
            coverpoint,
            f"Attempt CSR ops to {', '.join(csrs)} from {mode_names} with SE0-SE3=1 (should trap)",
        )
    ]

    temp_reg, save_mstateen, save_mstatenh = test_data.int_regs.get_registers(3)

    # Enable every sstateenN at M level so that the accesses trap only for privilege.
    # mstateen1-3 reset to zero and no other test leaves SE1-3 set, so they are cleared afterward.
    lines.extend(_save_mstateen(save_mstateen, save_mstatenh))
    for n in range(4):
        lines.extend(_write_se(n, temp_reg, enable=True))

    for mode_label, enter_line in modes:
        lines.append(enter_line)
        for csr in [*csrs, *rv32]:
            body = []
            for op in CSR_OPS:
                if op == "csrr":
                    insn = f"{op} x{temp_reg}, {csr}  # illegal from {mode_label}"
                else:
                    insn = f"{op} x{temp_reg}, {csr}, x{temp_reg}  # illegal from {mode_label}"
                body.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_{mode_label}_se_1", coverpoint, covergroup),
                        insn,
                    ]
                )
            lines.extend(gated(body, "__riscv_xlen == 32" if csr in rv32 else None))
        lines.append("RVTEST_TSBI_GOTO_SMODE")

    lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))
    for n in range(1, 4):
        lines.extend(_write_se(n, temp_reg, enable=False))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: priv_mode_s × sstateen_walk_csr × csrops × csr_walk × mstateen_se_n_one
#   Must run from S-mode with SEn=1 in the mstateenN matching each sstateenN.
#   csr_walk_test covers csrw+csrs+csrc internally (walking-1s uses csrw+csrs,
#   walking-0s uses csrw+csrc).
# ---------------------------------------------------------------------------


def _generate_walking_ones(
    test_data: TestData,
    *,
    ctl: str = "sstateen",
    mask0: int = 0x7,
    skip0: int = SSTATEEN0_SKIP_BITS,
    covergroup: str = "Ssstateen_cg",
    high_halves: bool = False,
) -> list[str]:
    """Walk <ctl>0-3 from S-mode with the matching SEn=1, checking the bits of <ctl>0 in ``mask0`` and leaving out
    the bits in ``skip0``.

    The H group walks hstateen0-3 from HS-mode, and with ``high_halves`` also hstateen0h-3h on RV32.
    """
    coverpoint = "cp_walking_ones"

    def walk(n: int, mask: int | None, skip: int = 0) -> list[str]:
        return stateen_walk(
            test_data,
            f"{ctl}{n}",
            covergroup=covergroup,
            label=f"{{csr}}_walk_se{n}_1_smode",
            mask=mask,
            skip_bits=skip,
            high_half=high_halves,
        )

    lines = [
        comment_banner(
            coverpoint,
            f"Walking-1 and walking-0 patterns on {ctl}0-3 from S-mode with the matching SEn=1",
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
    lines.extend(walk(0, mask0, skip0))

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

    # sstateen1-3 have no defined bits, so every bit reads zero (norm:stateen_reserved_roz);
    # hstateen1-3 define only bit 63. Each needs SE<n> set in mstateen<n>; mstateen1-3 reset
    # to zero and no other test leaves SE1-3 set, so SE<n> is cleared afterward rather than
    # saved and restored.
    temp_reg = test_data.int_regs.get_register()
    for n in range(1, 4):
        lines.extend(_write_se(n, temp_reg, enable=True))
        lines.extend(walk(n, None))
        lines.extend(_write_se(n, temp_reg, enable=False))
    test_data.int_regs.return_registers([temp_reg])

    return lines


# ---------------------------------------------------------------------------
# cp_jvt
#   Cross: priv_mode_s_u × csrops × jvt_csr × jvt_state × se0_one
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

    for mode_label in ("smode", "umode"):
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
                    f"{jvt_action} sstateen0, x{temp_reg}  # sstateen0.JVT = {jvt_state}",
                ]
            )
            if mode_label == "umode":
                lines.append("RVTEST_TSBI_GOTO_UMODE")
            for op in CSR_OPS:
                insn = f"{op} x{temp_reg}, jvt" if op == "csrr" else f"{op} x{temp_reg}, jvt, x{ones_reg}"
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
            if mode_label == "umode":
                lines.append("RVTEST_TSBI_GOTO_SMODE")
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
#   Cross: priv_mode_s_u × misa_F × se0_one × sstateen0_fcsr_bit × csrops × fcsr_lower_mode_csrs
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

    temp_reg, save_mstateen, save_mstatenh, save_sstateen, wdata_reg = test_data.int_regs.get_registers(5)
    fp_csrs = ["frm", "fflags", "fcsr"]
    FCSR_BIT = 1  # sstateen0 bit 1 = FCSR

    # Write data for csrrw/csrrs/csrrc, set outside the gated region so that only the op under test
    # accesses the FP CSRs. 0 is a legal frm (RNE) and clears fflags.
    lines.append(f"LI(x{wdata_reg}, 0)  # write data for csrrw/csrrs/csrrc")

    for fcsr_bit in [0, 1]:
        fcsr_action = "csrc" if fcsr_bit == 0 else "csrs"
        for mode_label in ("smode", "umode"):
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
                    f"{fcsr_action} sstateen0, x{temp_reg}  # sstateen0.FCSR = {fcsr_bit}",
                ]
            )
            if mode_label == "umode":
                lines.append("RVTEST_TSBI_GOTO_UMODE")
            for csr in fp_csrs:
                for op in CSR_OPS:
                    insn = f"{op} x{temp_reg}, {csr}" if op == "csrr" else f"{op} x{temp_reg}, {csr}, x{wdata_reg}"
                    lines.extend(
                        [
                            "",
                            test_data.add_testcase(
                                f"{op.lower()}_{csr}_se0_1_fcsr{fcsr_bit}_{mode_label}",
                                coverpoint,
                                covergroup,
                            ),
                            insn,
                        ]
                    )
            if mode_label == "umode":
                lines.append("RVTEST_TSBI_GOTO_SMODE")
            lines.append(f"csrw sstateen0, x{save_sstateen}  # restore sstateen0")
            lines.extend(_restore_mstateen(save_mstateen, save_mstatenh))

    test_data.int_regs.return_registers([temp_reg, save_mstateen, save_mstatenh, save_sstateen, wdata_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_fp_instrs
#   Cross: priv_mode_s_u × misa_F × se0_one × sstateen0_fcsr_bit × fp_instrs
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
        for mode_label in ("smode", "umode"):
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
                    f"{fcsr_action} sstateen0, x{temp_reg1}  # sstateen0.FCSR = {fcsr_bit}",
                ]
            )
            if mode_label == "umode":
                lines.append("RVTEST_TSBI_GOTO_UMODE")
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
            if mode_label == "umode":
                lines.append("RVTEST_TSBI_GOTO_SMODE")
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
    march_extensions=["Ssstateen"],
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
    fcsr_lines = [*_generate_fcsr_lower(test_data), *_generate_fcsr_lower_fp_instrs(test_data)]
    tc.code.extend(arch_block(fcsr_lines, "zfinx"))
    tc.code.append("#endif  // ZFINX_SUPPORTED")

    # cp_jvt — only when Zcmt is supported (covers both S-mode and U-mode).  Sail does not model Zcmt
    # (SAIL_UNMODELED_TESTS in Smstateen.py).
    if SAIL_UNMODELED_TESTS:
        tc.code.append("#ifdef ZCMT_SUPPORTED")
        tc.code.extend(arch_block(_generate_jvt(test_data), "zcmt"))
        tc.code.append("#endif  // ZCMT_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


# ---------------------------------------------------------------------------
# H group: hstateen control of VS- and VU-mode access. Like the base tests it boots
# to (H)S-mode and writes mstateen through T-SBI. Ssstateen comprises only the sstateen
# and hstateen CSRs, so the effects of mstateen are tested in the Smstateen H group.
# ---------------------------------------------------------------------------

_H_CG = "Ssstateen_H_cg"

# The H group's modes, entered from HS-mode
_MODES_H = [
    ("hsmode", f"{INDENT}# already in HS-mode", False),
    ("vsmode", "RVTEST_TSBI_GOTO_VSMODE", False),
    ("vumode", "RVTEST_TSBI_GOTO_VUMODE", False),
]

# hstateen0 C, FCSR and JVT, which control the matching sstateen0 bits
_HSTATEEN0_LOW = "(HSTATEEN0_CS | HSTATEEN0_FCSR | HSTATEEN0_JVT)"


def _h_enable_mstateen(temp_reg: int) -> list[str]:
    """With Smstateen, set mstateen0.SE0, ENVCFG and CONTEXT and SE1-SE3, so that HS-mode can reach the state the
    hstateen CSRs control."""
    lines = []
    for bit in (63, 62, 57):
        lines.extend(_write_mstateen_bit(0, bit, temp_reg, enable=True))
    for n in range(1, 4):
        lines.extend(_write_se(n, temp_reg, enable=True))
    return lines


def _h_walking_ones_vs(test_data: TestData) -> list[str]:
    """Walk sstateen0 from VS-mode with hstateen0 C, FCSR and JVT clear and set; sstateen0 bits whose hstateen0 bit
    is 0 read as zero (norm:sstateen_vsmode_access_roz)."""
    coverpoint = "cp_walking_ones_vs"
    temp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns on sstateen0 from VS-mode with hstateen0 C, FCSR and JVT clear and set",
        ),
        *_h_enable_mstateen(temp_reg),
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, HSTATEEN_SSTATEEN)",
        f"csrs hstateen0, x{temp_reg}",
        "#else",
        f"LI(x{temp_reg}, HSTATEENH_SSTATEEN)",
        f"csrs hstateen0h, x{temp_reg}",
        "#endif",
    ]
    for state in (0, 1):
        lines.extend(
            [
                "",
                f"LI(x{temp_reg}, {_HSTATEEN0_LOW})",
                f"{'csrs' if state else 'csrc'} hstateen0, x{temp_reg}  # hstateen0 C, FCSR, JVT = {state}",
                "RVTEST_TSBI_GOTO_VSMODE",
                test_data.add_testcase(f"sstateen0_walk_h{state}_vsmode", coverpoint, _H_CG),
                *csr_walk_test(
                    test_data, ("sstateen0", 0x7), _H_CG, coverpoint, tag=f"_h{state}", skip_bits=SSTATEEN0_SKIP_BITS
                ),
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    test_data.int_regs.return_registers([temp_reg])
    return lines


def _h_gate_tests(test_data: TestData) -> list[str]:
    """CSR ops on sstateen0-3, senvcfg and scontext from HS-, VS- and VU-mode for each value of the hstateen bit
    that controls them.  The bits control VS-mode access but not HS-mode access."""
    common = {"covergroup": _H_CG, "ctl": "hstateen", "modes": _MODES_H, "home": "RVTEST_TSBI_GOTO_SMODE"}
    temp_reg = test_data.int_regs.get_register()
    lines = _h_enable_mstateen(temp_reg)
    test_data.int_regs.return_registers([temp_reg])
    for n in range(4):
        lines.extend(
            bit_controlled_tests(
                test_data,
                coverpoint="cp_hstateen0_se0_controls_sstateen0" if n == 0 else "cp_hstateen_se_controls_sstateen123",
                bit=63,
                bit_name="se",
                n=n,
                banner=f"CSR ops on sstateen{n} from HS/VS/VU-mode with hstateen{n}.SE{n} (bit 63) disabled and enabled",
                csrs=[f"sstateen{n}"],
                check=n > 0,
                preserve=True,
                **common,
            )
        )
    lines.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_envcfg",
            bit=62,
            bit_name="envcfg",
            banner="CSR ops on senvcfg from HS/VS/VU-mode with hstateen0.envcfg (bit 62) disabled and enabled",
            csrs=["senvcfg"],
            preserve=True,
            **common,
        )
    )
    lines.append("#ifdef UDB_SCONTEXT_IMPLEMENTED")
    lines.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_context",
            bit=57,
            bit_name="context",
            banner="CSR ops on scontext from HS/VS/VU-mode with hstateen0.context (bit 57) disabled and enabled",
            csrs=["scontext"],
            preserve=True,
            **common,
        )
    )
    lines.append("#endif  // UDB_SCONTEXT_IMPLEMENTED")
    return lines


@add_priv_test_generator(
    "Ssstateen",
    required_extensions=["Ssstateen", "H"],
    march_extensions=["Ssstateen"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssstateen_h(test_data: TestData) -> list[TestChunk]:
    """Generate the Ssstateen H group tests."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "H_walk")
    tc.code.extend(
        [
            *_generate_walking_ones(
                test_data,
                ctl="hstateen",
                mask0=HSTATEEN0_WALK_MASK,
                skip0=STATEEN0_SKIP_BITS,
                covergroup=_H_CG,
                high_halves=True,
            ),
            *_h_walking_ones_vs(test_data),
            *_generate_csr_illegal_accesses(
                test_data,
                covergroup=_H_CG,
                csrs=[f"hstateen{n}" for n in range(4)],
                csrs_rv32=[f"hstateen{n}h" for n in range(4)],
                modes=(("vsmode", "RVTEST_TSBI_GOTO_VSMODE"), ("vumode", "RVTEST_TSBI_GOTO_VUMODE")),
            ),
        ]
    )

    tc = test_data.new_test_chunk(test_chunks, "H_gate")
    tc.code.extend(_h_gate_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
