# Smstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Smstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MSTATEEN_CSRS_64 = ["mstateen0", "mstateen1", "mstateen2", "mstateen3"]
MSTATEEN_CSRS_H = ["mstateen0h", "mstateen1h", "mstateen2h", "mstateen3h"]

CSR_OPS = ["CSRRW", "CSRRS", "CSRRC", "CSRR"]
# Subset used for walking-ones / cross coverpoints (excludes read-only CSRR)
CSR_OPS_RW = ["CSRRW", "CSRRS", "CSRRC"]


def _enter_umode(test_data: TestData, temp_reg: int) -> list[str]:
    return ["\tRVTEST_GOTO_LOWER_MODE Umode  # enter U-mode"]


def _enter_smode(test_data: TestData, temp_reg: int) -> list[str]:
    return ["\tRVTEST_GOTO_LOWER_MODE Smode  # enter S-mode"]


def _enter_mmode(_test_data: TestData, _temp_reg: int) -> list[str]:
    """M-mode is the default; emitting a comment keeps the assembly readable."""
    return ["\t# already in M-mode"]


def _return_mmode(test_data: TestData, temp_reg: int) -> list[str]:
    return ["\tRVTEST_GOTO_MMODE  # return to M-mode"]


def _csr_insn(op: str, rd: int, csr: str, rs1: int) -> str:
    """Emit a single CSR instruction line. CSRR only takes (rd, csr)."""
    if op == "CSRR":
        return f"\t{op}(x{rd}, {csr})"
    return f"\t{op}(x{rd}, {csr}, x{rs1})"


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses
#   Cross: priv_mode_s_u × mstateen_csrs × csrops
#   All CSR ops to mstateenN CSRs from U-mode AND S-mode — must trap.
# ---------------------------------------------------------------------------


def _generate_csr_illegal_accesses(test_data: TestData) -> list[str]:
    coverpoint = "cp_csr_illegal_accesses"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "All CSR ops to mstateenN CSRs from U-mode and S-mode — must trap (M-only CSRs)",
        )
    ]

    (temp_reg,) = test_data.int_regs.get_registers(1, exclude_regs=[0])

    # ── U-mode ──────────────────────────────────────────────────────────────
    lines.extend(_enter_umode(test_data, temp_reg))

    for csr in MSTATEEN_CSRS_64:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "\tnop",
                ]
            )

    lines.append("#if __riscv_xlen == 32")
    for csr in MSTATEEN_CSRS_H:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_umode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "\tnop",
                ]
            )
    lines.append("#endif  // __riscv_xlen == 32")

    lines.extend(_return_mmode(test_data, temp_reg))

    # ── S-mode ──────────────────────────────────────────────────────────────
    lines.append("#ifdef S_SUPPORTED")
    lines.extend(_enter_smode(test_data, temp_reg))

    for csr in MSTATEEN_CSRS_64:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_smode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "\tnop",
                ]
            )

    lines.append("#if __riscv_xlen == 32")
    for csr in MSTATEEN_CSRS_H:
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"{csr}_{op.lower()}_smode", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, csr, temp_reg),
                    "\tnop",
                ]
            )
    lines.append("#endif  // __riscv_xlen == 32")

    lines.extend(_return_mmode(test_data, temp_reg))
    lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: mstateen_walk_csrs × csrops × csr_walk
#   mstateen_walk_csrs = mstateen0 always, mstateen0h on RV32 only.
# ---------------------------------------------------------------------------


def _generate_walking_ones(test_data: TestData) -> list[str]:
    coverpoint = "cp_walking_ones"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "Walking-1 and walking-0 patterns on mstateen0 (+ mstateen0h on RV32) from M-mode",
        )
    ]

    # mstateen0 — always (RV32 and RV64)
    lines.extend(
        [
            "",
            test_data.add_testcase("mstateen0_walk", coverpoint, covergroup),
        ]
    )
    lines.extend(csr_walk_test(test_data, ("mstateen0", 0xDF80000000000006), covergroup, coverpoint))

    # mstateen0h — RV32 only
    lines.append("#if __riscv_xlen == 32")
    lines.extend(
        [
            "",
            test_data.add_testcase("mstateen0h_walk", coverpoint, covergroup),
        ]
    )
    lines.extend(csr_walk_test(test_data, ("mstateen0h", 0xDF800000), covergroup, coverpoint))
    lines.append("#endif  // __riscv_xlen == 32")

    return lines


# ---------------------------------------------------------------------------
# cp_envcfg
#   Cross: csrops × priv_mode_m_maybes_u × senvcfg_csr × envcfg_state
#   Must cover M-mode, S-mode, and U-mode (priv_mode_m_maybes_u).
# ---------------------------------------------------------------------------


def _generate_envcfg(test_data: TestData) -> list[str]:
    coverpoint = "cp_envcfg"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on senvcfg from M/S/U-mode with mstateen0.envcfg (bit 62) enabled and disabled",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    ENVCFG_BIT_MASK_64 = "0x4000000000000000"  # bit 62 of mstateen0
    ENVCFG_BIT_MASK_32 = "0x40000000"  # bit 30 of mstateen0h (logical bit 62)

    lines.append(f"\tLI(x{ones_reg}, -1)")

    # All three modes required by priv_mode_m_maybes_u
    modes = [
        ("mmode", _enter_mmode, False),
        ("smode", _enter_smode, True),  # guarded by S_SUPPORTED
        ("umode", _enter_umode, False),
    ]

    for state in [1, 0]:
        bit_action = "CSRS" if state == 1 else "CSRC"
        lines.extend(
            [
                "",
                f"\t# Set mstateen0.envcfg = {state} from M-mode",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {ENVCFG_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {ENVCFG_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )

        for mode_label, enter_fn, needs_guard in modes:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(enter_fn(test_data, temp_reg))
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"senvcfg_{op.lower()}_envcfg{state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        _csr_insn(op, temp_reg, "senvcfg", ones_reg),
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_imsic
# ---------------------------------------------------------------------------


def _generate_imsic(test_data: TestData) -> list[str]:
    coverpoint = "cp_imsic"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on stopei/vstopei with mstateen0.imsic (bit 58) disabled and enabled",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    IMSIC_BIT_MASK_64 = "0x0400000000000000"  # bit 58
    IMSIC_BIT_MASK_32 = "0x04000000"  # bit 26 of mstateen0h

    imsic_csrs = ["stopei", "vstopei"]

    lines.append(f"\tLI(x{ones_reg}, -1)")

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.imsic = {state}",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {IMSIC_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {IMSIC_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        for csr in imsic_csrs:
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_imsic{state}", coverpoint, covergroup),
                        _csr_insn(op, temp_reg, csr, ones_reg),
                        "\tnop",
                    ]
                )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_aia
# ---------------------------------------------------------------------------


def _generate_aia(test_data: TestData) -> list[str]:
    coverpoint = "cp_aia"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on AIA CSRs with mstateen0.aia (bit 59) disabled and enabled",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    AIA_BIT_MASK_64 = "0x0800000000000000"  # bit 59
    AIA_BIT_MASK_32 = "0x08000000"  # bit 27 of mstateen0h

    lines.append(f"\tLI(x{ones_reg}, -1)")

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.aia = {state}",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {AIA_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {AIA_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )
        lines.append("#if __riscv_xlen == 64")
        for csr in ["sie", "sip"]:
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_aia{state}", coverpoint, covergroup),
                        _csr_insn(op, temp_reg, csr, ones_reg),
                        "\tnop",
                    ]
                )
        lines.append("#else  // RV32")
        for csr in ["sieh", "siph"]:
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op.lower()}_aia{state}", coverpoint, covergroup),
                        _csr_insn(op, temp_reg, csr, ones_reg),
                        "\tnop",
                    ]
                )
        lines.append("#endif")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt_access
# ---------------------------------------------------------------------------


def _generate_jvt_access(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt_access"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on jvt with mstateen0.jvt (bit 2) disabled and enabled from M-mode",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    JVT_BIT_MASK = 1 << 2

    lines.append(f"\tLI(x{ones_reg}, -1)")

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.jvt = {state}",
                f"\tLI(x{temp_reg}, {JVT_BIT_MASK})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
            ]
        )
        for op in CSR_OPS:
            lines.extend(
                [
                    "",
                    test_data.add_testcase(f"jvt_{op.lower()}_jvt{state}", coverpoint, covergroup),
                    _csr_insn(op, temp_reg, "jvt", ones_reg),
                    "\tnop",
                ]
            )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt_lower_mode
#   Cross: priv_mode_s_u × csrops × jvt_csr × jvt_state
#   S-mode and U-mode only .
# ---------------------------------------------------------------------------


def _generate_jvt_lower_mode(test_data: TestData) -> list[str]:
    coverpoint = "cp_jvt_lower_mode"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on jvt from U/S-mode with mstateen0.jvt (bit 2) disabled and enabled",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    JVT_BIT_MASK = 1 << 2

    lines.append(f"\tLI(x{ones_reg}, -1)")

    modes = [
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for mode_label, enter_fn, needs_guard in modes:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "CSRC" if state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"\t# mstateen0.jvt = {state}, {mode_label}",
                    f"\tLI(x{temp_reg}, {JVT_BIT_MASK})",
                    f"\t{bit_action}(mstateen0, x{temp_reg})",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"jvt_{op.lower()}_jvt{state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        _csr_insn(op, temp_reg, "jvt", ones_reg),
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_context
#   Cross: csrops × scontext_csr × context_state × priv_mode_m_maybes_u
# ---------------------------------------------------------------------------


def _generate_context(test_data: TestData) -> list[str]:
    coverpoint = "cp_context"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on scontext with mstateen0.context (bit 57) disabled and enabled — M/S/U-mode",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    CONTEXT_BIT_MASK_64 = "0x0200000000000000"  # bit 57
    CONTEXT_BIT_MASK_32 = "0x02000000"  # bit 25 of mstateen0h

    lines.append(f"\tLI(x{ones_reg}, -1)")

    modes = [
        ("mmode", _enter_mmode, False),
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.context = {state}",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {CONTEXT_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {CONTEXT_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )

        for mode_label, enter_fn, needs_guard in modes:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(enter_fn(test_data, temp_reg))
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"scontext_{op.lower()}_context{state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        _csr_insn(op, temp_reg, "scontext", ones_reg),
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_p1p13
#   Cross: csrops × p1p13_state × hedelegh_csr × priv_mode_m_maybes_u
# ---------------------------------------------------------------------------


def _generate_p1p13(test_data: TestData) -> list[str]:
    coverpoint = "cp_p1p13"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on hedelegh with mstateen0.p1p13 (bit 56) disabled and enabled — M/S/U-mode",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    P1P13_BIT_MASK_64 = "0x0100000000000000"  # bit 56
    P1P13_BIT_MASK_32 = "0x01000000"  # bit 24 of mstateen0h

    lines.append(f"\tLI(x{ones_reg}, -1)")

    modes = [
        ("mmode", _enter_mmode, False),
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.p1p13 = {state}",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {P1P13_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {P1P13_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )

        for mode_label, enter_fn, needs_guard in modes:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(enter_fn(test_data, temp_reg))
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"hedelegh_{op.lower()}_p1p13_{state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        _csr_insn(op, temp_reg, "hedelegh", ones_reg),
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_srmcfg
#   Cross: csrops × srmcfg_csr × srmcfg_state × priv_mode_m_maybes_u
# ---------------------------------------------------------------------------


def _generate_srmcfg(test_data: TestData) -> list[str]:
    coverpoint = "cp_srmcfg"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on srmcfg with mstateen0.srmcfg (bit 55) disabled and enabled — M/S/U-mode",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    SRMCFG_BIT_MASK_64 = "0x0080000000000000"  # bit 55
    SRMCFG_BIT_MASK_32 = "0x00800000"  # bit 23 of mstateen0h

    lines.append(f"\tLI(x{ones_reg}, -1)")

    modes = [
        ("mmode", _enter_mmode, False),
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.srmcfg = {state}",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {SRMCFG_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {SRMCFG_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )

        for mode_label, enter_fn, needs_guard in modes:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(enter_fn(test_data, temp_reg))
            for op in CSR_OPS:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(
                            f"srmcfg_{op.lower()}_srmcfg{state}_{mode_label}",
                            coverpoint,
                            covergroup,
                        ),
                        _csr_insn(op, temp_reg, "srmcfg", ones_reg),
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_ctr
#   Cross: csrops × ctr_csrs × ctr_state × priv_mode_m_maybes_u
# ---------------------------------------------------------------------------


def _generate_ctr(test_data: TestData) -> list[str]:
    coverpoint = "cp_ctr"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "CSR ops on sctrdepth/sctrstatus with mstateen0.ctr (bit 54) disabled and enabled — M/S/U-mode",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    CTR_BIT_MASK_64 = "0x0040000000000000"  # bit 54
    CTR_BIT_MASK_32 = "0x00400000"  # bit 22 of mstateen0h

    ctr_csrs = ["sctrdepth", "sctrstatus"]

    lines.append(f"\tLI(x{ones_reg}, -1)")

    modes = [
        ("mmode", _enter_mmode, False),
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for state in [0, 1]:
        bit_action = "CSRC" if state == 0 else "CSRS"
        lines.extend(
            [
                "",
                f"\t# mstateen0.ctr = {state}",
                "#if __riscv_xlen == 64",
                f"\tLI(x{temp_reg}, {CTR_BIT_MASK_64})",
                f"\t{bit_action}(mstateen0, x{temp_reg})",
                "#else",
                f"\tLI(x{temp_reg}, {CTR_BIT_MASK_32})",
                f"\t{bit_action}(mstateen0h, x{temp_reg})",
                "#endif",
            ]
        )

        for mode_label, enter_fn, needs_guard in modes:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(enter_fn(test_data, temp_reg))
            for csr in ctr_csrs:
                for op in CSR_OPS:
                    lines.extend(
                        [
                            "",
                            test_data.add_testcase(
                                f"{csr}_{op.lower()}_ctr{state}_{mode_label}",
                                coverpoint,
                                covergroup,
                            ),
                            _csr_insn(op, temp_reg, csr, ones_reg),
                            "\tnop",
                        ]
                    )
            lines.extend(_return_mmode(test_data, temp_reg))
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_ro_zero  (NEW — was missing entirely)
#   Cross: misa_F × csrops × mstateen0_fcsr_bit
#   Exercises the ignore_bins-covered path where fcsr reads as zero
#   when misa.F is set but mstateen0.fcsr (bit 1) is clear.
# ---------------------------------------------------------------------------


def _generate_fcsr_ro_zero(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_ro_zero"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "misa.F set, mstateen0.fcsr (bit 1) clear — fcsr reads as zero (access-fault path)",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    FCSR_BIT_MASK = 1 << 1  # bit 1 of mstateen0

    lines.extend(
        [
            f"\tLI(x{ones_reg}, -1)",
            "",
            "\t# Ensure misa.F is set (read misa, verify F bit, then proceed)",
            f"\tCSRR(x{temp_reg}, misa)",
            "\t# bit 5 = F; test proceeds assuming F is present per MARCH",
            "",
            "\t# Clear mstateen0.fcsr so fcsr reads zero",
            f"\tLI(x{temp_reg}, {FCSR_BIT_MASK})",
            "\tCSRC(mstateen0, x{temp_reg})",
        ]
    )

    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_ro_zero", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "\tnop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr
# ---------------------------------------------------------------------------


def _generate_fcsr(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "M-mode CSR ops on fcsr under misa.F set and mstateen0.fcsr (bit 1) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    FCSR_BIT_MASK = 1 << 1

    lines.append(f"\tLI(x{ones_reg}, -1)")

    lines.extend(
        [
            "",
            "\t# mstateen0.fcsr = 1 (only meaningful state per ignore_bins)",
            f"\tLI(x{temp_reg}, {FCSR_BIT_MASK})",
            "\tCSRS(mstateen0, x{temp_reg})",
        ]
    )
    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_fcsr1", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "\tnop",
            ]
        )

    lines.extend(
        [
            "",
            "\t# mstateen0.fcsr = 0",
            f"\tLI(x{temp_reg}, {FCSR_BIT_MASK})",
            "\tCSRC(mstateen0, x{temp_reg})",
        ]
    )
    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_fcsr0", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "\tnop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower
#   Cross: priv_mode_s_u × misa_F × mstateen0_fcsr_bit × csrops × fcsr_lower_mode_csrs
#   S-mode and U-mode only .
# ---------------------------------------------------------------------------


def _generate_fcsr_lower(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "S/U-mode CSR ops on frm/fflags/fcsr with mstateen0.fcsr (bit 1) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    FCSR_BIT_MASK = 1 << 1
    fp_csrs = ["frm", "fflags", "fcsr"]

    lines.append(f"\tLI(x{ones_reg}, -1)")

    modes = [
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for mode_label, enter_fn, needs_guard in modes:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "CSRC" if state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"\t# mstateen0.fcsr = {state}, {mode_label}",
                    f"\tLI(x{temp_reg}, {FCSR_BIT_MASK})",
                    f"\t{bit_action}(mstateen0, x{temp_reg})",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for csr in fp_csrs:
                for op in CSR_OPS:
                    lines.extend(
                        [
                            "",
                            test_data.add_testcase(
                                f"{csr}_{op.lower()}_fcsr{state}_{mode_label}",
                                coverpoint,
                                covergroup,
                            ),
                            _csr_insn(op, temp_reg, csr, ones_reg),
                            "\tnop",
                        ]
                    )
            lines.extend(_return_mmode(test_data, temp_reg))
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower_fp_instrs
#   Cross: priv_mode_s_u × misa_F × mstateen0_fcsr_bit × fp_instrs
#   S-mode and U-mode only .
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_lower_fp_instrs"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "FP instructions from U/S-mode with mstateen0.fcsr (bit 1) disabled and enabled",
        )
    ]

    temp_reg, scratch_reg = test_data.int_regs.get_registers(2, exclude_regs=[0, 6, 7, 29])
    FCSR_BIT_MASK = 1 << 1

    fp_instrs = [
        ("fadd.s f0, f1, f2", "fadd_s"),
        ("flw f0, 0(x{scratch})", "flw"),
        ("fcvt.w.s x{temp}, f0", "fcvt_w_s"),
        ("fcvt.s.w f0, x0", "fcvt_s_w"),
        ("fmv.x.w x{temp}, f0", "fmv_x_w"),
        ("fmv.w.x f0, x{temp}", "fmv_w_x"),
        ("fclass.s x{temp}, f0", "fclass_s"),
    ]

    lines.append(f"\tLA(x{scratch_reg}, scratch)  # scratch memory for flw")

    modes = [
        ("umode", _enter_umode, False),
        ("smode", _enter_smode, True),
    ]

    for mode_label, enter_fn, needs_guard in modes:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "CSRC" if state == 0 else "CSRS"
            lines.extend(
                [
                    "",
                    f"\t# mstateen0.fcsr = {state}, {mode_label}",
                    f"\tLI(x{temp_reg}, {FCSR_BIT_MASK})",
                    f"\t{bit_action}(mstateen0, x{temp_reg})",
                ]
            )
            lines.extend(enter_fn(test_data, temp_reg))
            for insn_template, label in fp_instrs:
                insn = insn_template.replace("{temp}", str(temp_reg)).replace("{scratch}", str(scratch_reg))
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{label}_fcsr{state}_{mode_label}", coverpoint, covergroup),
                        f"\t{insn}",
                        "\tnop",
                    ]
                )
            lines.extend(_return_mmode(test_data, temp_reg))
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, scratch_reg])
    return lines


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["S", "Zicsr", "Smstateen"],
    march_extensions=["S", "Smstateen", "Zicsr", "Zcmt"],
)
def make_smstateen(test_data: TestData) -> list[str]:
    """Generate tests for Smstateen state-enable extension testsuite."""
    lines: list[str] = []

    # Unconditional coverpoints — required by all Smstateen targets
    lines.extend(_generate_csr_illegal_accesses(test_data))
    lines.extend(_generate_walking_ones(test_data))
    lines.extend(_generate_envcfg(test_data))

    # cp_imsic — only when IMSIC is present
    lines.append("#ifdef IMSIC_SUPPORTED")
    lines.extend(_generate_imsic(test_data))
    lines.append("#endif  // IMSIC_SUPPORTED")

    # cp_aia — only when AIA is present
    lines.append("#ifdef AIA_SUPPORTED")
    lines.extend(_generate_aia(test_data))
    lines.append("#endif  // AIA_SUPPORTED")

    # cp_jvt_access, cp_jvt_lower_mode — only when Zcmt is present
    lines.append("#ifdef ZCMT_SUPPORTED")
    lines.extend(_generate_jvt_access(test_data))
    lines.extend(_generate_jvt_lower_mode(test_data))
    lines.append("#endif  // ZCMT_SUPPORTED")

    # cp_context — only when Ssdtrig is present
    lines.append("#ifdef SSDTRIG_SUPPORTED")
    lines.extend(_generate_context(test_data))
    lines.append("#endif  // SSDTRIG_SUPPORTED")

    # cp_p1p13 — only when Sm1p13 + Hypervisor present
    lines.append("#ifdef SM1P13_SUPPORTED")
    lines.extend(_generate_p1p13(test_data))
    lines.append("#endif  // SM1P13_SUPPORTED")

    # cp_srmcfg — only when Ssqosid is present
    lines.append("#ifdef SSQOSID_SUPPORTED")
    lines.extend(_generate_srmcfg(test_data))
    lines.append("#endif  // SSQOSID_SUPPORTED")

    # cp_ctr — only when Sctr is present
    lines.append("#ifdef SCTR_SUPPORTED")
    lines.extend(_generate_ctr(test_data))
    lines.append("#endif  // SCTR_SUPPORTED")

    # cp_fcsr, cp_fcsr_ro_zero, cp_fcsr_lower, cp_fcsr_lower_fp_instrs — only when Zfinx present
    lines.append("#ifdef ZFINX_SUPPORTED")
    lines.extend(_generate_fcsr_ro_zero(test_data))
    lines.extend(_generate_fcsr(test_data))
    lines.extend(_generate_fcsr_lower(test_data))
    lines.extend(_generate_fcsr_lower_fp_instrs(test_data))
    lines.append("#endif  // ZFINX_SUPPORTED")

    return lines
