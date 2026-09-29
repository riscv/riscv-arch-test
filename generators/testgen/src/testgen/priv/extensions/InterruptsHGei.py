##################################
# priv/extensions/InterruptsHGei.py
#
# Guest external interrupt tests, which need the platform to raise hgeip bits.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""InterruptsHGei guest external interrupt test generator.

hgeip is read-only, so only the platform can raise a guest external interrupt, through the optional
RVMODEL_SET/CLR_GUEST_EXT_INT hooks (UDB_SGEI_INTR_IMPL).  Every test here uses those hooks, so they are kept apart
from InterruptsH and InterruptsHSm and produce no testcases when the hooks are undefined.

The suite boots to HS-mode.  The m file reads mip from M-mode with a guest external interrupt pending.  The hs file
covers hgeip and hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI priority.  The hooks may reach IMSIC state below
M-mode (vstopei, vsiselect and vsireg), so the hs file first sets mstateen0.IMSIC, AIA and CSRIND.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import REG_TRIGGER_DEFINES, int_macro
from testgen.priv.extensions.InterruptsH import S_INTS
from testgen.priv.registry import add_priv_test_generator

_CG = "InterruptsHGei_hs_cg"
_CG_M = "InterruptsHGei_m_cg"

# Let the hooks reach IMSIC state (vstopei, vsiselect and vsireg) from HS-mode
IMSIC_STATEEN_ON = (
    "#ifdef SMSTATEEN_SUPPORTED",
    "#if __riscv_xlen == 64",
    "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0, MSTATEEN0_IMSIC | MSTATEEN0_AIA | MSTATEEN0_CSRIND)",
    "#else",
    "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0H, MSTATEEN0H_IMSIC | MSTATEEN0H_AIA | MSTATEEN0H_CSRIND)",
    "#endif",
    "#endif",
)


def _gei(op: str, gei: int, tmp_reg: int) -> list[str]:
    """Raise (SET) or clear (CLR) guest external interrupt gei through the platform, and wait for hgeip."""
    return [f"RVMODEL_{op}_GUEST_EXT_INT({gei}, a1, a2)", f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})"]


def _mip_tests(test_data: TestData) -> list[str]:
    """Read mip from M-mode with guest external interrupt 1 pending and enabled in hgeie."""
    tmp_reg, check_reg = test_data.int_regs.get_registers(2)
    lines = [
        "#ifdef UDB_SGEI_INTR_IMPL",
        "RVTEST_TSBI_GOTO_MMODE",
        comment_banner("cp_mip_gilen", "With guest external interrupt 1 pending and enabled in hgeie, read mip"),
        f"LI(x{tmp_reg}, 2)",
        f"csrw hgeie, x{tmp_reg}",
        *_gei("SET", 1, tmp_reg),
        f"LI(x{tmp_reg}, MIP_HS_MASK)",
        test_data.add_testcase("hgeip_1", "cp_mip_gilen", _CG_M),
        f"csrr x{check_reg}, mip",
        f"and x{check_reg}, x{check_reg}, x{tmp_reg}",
        write_sigupd(check_reg, test_data),
        *_gei("CLR", 1, tmp_reg),
        "csrw hgeie, zero",
        "RVTEST_TSBI_GOTO_SMODE",
        "#endif // UDB_SGEI_INTR_IMPL",
    ]
    test_data.int_regs.return_registers([tmp_reg, check_reg])
    return lines


def _sgei_tests(test_data: TestData) -> list[str]:
    """Guest external interrupts: hgeip and hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI priority."""
    tmp_reg = test_data.int_regs.get_register()
    geis = range(1, 64)

    def each_gei(body: list[str], gei: int) -> list[str]:
        """body for one guest external interrupt, assembled only when GEILEN is at least gei."""
        return [f"#if {gei} <= UDB_NUM_EXTERNAL_GUEST_INTERRUPTS", *body, "#endif"]

    def all_gei(op: str) -> list[str]:
        """Raise or clear every implemented guest external interrupt."""
        lines = []
        for gei in geis:
            lines.extend(each_gei(_gei(op, gei, tmp_reg), gei))
        return lines

    def check(bin_name: str, coverpoint: str, hgeie: int | str) -> list[str]:
        """Write hgeie, then record hgeip and hip."""
        return [
            f"LI(x{tmp_reg}, {hgeie})",
            test_data.add_testcase(bin_name, coverpoint, _CG),
            f"csrw hgeie, x{tmp_reg}",
            f"csrr x{tmp_reg}, hgeip",
            write_sigupd(tmp_reg, test_data),
            f"csrr x{tmp_reg}, hip",
            write_sigupd(tmp_reg, test_data),
        ]

    lines = [
        "#ifdef UDB_SGEI_INTR_IMPL",
        comment_banner(
            "cp_trigger_sgei",
            "With guest external interrupt 1 pending and enabled in hgeie, set hie.SGEIE = 0/1 with\n"
            "sstatus.SIE = 0/1.  hip.SGEIP = 1; HS-mode takes cause 12 when SIE = 1 and SGEIE = 1",
        ),
        "csrw hideleg, zero",
        "csrw hie, zero",
        f"LI(x{tmp_reg}, 2)",
        f"csrw hgeie, x{tmp_reg}",
    ]
    for sie in (0, 1):
        for ie in (0, 1):
            lines.extend(
                [
                    f"csr{'s' if sie else 'c'}i sstatus, SSTATUS_SIE",
                    *_gei("SET", 1, tmp_reg),
                    f"LI(x{tmp_reg}, {'MIP_SGEIP' if ie else 0})",
                    test_data.add_testcase(f"sie{sie}_sgeie{ie}", "cp_trigger_sgei", _CG),
                    f"csrw hie, x{tmp_reg}",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                    "csrci sstatus, SSTATUS_SIE",
                    f"csrr x{tmp_reg}, hip",
                    write_sigupd(tmp_reg, test_data),
                    *_gei("CLR", 1, tmp_reg),
                    "csrw hie, zero",
                ]
            )
    lines.append(
        comment_banner(
            "cp_priority_sgei, cp_priority_sgei_s",
            "With guest external interrupt 1 and hvip = 0x444 pending, hideleg = 0, hie = 0x1444, sie = 1s and\n"
            "SEI, STI, SSI or no S-level interrupt pending, set sstatus.SIE.  The S-level interrupt is taken\n"
            "first, then SGEI, VSEI, VSSI and VSTI",
        )
    )
    for s_int in [None, *S_INTS]:
        coverpoint = "cp_priority_sgei_s" if s_int else "cp_priority_sgei"
        lines.extend(
            [
                f"LI(x{tmp_reg}, MIP_VS_MASK)",
                f"csrw hvip, x{tmp_reg}",
                f"LI(x{tmp_reg}, MIP_HS_MASK)",
                f"csrw hie, x{tmp_reg}",
                f"LI(x{tmp_reg}, -1)",
                f"csrw sie, x{tmp_reg}",
                *([f"RVTEST_SET_{int_macro[s_int]}_INT_S"] if s_int else []),
                *_gei("SET", 1, tmp_reg),
                test_data.add_testcase(s_int.lower() if s_int else "sgei", coverpoint, _CG),
                f"csrr x{tmp_reg}, sip",
                write_sigupd(tmp_reg, test_data),
                "csrsi sstatus, SSTATUS_SIE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                "csrci sstatus, SSTATUS_SIE",
                *([f"RVTEST_CLR_{int_macro[s_int]}_INT_S"] if s_int else []),
                *_gei("CLR", 1, tmp_reg),
                "csrw sie, zero",
                "csrw hie, zero",
                "csrw hvip, zero",
            ]
        )
    lines.append(
        comment_banner(
            "cp_hgeie",
            "With sstatus.SIE = 0, for each guest external interrupt i, set hgeie to bit i with hgeip = 0,\n"
            "bit i and every implemented bit.  hip.SGEIP = 1 when hgeip & hgeie != 0",
        )
    )
    for pending in ("none", "i", "all"):
        if pending == "all":
            lines.extend(all_gei("SET"))
        for gei in geis:
            body = [
                *(_gei("SET", gei, tmp_reg) if pending == "i" else []),
                *check(f"hgeie_{gei}_hgeip_{pending}", "cp_hgeie", 1 << gei),
                *(_gei("CLR", gei, tmp_reg) if pending == "i" else []),
            ]
            lines.extend(each_gei(body, gei))
        if pending == "all":
            lines.extend(all_gei("CLR"))
    lines.append(
        comment_banner(
            "cp_trigger_vsei_hgeip",
            "With hvip = hideleg = hie = 0, for each guest external interrupt i, set hstatus.VGEIN = i with\n"
            "hgeip = 0, bit i and every implemented bit but i, and hgeie bit i = 0/1.  hip.VSEIP = hgeip[i]",
        )
    )
    # "others" raises every guest external interrupt once and clears bit i around each case
    for pending in ("none", "i", "others"):
        if pending == "others":
            lines.extend(all_gei("SET"))
        for gei in geis:
            body = [
                *(_gei("SET", gei, tmp_reg) if pending == "i" else []),
                *(_gei("CLR", gei, tmp_reg) if pending == "others" else []),
                f"LI(x{tmp_reg}, HSTATUS_VGEIN)",
                f"csrc hstatus, x{tmp_reg}",
                f"LI(x{tmp_reg}, {gei << 12:#x})",
                f"csrs hstatus, x{tmp_reg}",
            ]
            for ie in (0, 1):
                body.extend(check(f"vgein_{gei}_hgeip_{pending}_hgeie{ie}", "cp_trigger_vsei_hgeip", ie << gei))
            body.extend(_gei("CLR", gei, tmp_reg) if pending == "i" else [])
            body.extend(_gei("SET", gei, tmp_reg) if pending == "others" else [])
            lines.extend(each_gei(body, gei))
        if pending == "others":
            lines.extend(all_gei("CLR"))
    lines.extend(
        [
            comment_banner(
                "cp_hgeip0",
                "With hgeip = hgeie = every implemented bit and hstatus.VGEIN = 0, hip.SGEIP = 1 and hip.VSEIP = 0",
            ),
            f"LI(x{tmp_reg}, HSTATUS_VGEIN)",
            f"csrc hstatus, x{tmp_reg}",
            *all_gei("SET"),
            *check("vgein_0", "cp_hgeip0", -1),
            *all_gei("CLR"),
            "csrw hgeie, zero",
            "#endif // UDB_SGEI_INTR_IMPL",
        ]
    )
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "InterruptsHGei",
    required_extensions=["H"],
    extra_defines=[*REG_TRIGGER_DEFINES, "#define BOOT_TO_SMODE"],
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_interruptshgei(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the InterruptsHGei guest external interrupt suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "m")
    tc.code.extend(_mip_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "hs")
    tc.code.extend([*IMSIC_STATEEN_ON, *_sgei_tests(test_data)])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
