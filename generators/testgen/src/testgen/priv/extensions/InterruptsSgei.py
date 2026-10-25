##################################
# priv/extensions/InterruptsSgei.py
#
# Interrupts_Sgei and Interrupts_SgeiSm groups: guest external interrupts, which need the platform to raise hgeip bits.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Interrupts guest external interrupt test generator (from the hypervisor branch's InterruptsHGei).

hgeip is read-only, so only the platform can raise a guest external interrupt, through the RVMODEL_SET/CLR_GUEST_EXT_INT
hooks that a DUT with H and GEILEN > 0 (RVTEST_SGEI_INTR_IMPL) must define; the tests call them through
RVTEST_SET/CLR_GUEST_EXT_INT_M/_S.  Every test here uses those hooks, so they are kept in their own groups and
produce no testcases when GEILEN = 0.

Interrupts_Sgei boots to HS-mode.  Its trigger file takes SGEI from HS, U, VS and VU modes; its hs file covers hgeip
and hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI priority.  Interrupts_SgeiSm boots to M-mode with mideleg = 0 and
takes SGEI from every mode: SGEI still goes to HS-mode because mideleg[12] is read-only one.  The hooks may reach
IMSIC state below M-mode (vstopei, vsiselect and vsireg), so each file first sets mstateen0.IMSIC, AIA and CSRIND.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import int_macro
from testgen.priv.registry import add_priv_test_generator

_CG = "Interrupts_Sgei_cg"
_CG_SM = "Interrupts_SgeiSm_cg"

# S-level interrupts that preempt SGEI, raised by RVTEST_SET_<macro>_INT_S
S_INTS = ["SEI", "STI", "SSI"]

# Let the hooks reach IMSIC state (vstopei, vsiselect and vsireg) below M-mode
IMSIC_STATEEN_ON = (
    "#ifdef SMSTATEEN_SUPPORTED",
    "#if __riscv_xlen == 64",
    "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0, MSTATEEN0_IMSIC | MSTATEEN0_AIA | MSTATEEN0_CSRIND)",
    "#else",
    "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0H, MSTATEEN0H_IMSIC | MSTATEEN0H_AIA | MSTATEEN0H_CSRIND)",
    "#endif",
    "#endif",
)

# Modes a test enters with RVTEST_TSBI_GOTO_<mode>MODE, by the name of the GOTO macro
_GOTO = {"HS": "S", "U": "U", "VS": "VS", "VU": "VU"}


def _gei(op: str, gei: int, tmp_reg: int, mode: str = "S") -> list[str]:
    """Raise (SET) or clear (CLR) guest external interrupt gei through the platform from mode M or S, and wait for
    hgeip."""
    return [f"RVTEST_{op}_GUEST_EXT_INT_{mode}({gei})", f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})"]


def _trigger_tests(test_data: TestData) -> list[str]:
    """SGEI goes to HS-mode.  HS-mode takes it when sstatus.SIE = 1 and hie.SGEIE = 1; U, VS and VU modes take it
    whenever hie.SGEIE = 1."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        "#ifdef RVTEST_SGEI_INTR_IMPL",
        comment_banner(
            "cp_trigger_sgei",
            "With guest external interrupt 1 pending and enabled in hgeie, write hie.SGEIE = 0/1 with\n"
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
            "cp_trigger_sgei_lower",
            "With guest external interrupt 1 pending and enabled in hgeie, sstatus.SIE = 0 and hie.SGEIE = 0/1,\n"
            "enter U, VS or VU mode.  HS-mode takes cause 12 on the mret into the mode when SGEIE = 1",
        )
    )
    for mode in ("U", "VS", "VU"):
        for ie in (0, 1):
            lines.extend(
                [
                    f"LI(x{tmp_reg}, {'MIP_SGEIP' if ie else 0})",
                    f"csrw hie, x{tmp_reg}",
                    *_gei("SET", 1, tmp_reg),
                    test_data.add_testcase(f"{mode.lower()}_sgeie{ie}", "cp_trigger_sgei_lower", _CG),
                    f"RVTEST_TSBI_GOTO_{_GOTO[mode]}MODE",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                    "RVTEST_TSBI_GOTO_SMODE",
                    f"csrr x{tmp_reg}, hip",
                    write_sigupd(tmp_reg, test_data),
                    *_gei("CLR", 1, tmp_reg),
                    "csrw hie, zero",
                ]
            )
    lines.extend(["csrw hgeie, zero", "#endif // RVTEST_SGEI_INTR_IMPL"])
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _trigger_sm_tests(test_data: TestData) -> list[str]:
    """With mideleg = 0, SGEI still goes to HS-mode.  M-mode never takes it; HS-mode takes it when sstatus.SIE = 1
    and hie.SGEIE = 1; U, VS and VU modes take it whenever hie.SGEIE = 1."""
    tmp_reg, check_reg = test_data.int_regs.get_registers(2)
    lines = [
        "#ifdef RVTEST_SGEI_INTR_IMPL",
        comment_banner(
            "cp_trigger_sgei",
            "With mideleg = 0 and guest external interrupt 1 pending and enabled in hgeie, set mstatus.MIE = 0/1,\n"
            "mstatus.SIE = 0/1 and hie.SGEIE = 0/1, then read mip in M-mode or enter HS, U, VS or VU mode",
        ),
        "csrw mideleg, zero",
        "csrw hideleg, zero",
        "csrw hie, zero",
        f"LI(x{tmp_reg}, 2)",
        f"csrw hgeie, x{tmp_reg}",
    ]
    for mode in ("M", *_GOTO):
        for mie in (0, 1):
            for sie in (0, 1):
                for ie in (0, 1):
                    bin_name = f"{mode.lower()}_mie{mie}_sie{sie}_sgeie{ie}"
                    if mode == "M":
                        body = [
                            f"LI(x{tmp_reg}, MIP_HS_MASK)",
                            test_data.add_testcase(bin_name, "cp_trigger_sgei", _CG_SM),
                            f"csrr x{check_reg}, mip",
                            f"and x{check_reg}, x{check_reg}, x{tmp_reg}",
                            write_sigupd(check_reg, test_data),
                        ]
                    else:
                        body = [
                            test_data.add_testcase(bin_name, "cp_trigger_sgei", _CG_SM),
                            f"RVTEST_TSBI_GOTO_{_GOTO[mode]}MODE",
                            f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                            "RVTEST_TSBI_GOTO_MMODE",
                            f"csrr x{check_reg}, hip",
                            write_sigupd(check_reg, test_data),
                        ]
                    lines.extend(
                        [
                            f"LI(x{tmp_reg}, {'MIP_SGEIP' if ie else 0})",
                            f"csrw hie, x{tmp_reg}",
                            f"csr{'s' if sie else 'c'}i mstatus, MSTATUS_SIE",
                            *_gei("SET", 1, tmp_reg, "M"),
                            f"csr{'s' if mie else 'c'}i mstatus, MSTATUS_MIE",
                            *body,
                            "csrci mstatus, MSTATUS_MIE",
                            *_gei("CLR", 1, tmp_reg, "M"),
                            "csrw hie, zero",
                        ]
                    )
    lines.extend(["csrci mstatus, MSTATUS_SIE", "csrw hgeie, zero", "#endif // RVTEST_SGEI_INTR_IMPL"])
    test_data.int_regs.return_registers([tmp_reg, check_reg])
    return lines


def _sgei_tests(test_data: TestData) -> list[str]:
    """Guest external interrupts in HS-mode: hgeip and hgeie, hip.SGEIP, hstatus.VGEIN and the SGEI priority."""
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

    lines = ["#ifdef RVTEST_SGEI_INTR_IMPL"]
    lines.append(
        comment_banner(
            "cp_priority_sgei",
            "With guest external interrupt 1 and hvip = 0x444 pending, hideleg = 0, hie = 0x1444, sie = 1s and\n"
            "SEI, STI, SSI or no S-level interrupt pending, set sstatus.SIE.  The S-level interrupt is taken\n"
            "first, then SGEI, VSEI, VSSI and VSTI",
        )
    )
    for s_int in [None, *S_INTS]:
        coverpoint = "cp_priority_sgei"
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
    # With GEILEN = 1, "all" is the same case as "i", and "others" below is the same case as "none"
    for pending in ("none", "i", "all"):
        if pending == "all":
            lines.extend(["#if UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 2", *all_gei("SET")])
        for gei in geis:
            body = [
                *(_gei("SET", gei, tmp_reg) if pending == "i" else []),
                *check(f"hgeie_{gei}_hgeip_{pending}", "cp_hgeie", 1 << gei),
                *(_gei("CLR", gei, tmp_reg) if pending == "i" else []),
            ]
            lines.extend(each_gei(body, gei))
        if pending == "all":
            lines.extend([*all_gei("CLR"), "#endif"])
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
            lines.extend(["#if UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 2", *all_gei("SET")])
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
            lines.extend([*all_gei("CLR"), "#endif"])
    lines.extend(
        [
            comment_banner(
                "cp_trigger_vsei_hgeip",
                "With hgeip = hgeie = every implemented bit and hstatus.VGEIN = 0, hip.SGEIP = 1 and hip.VSEIP = 0",
            ),
            f"LI(x{tmp_reg}, HSTATUS_VGEIN)",
            f"csrc hstatus, x{tmp_reg}",
            *all_gei("SET"),
            *check("vgein_0", "cp_trigger_vsei_hgeip", -1),
            *all_gei("CLR"),
            "csrw hgeie, zero",
            "#endif // RVTEST_SGEI_INTR_IMPL",
        ]
    )
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "Interrupts",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_interrupts_sgei(test_data: TestData) -> list[TestChunk]:
    """Interrupts_Sgei tests of guest external interrupts."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "Sgei_trigger")
    tc.code.extend([*IMSIC_STATEEN_ON, *_trigger_tests(test_data)])

    tc = test_data.new_test_chunk(test_chunks, "Sgei_hs")
    tc.code.extend([*IMSIC_STATEEN_ON, *_sgei_tests(test_data)])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Interrupts",
    required_extensions=["Sm", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_interrupts_sgeism(test_data: TestData) -> list[TestChunk]:
    """Interrupts_SgeiSm tests of guest external interrupts from every mode with mideleg = 0."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "SgeiSm_trigger")
    tc.code.extend([*IMSIC_STATEEN_ON, *_trigger_sm_tests(test_data)])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
