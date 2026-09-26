##################################
# priv/extensions/InterruptsH.py
#
# Hypervisor interrupt tests that run in HS, VS, VU and U modes.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""InterruptsH hypervisor interrupt test generator.

The suite boots to HS-mode, where mideleg delegates the S-level, VS-level and guest external interrupts.
VS-level interrupts are raised through hvip.  Guest external interrupts need the optional
RVMODEL_SET/CLR_GUEST_EXT_INT hooks (UDB_SGEI_INTR_IMPL).  Every testcase is sampled in HS-mode, the guest ones at
the T-SBI call that enters the guest.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import (
    REG_TRIGGER_DEFINES,
    int_bit,
    int_macro,
    interrupt_xtinst_tests,
    vs_int_macro,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "InterruptsH_hs_cg"

# VS-level interrupts in HS-mode priority order, with their bit in hvip, hip, hie and hideleg
VS_INTS = {name: int_bit[name] for name in ("VSEI", "VSSI", "VSTI")}
# S-level interrupts that preempt the VS-level ones, raised by RVTEST_SET_<macro>_INT_S
S_INTS = ["SEI", "STI", "SSI"]


def _vs(combo: int) -> int:
    """VS-level interrupt bits selected by a 3-bit combination: bit 0 VSSI, bit 1 VSTI, bit 2 VSEI."""
    return sum(1 << (4 * i + 2) for i in range(3) if combo >> i & 1)


def _gei(op: str, gei: int, tmp_reg: int) -> list[str]:
    """Raise (SET) or clear (CLR) guest external interrupt gei through the platform, and wait for hgeip."""
    return [f"RVMODEL_{op}_GUEST_EXT_INT({gei}, a1, a2)", f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})"]


def _trigger_tests(test_data: TestData) -> list[str]:
    """Raise each VS-level interrupt through hvip across sstatus.SIE, hideleg and hie.  HS-mode writes hvip with the
    M-mode macros."""
    tmp_reg = test_data.int_regs.get_register()
    lines = []
    for name, bit in VS_INTS.items():
        coverpoint = f"cp_trigger_{name.lower()}"
        lines.append(
            comment_banner(
                coverpoint,
                f"Raise {name} through hvip with sstatus.SIE, hideleg and hie = 0/1.  hip.{name}P rises;\n"
                f"HS-mode takes cause {bit} when SIE = 1, hideleg = 0 and hie = 1",
            )
        )
        for sie in (0, 1):
            for deleg in (0, 1):
                for ie in (0, 1):
                    lines.extend(
                        [
                            f"LI(x{tmp_reg}, {deleg << bit:#x})",
                            f"csrw hideleg, x{tmp_reg}",
                            f"LI(x{tmp_reg}, {ie << bit:#x})",
                            f"csrw hie, x{tmp_reg}",
                            f"csr{'s' if sie else 'c'}i sstatus, SSTATUS_SIE",
                            test_data.add_testcase(f"sie{sie}_hideleg{deleg}_hie{ie}", coverpoint, _CG),
                            f"RVTEST_SET_{vs_int_macro[name]}_INT_M",
                            f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                            "csrci sstatus, SSTATUS_SIE",
                            f"csrr x{tmp_reg}, hip    # still pending unless HS-mode took it",
                            write_sigupd(tmp_reg, test_data),
                            f"RVTEST_CLR_{vs_int_macro[name]}_INT_M",
                        ]
                    )
    lines.extend(["csrw hideleg, zero", "csrw hie, zero"])
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _hip_write_tests(test_data: TestData) -> list[str]:
    """Only hip.VSSIP is writable, and it is an alias of hvip.VSSIP."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner("cp_hip_write", "Write hip = 0xFFFF and 0, and read hvip and hip"),
        "csrw hie, zero",
        "csrw hvip, zero",
    ]
    for name, value in (("ones", 0xFFFF), ("zeros", 0)):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {value:#x})",
                test_data.add_testcase(name, "cp_hip_write", _CG),
                f"csrw hip, x{tmp_reg}",
                f"csrr x{tmp_reg}, hvip",
                write_sigupd(tmp_reg, test_data),
                f"csrr x{tmp_reg}, hip",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _priority_tests(test_data: TestData, vary: str) -> list[str]:
    """Raise each combination of VS-level interrupts in one hvip write, with SIE = 1 and each combination
    of vary: hie (cp_priority_en_vsi) or hideleg (cp_priority_deleg_vsi)."""
    tmp_reg = test_data.int_regs.get_register()
    coverpoint = "cp_priority_en_vsi" if vary == "hie" else "cp_priority_deleg_vsi"
    fixed, fixed_value = ("hideleg", "0") if vary == "hie" else ("hie", "MIP_VS_MASK")
    lines = [
        comment_banner(
            coverpoint,
            f"With sstatus.SIE = 1 and {fixed} = {fixed_value}, write each combination of hvip.VS*IP for each\n"
            f"combination of {vary}.  HS-mode takes the pending {'enabled' if vary == 'hie' else 'undelegated'} "
            "interrupts in priority order VSEI, VSSI, VSTI",
        ),
    ]
    for combo in range(8):
        for pending in range(8):
            lines.extend(
                [
                    f"LI(x{tmp_reg}, {fixed_value})",
                    f"csrw {fixed}, x{tmp_reg}",
                    f"LI(x{tmp_reg}, {_vs(combo):#x})",
                    f"csrw {vary}, x{tmp_reg}",
                    "csrsi sstatus, SSTATUS_SIE",
                    f"LI(x{tmp_reg}, {_vs(pending):#x})",
                    test_data.add_testcase(f"{vary}_{_vs(combo):03x}_hvip_{_vs(pending):03x}", coverpoint, _CG),
                    f"csrw hvip, x{tmp_reg}",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                    "csrci sstatus, SSTATUS_SIE",
                    "csrw hvip, zero",
                ]
            )
    lines.extend(["csrw hideleg, zero", "csrw hie, zero"])
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _priority_s_tests(test_data: TestData) -> list[str]:
    """Pending S-level interrupts are taken before the VS-level ones."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_priority_s",
            "With hvip = hie = 0x444, hideleg = 0 and sie = 1s, raise SEI, STI, SSI or nothing, then set\n"
            "sstatus.SIE.  The S-level interrupt is taken first, then VSEI, VSSI and VSTI",
        ),
        "csrw hideleg, zero",
    ]
    for s_int in [*S_INTS, None]:
        name = s_int.lower() if s_int else "none"
        lines.extend(
            [
                f"LI(x{tmp_reg}, MIP_VS_MASK)",
                f"csrw hvip, x{tmp_reg}",
                f"csrw hie, x{tmp_reg}",
                f"LI(x{tmp_reg}, -1)",
                f"csrw sie, x{tmp_reg}",
                *([f"RVTEST_SET_{int_macro[s_int]}_INT_S"] if s_int else []),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                test_data.add_testcase(name, "cp_priority_s", _CG),
                f"csrr x{tmp_reg}, sip",
                write_sigupd(tmp_reg, test_data),
                "csrsi sstatus, SSTATUS_SIE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                "csrci sstatus, SSTATUS_SIE",
                *([f"RVTEST_CLR_{int_macro[s_int]}_INT_S"] if s_int else []),
                "csrw sie, zero",
                "csrw hvip, zero",
            ]
        )
    lines.append("csrw hie, zero")
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _alias_tests(test_data: TestData) -> list[str]:
    """hie, hip, vsie and vsip as views of mie, mip and each other through hideleg."""
    tmp_reg, mask_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_hie", "With mie = 0x444, read hie and vsie for each combination of hideleg.VS*I (vsie shows it >> 1)"
        ),
        "RVTEST_TSBI_CSR_WRITE(CSR_MIE, MIP_VS_MASK)",
    ]
    for combo in range(8):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {_vs(combo):#x})",
                f"csrw hideleg, x{tmp_reg}",
                test_data.add_testcase(f"hideleg_{_vs(combo):03x}", "cp_hie", _CG),
                f"csrr x{tmp_reg}, hie",
                write_sigupd(tmp_reg, test_data),
                f"csrr x{tmp_reg}, vsie",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    lines.extend(
        [
            "RVTEST_TSBI_CSR_WRITE(CSR_MIE, 0)",
            comment_banner(
                "cp_hip",
                "With hvip = 0x444, read hip and vsip for each combination of hideleg.VS*I (vsip shows it >> 1)",
            ),
            f"LI(x{tmp_reg}, MIP_VS_MASK)",
            f"csrw hvip, x{tmp_reg}",
        ]
    )
    for combo in range(8):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {_vs(combo):#x})",
                f"csrw hideleg, x{tmp_reg}",
                test_data.add_testcase(f"hideleg_{_vs(combo):03x}", "cp_hip", _CG),
                f"csrr x{tmp_reg}, hip",
                write_sigupd(tmp_reg, test_data),
                f"csrr x{tmp_reg}, vsip",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    lines.extend(
        [
            "csrw hvip, zero",
            comment_banner(
                "cp_hideleg",
                "Write hideleg = 0xFFFF.  Bits 10, 6 and 2 are writable.  Bit 13 is writable only with Shlcofideleg,\n"
                "which UDB and the reference model do not describe, so it is not checked",
            ),
            f"LI(x{tmp_reg}, 0xFFFF)",
            test_data.add_testcase("ones", "cp_hideleg", _CG),
            f"csrw hideleg, x{tmp_reg}",
            f"csrr x{tmp_reg}, hideleg",
            f"LI(x{mask_reg}, ~MIP_LCOFIP)",
            f"and x{tmp_reg}, x{tmp_reg}, x{mask_reg}",
            write_sigupd(tmp_reg, test_data),
        ]
    )
    for alias, source, field in (("vsie", "hie", "VS*IE"), ("vsip", "hvip", "VS*IP")):
        coverpoint = f"cp_{alias}"
        lines.append(
            comment_banner(coverpoint, f"Read {alias} for each combination of hideleg.VS*I and {source}.{field}")
        )
        for deleg in range(8):
            for combo in range(8):
                lines.extend(
                    [
                        f"LI(x{tmp_reg}, {_vs(deleg):#x})",
                        f"csrw hideleg, x{tmp_reg}",
                        f"LI(x{tmp_reg}, {_vs(combo):#x})",
                        f"csrw {source}, x{tmp_reg}",
                        test_data.add_testcase(f"hideleg_{_vs(deleg):03x}_{source}_{_vs(combo):03x}", coverpoint, _CG),
                        f"csrr x{tmp_reg}, {alias}",
                        write_sigupd(tmp_reg, test_data),
                    ]
                )
        lines.append(f"csrw {source}, zero")
    lines.append(
        comment_banner("cp_vsie_from_hie", "Write vsie = 0xFFFF for each combination of hideleg.VS*I and read hie")
    )
    for deleg in range(8):
        lines.extend(
            [
                "csrw hie, zero",
                f"LI(x{tmp_reg}, {_vs(deleg):#x})",
                f"csrw hideleg, x{tmp_reg}",
                f"LI(x{tmp_reg}, 0xFFFF)",
                test_data.add_testcase(f"hideleg_{_vs(deleg):03x}", "cp_vsie_from_hie", _CG),
                f"csrw vsie, x{tmp_reg}",
                f"csrr x{tmp_reg}, hie",
                write_sigupd(tmp_reg, test_data),
            ]
        )
    lines.extend(
        [
            "csrw hie, zero",
            "csrw hideleg, zero",
            comment_banner("cp_hie_gilen", "With mie = 0x1444, read hie.  SGEIE is writable if GEILEN > 0"),
            "RVTEST_TSBI_CSR_WRITE(CSR_MIE, MIP_HS_MASK)",
            test_data.add_testcase("mie_1444", "cp_hie_gilen", _CG),
            f"csrr x{tmp_reg}, hie",
            write_sigupd(tmp_reg, test_data),
            "RVTEST_TSBI_CSR_WRITE(CSR_MIE, 0)",
        ]
    )
    test_data.int_regs.return_registers([tmp_reg, mask_reg])
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


def _guest_tests(
    test_data: TestData, coverpoint: str, mode: str, cases: list[tuple[str, int, int, int, int]]
) -> list[str]:
    """Enter mode (vs or vu) with each case's (bin, hideleg, hvip, hie, vsstatus.SIE).

    HS-mode takes the pending, enabled, undelegated interrupts first, then the guest's VS-mode handler takes the
    delegated ones, which it sees as SEI, STI and SSI.
    """
    tmp_reg = test_data.int_regs.get_register()
    lines = []
    for bin_name, deleg, pending, enable, sie in cases:
        lines.extend(
            [
                f"LI(x{tmp_reg}, {deleg:#x})",
                f"csrw hideleg, x{tmp_reg}",
                f"LI(x{tmp_reg}, {pending:#x})",
                f"csrw hvip, x{tmp_reg}",
                f"LI(x{tmp_reg}, {enable:#x})",
                f"csrw hie, x{tmp_reg}",
                f"LI(x{tmp_reg}, SSTATUS_SIE)",
                f"csr{'s' if sie else 'c'} vsstatus, x{tmp_reg}",
                test_data.add_testcase(bin_name, coverpoint, _CG),
                f"RVTEST_TSBI_GOTO_{mode.upper()}MODE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                "RVTEST_TSBI_GOTO_SMODE",
                "csrw hvip, zero",
            ]
        )
    lines.extend(["csrw hideleg, zero", "csrw hie, zero"])
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _guest_cross_tests(test_data: TestData, mode: str) -> list[str]:
    """Enter VS-mode (vsstatus.SIE = 1) or VU-mode (vsstatus.SIE = 0) with every combination of two of hideleg,
    hvip and hie, the third holding every VS-level bit."""
    sie = 1 if mode == "vs" else 0
    combos = [_vs(combo) for combo in range(8)]
    every = combos[-1]
    crosses = [
        ("hideleg_hip", "hideleg and hvip, with hie = 0x444", [(d, p, every) for d in combos for p in combos]),
        ("hideleg_hie", "hideleg and hie, with hvip = 0x444", [(d, every, e) for d in combos for e in combos]),
        ("hip_hie", "hvip and hie, with hideleg = 0x444", [(every, p, e) for p in combos for e in combos]),
    ]
    lines = []
    for name, description, cases in crosses:
        coverpoint = f"cp_{name}_{mode}"
        lines.append(
            comment_banner(
                coverpoint,
                f"Enter {mode.upper()}-mode with vsstatus.SIE = {sie} for each combination of {description}.\n"
                "HS-mode takes the enabled undelegated interrupts, then VS-mode takes the enabled delegated ones",
            )
        )
        named = [(f"hideleg_{d:03x}_hvip_{p:03x}_hie_{e:03x}", d, p, e, sie) for d, p, e in cases]
        lines.extend(_guest_tests(test_data, coverpoint, mode, named))
    return lines


def _vectored_tests(test_data: TestData) -> list[str]:
    """Delegated VS-level interrupts through a vectored vstvec land at BASE + 4 x the S-level cause."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_vsint_vectored",
            "With vstvec.MODE = vectored and hideleg = 0x444, take each VS-level interrupt in VS-mode.  VSEI, VSTI\n"
            "and VSSI arrive as causes 9, 5 and 1 at vstvec.BASE + 4 x cause",
        ),
        "#ifdef UDB_VSTVEC_MODES_1",
        "csrsi vstvec, 1",
        f"LI(x{tmp_reg}, MIP_VS_MASK)",
        f"csrw hideleg, x{tmp_reg}",
        f"LI(x{tmp_reg}, SSTATUS_SIE)",
        f"csrs vsstatus, x{tmp_reg}",
    ]
    for name, bit in VS_INTS.items():
        lines.extend(
            [
                f"LI(x{tmp_reg}, {1 << bit:#x})",
                f"csrw hie, x{tmp_reg}",
                f"csrw hvip, x{tmp_reg}",
                test_data.add_testcase(name.lower(), "cp_vsint_vectored", _CG),
                "RVTEST_TSBI_GOTO_VSMODE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                "RVTEST_TSBI_GOTO_SMODE",
                "csrw hvip, zero",
            ]
        )
    lines.extend(["csrci vstvec, 1", "csrw hideleg, zero", "csrw hie, zero", "#endif // UDB_VSTVEC_MODES_1"])
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _user_tests(test_data: TestData) -> list[str]:
    """VS-level interrupts are never taken with V = 0 below HS-mode."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_vsint_disabled_u",
            "With hideleg = hvip = hie = 0x444, enter U-mode.  No interrupt is taken and hip stays 0x444",
        ),
        f"LI(x{tmp_reg}, MIP_VS_MASK)",
        f"csrw hideleg, x{tmp_reg}",
        f"csrw hvip, x{tmp_reg}",
        f"csrw hie, x{tmp_reg}",
        test_data.add_testcase("hideleg_444", "cp_vsint_disabled_u", _CG),
        "RVTEST_TSBI_GOTO_UMODE",
        f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
        "RVTEST_TSBI_GOTO_SMODE",
        f"csrr x{tmp_reg}, hip",
        write_sigupd(tmp_reg, test_data),
        "csrw hvip, zero",
        "csrw hideleg, zero",
        "csrw hie, zero",
    ]
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "InterruptsH",
    required_extensions=["H"],
    extra_defines=[*REG_TRIGGER_DEFINES, "#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_interruptsh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the InterruptsH hypervisor interrupt suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "trigger")
    tc.code.extend(
        [*_trigger_tests(test_data), *_hip_write_tests(test_data), *interrupt_xtinst_tests(test_data, _CG, "S")]
    )

    tc = test_data.new_test_chunk(test_chunks, "priority")
    tc.code.extend(
        [*_priority_tests(test_data, "hie"), *_priority_tests(test_data, "hideleg"), *_priority_s_tests(test_data)]
    )

    tc = test_data.new_test_chunk(test_chunks, "alias")
    tc.code.extend(_alias_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "sgei")
    tc.code.extend(_sgei_tests(test_data))

    every = _vs(0b111)
    tc = test_data.new_test_chunk(test_chunks, "vs")
    tc.code.extend(
        [
            *_guest_cross_tests(test_data, "vs"),
            comment_banner(
                "cp_sie_vs",
                "With hideleg = hvip = hie = 0x444, enter VS-mode with vsstatus.SIE = 0/1.  VS-mode takes SEI,\n"
                "SSI and STI only when SIE = 1",
            ),
            *_guest_tests(test_data, "cp_sie_vs", "vs", [(f"sie{sie}", every, every, every, sie) for sie in (0, 1)]),
            *_vectored_tests(test_data),
        ]
    )

    tc = test_data.new_test_chunk(test_chunks, "vu")
    tc.code.extend([*_guest_cross_tests(test_data, "vu"), *_user_tests(test_data)])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
