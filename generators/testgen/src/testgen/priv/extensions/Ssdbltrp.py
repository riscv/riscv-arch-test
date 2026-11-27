##################################
# priv/extensions/Ssdbltrp.py
#
# Ssdbltrp Sm, H and HSm groups: sstatus.SDT and vsstatus.SDT across xRET and traps, and double traps.
# David_Harris@hmc.edu 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssdbltrp Sm, H and HSm group test generators.

The Sm group boots to M-mode, sets menvcfg.DTE = 1 and enters S-mode (HS-mode with H) by MRET.  A trap into
S-mode with sstatus.SDT = 1 is a double trap, taken in M-mode with mcause = 16 and the cause in mtval2.  A trap
not delegated to S-mode, a trap with sstatus.SDT = 0 (which sets it), and a trap with menvcfg.DTE = 0 are not.

The H and HSm groups set menvcfg.DTE = henvcfg.DTE = 1, so sstatus.SDT and vsstatus.SDT are writable.

The H group boots to HS-mode.  An SRET in HS-mode clears sstatus.SDT, and also vsstatus.SDT when it returns to
VU-mode; an SRET in VS-mode clears vsstatus.SDT.  An SRET from HS-mode to VS-mode or HS-mode leaves vsstatus.SDT
alone.  After each SRET the test returns to HS-mode and records vsstatus.SDT and sstatus.SDT.  A trap into VS-mode
sets vsstatus.SDT, a trap into HS-mode ignores it, an explicit write that sets vsstatus.SDT clears vsstatus.SIE, and
henvcfg.DTE = 0 makes vsstatus.SDT read-only zero.

The HSm group boots to M-mode.  A trap into VS-mode with vsstatus.SDT = 1 is a double trap, taken in M-mode with
mcause = 16 and the unexpected trap's cause in mtval2.  With Smdbltrp, MRET and SRET in M-mode clear vsstatus.SDT
only when they return to VU-mode.

Every return into VU-mode clears vsstatus.SDT (SRET from HS-mode or VS-mode, and with Smdbltrp MRET and SRET in
M-mode), so vsstatus.SDT = 1 is reachable only in VS-mode, and only VS-mode can raise a double trap.
"""

from testgen.asm.helpers import comment_banner, gated, tvec_alignment, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Ssdbltrp_H_cg"
_HSM_CG = "Ssdbltrp_HSm_cg"

_DTE_ON = [
    "#if __riscv_xlen == 64",
    "RVTEST_TSBI_CSR_SET(CSR_MENVCFG, MENVCFG_DTE)",
    "#else",
    "RVTEST_TSBI_CSR_SET(CSR_MENVCFGH, MENVCFGH_DTE)",
    "#endif",
]
_DTE_OFF = [line.replace("_SET(", "_CLEAR(") for line in _DTE_ON]


def _henvcfg_dte(op: str, reg: int) -> list[str]:
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, HENVCFG_DTE)",
        f"{op} henvcfg, x{reg}",
        "#else",
        f"LI(x{reg}, HENVCFGH_DTE)",
        f"{op} henvcfgh, x{reg}",
        "#endif",
    ]


def _record_sdt(
    test_data: TestData, rd: int, mask_reg: int, name: str, coverpoint: str, covergroup: str = _CG
) -> list[str]:
    """In HS-mode or M-mode, record vsstatus.SDT and sstatus.SDT."""
    lines = []
    for csr in ("vsstatus", "sstatus"):
        lines.extend(
            [
                test_data.add_testcase(f"{name}_{csr}", coverpoint, covergroup),
                f"csrr x{rd}, {csr}",
                f"and x{rd}, x{rd}, x{mask_reg}",
                write_sigupd(rd, test_data),
            ]
        )
    return lines


def _sret_sdt_tests(test_data: TestData) -> list[str]:
    temp_reg, rd, mask_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_hs_sret_vsstatus_sdt, cp_vs_sret_vsstatus_sdt",
            "With menvcfg.DTE = henvcfg.DTE = 1 and vsstatus.SDT = 1, SRET from HS-mode to VU-mode, VS-mode and\n"
            "HS-mode, and SRET in VS-mode to VU-mode and VS-mode.  Back in HS-mode, read vsstatus.SDT and sstatus.SDT.\n"
            "Only SRET to VU-mode from HS-mode and SRET in VS-mode clear vsstatus.SDT",
        ),
        *_DTE_ON,
        *_henvcfg_dte("csrs", temp_reg),
        f"LI(x{mask_reg}, SSTATUS_SDT)",
    ]
    # SRET from HS-mode: (target, hstatus.SPV, sstatus.SPP)
    for target, spv, spp in (("vu", 1, 0), ("vs", 1, 1), ("hs", 0, 1)):
        name = f"hs_to_{target}"
        lines.extend(
            [
                "",
                f"# SRET from HS-mode to {target.upper()}-mode with vsstatus.SDT = 1 and sstatus.SDT = 1",
                f"csrs vsstatus, x{mask_reg}",
                f"LI(x{temp_reg}, HSTATUS_SPV)",
                f"{'csrs' if spv else 'csrc'} hstatus, x{temp_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPP)",
                f"{'csrs' if spp else 'csrc'} sstatus, x{temp_reg}",
                f"csrs sstatus, x{mask_reg}",
                f"LA(x{temp_reg}, 1f)",
                f"csrw sepc, x{temp_reg}",
                test_data.add_testcase(name, "cp_hs_sret_vsstatus_sdt", _CG),
                "sret",
                "1:",
                *([] if target == "hs" else ["RVTEST_TSBI_GOTO_SMODE"]),
                *_record_sdt(test_data, rd, mask_reg, name, "cp_hs_sret_vsstatus_sdt"),
            ]
        )
    lines.extend([f"LI(x{temp_reg}, HSTATUS_SPV)", f"csrc hstatus, x{temp_reg}"])
    # SRET in VS-mode: vsstatus.SPP selects VU-mode or VS-mode
    for target, spp in (("vu", 0), ("vs", 1)):
        name = f"vs_to_{target}"
        lines.extend(
            [
                "",
                f"# SRET in VS-mode to {target.upper()}-mode with vsstatus.SDT = 1",
                f"csrs vsstatus, x{mask_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPP)",
                f"{'csrs' if spp else 'csrc'} vsstatus, x{temp_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
                f"LA(x{temp_reg}, 1f)",
                f"csrw sepc, x{temp_reg}",
                test_data.add_testcase(name, "cp_vs_sret_vsstatus_sdt", _CG),
                "sret",
                "1:",
                "RVTEST_TSBI_GOTO_SMODE",
                *_record_sdt(test_data, rd, mask_reg, name, "cp_vs_sret_vsstatus_sdt"),
            ]
        )
    lines.extend(
        [
            f"csrc vsstatus, x{mask_reg}",
            f"csrc sstatus, x{mask_reg}",
            *_henvcfg_dte("csrc", temp_reg),
            *_DTE_OFF,
        ]
    )
    test_data.int_regs.return_registers([temp_reg, rd, mask_reg])
    return lines


_SDT_SIE = "SSTATUS_SDT | SSTATUS_SIE"
# A load from the access-fault address, on configurations that have one
_LOAD_FAULT_GATE = "defined(RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)"


def _vs_trap(test_data: TestData, mode: str, name: str, coverpoint: str, regs: list[int]) -> list[str]:
    """From HS-mode, enter ``mode`` (VS or VU) and execute an ebreak that hedeleg[3] sends to VS-mode.

    vstvec points just past the ebreak, so the trap resumes there in VS-mode instead of in the framework's VS-mode
    handler, whose SRET would clear vsstatus.SDT.  The test returns to HS-mode, puts vstvec back, and records
    vsstatus.SDT and vscause.
    """
    save_vstvec, temp_reg, rd = regs
    testcase = test_data.add_testcase(name, coverpoint, _CG)
    handler = f"{test_data.current_testcase_label}_vstvec"
    return [
        f"csrr x{save_vstvec}, vstvec",
        f"andi x{temp_reg}, x{save_vstvec}, 3   # keep the MODE the DUT uses",
        f"LA(x{rd}, {handler})",
        f"or x{rd}, x{rd}, x{temp_reg}",
        f"csrw vstvec, x{rd}",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        testcase,
        "ebreak",
        *tvec_alignment("stvec"),
        f"{handler}:",
        "RVTEST_TSBI_GOTO_SMODE",
        f"csrw vstvec, x{save_vstvec}",
        f"csrr x{rd}, vsstatus",
        f"LI(x{temp_reg}, SSTATUS_SDT)",
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
        f"csrr x{rd}, vscause",
        write_sigupd(rd, test_data),
    ]


def _vs_trap_sdt_tests(test_data: TestData) -> list[str]:
    """cp_vs_trap_sdt: a breakpoint from VS-mode or VU-mode delegated to VS-mode sets vsstatus.SDT."""
    regs = test_data.int_regs.get_registers(3)
    temp_reg = regs[1]
    lines = [
        comment_banner(
            "cp_vs_trap_sdt",
            "With menvcfg.DTE = henvcfg.DTE = 1, vsstatus.SDT = 0 and medeleg[3] = hedeleg[3] = 1, ebreak in VS-mode\n"
            "and in VU-mode traps into VS-mode, which sets vsstatus.SDT",
        ),
        f"LI(x{temp_reg}, 1 << CAUSE_BREAKPOINT)",
        f"csrs hedeleg, x{temp_reg}",
    ]
    for mode in ("VS", "VU"):
        lines.extend(
            [
                "",
                f"LI(x{temp_reg}, SSTATUS_SDT)",
                f"csrc vsstatus, x{temp_reg}",
                *_vs_trap(test_data, mode, mode.lower(), "cp_vs_trap_sdt", regs),
            ]
        )
    lines.extend(
        [
            f"LI(x{temp_reg}, SSTATUS_SDT)",
            f"csrc vsstatus, x{temp_reg}",
            f"LI(x{temp_reg}, 1 << CAUSE_BREAKPOINT)",
            f"csrc hedeleg, x{temp_reg}",
        ]
    )
    test_data.int_regs.return_registers(regs)
    return lines


def _vs_sdt_target_tests(test_data: TestData) -> list[str]:
    """cp_vs_sdt_target: with hedeleg = 0, a VS-mode breakpoint or load access fault goes to HS-mode even with
    vsstatus.SDT = 1.  The framework's HS-mode handler records the trap; SRET back to VS-mode leaves vsstatus.SDT."""
    addr_reg, temp_reg, rd = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_vs_sdt_target",
            "With menvcfg.DTE = henvcfg.DTE = 1, vsstatus.SDT = 1 and hedeleg = 0, ebreak and a load access fault in\n"
            "VS-mode are ordinary traps into HS-mode, not double traps.  Back in HS-mode, vsstatus.SDT is still 1",
        ),
    ]
    for name, trap, gate in (
        ("ebreak", ["ebreak"], None),
        ("load_access_fault", [f"lw x{rd}, 0(x{addr_reg})"], _LOAD_FAULT_GATE),
    ):
        body = [
            "",
            f"LI(x{temp_reg}, SSTATUS_SDT)",
            f"csrs vsstatus, x{temp_reg}",
            *([f"LI_FIXED_LEN(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)"] if gate else []),
            "RVTEST_TSBI_GOTO_VSMODE",
            test_data.add_testcase(name, "cp_vs_sdt_target", _CG),
            *trap,
            "RVTEST_TSBI_GOTO_SMODE",
            f"csrr x{rd}, vsstatus",
            f"and x{rd}, x{rd}, x{temp_reg}",
            write_sigupd(rd, test_data),
            f"csrc vsstatus, x{temp_reg}",
        ]
        lines.extend(gated(body, gate))
    test_data.int_regs.return_registers([addr_reg, temp_reg, rd])
    return lines


def _henvcfg_dte0_tests(test_data: TestData) -> list[str]:
    """cp_henvcfg_dte0: henvcfg.DTE = 0 makes vsstatus.SDT read-only zero and disables double traps in VS-mode.

    vsstatus.SDT is set while henvcfg.DTE = 1, so reads and traps with henvcfg.DTE = 0 must ignore a stored 1.
    """
    regs = test_data.int_regs.get_registers(3)
    _, temp_reg, rd = regs
    sdt = [f"LI(x{temp_reg}, SSTATUS_SDT)"]
    lines = [
        comment_banner(
            "cp_henvcfg_dte0",
            "Set vsstatus.SDT with menvcfg.DTE = henvcfg.DTE = 1, then clear henvcfg.DTE.  vsstatus.SDT reads 0 from\n"
            "HS-mode, a write of 1 from HS-mode (vsstatus) or VS-mode (sstatus) leaves it 0, and ebreak in VS-mode\n"
            "with medeleg[3] = hedeleg[3] = 1 is an ordinary trap into VS-mode",
        ),
        *sdt,
        f"csrs vsstatus, x{temp_reg}",
        *_henvcfg_dte("csrc", temp_reg),
        "",
        test_data.add_testcase("hs_read", "cp_henvcfg_dte0", _CG),
        f"csrr x{rd}, vsstatus",
        *sdt,
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
        "",
        test_data.add_testcase("hs_write", "cp_henvcfg_dte0", _CG),
        f"csrs vsstatus, x{temp_reg}",
        f"csrr x{rd}, vsstatus",
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
        "",
        "RVTEST_TSBI_GOTO_VSMODE",
        test_data.add_testcase("vs_write", "cp_henvcfg_dte0", _CG),
        f"csrs sstatus, x{temp_reg}",
        f"csrr x{rd}, sstatus",
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
        "RVTEST_TSBI_GOTO_SMODE",
        "",
        f"LI(x{temp_reg}, 1 << CAUSE_BREAKPOINT)",
        f"csrs hedeleg, x{temp_reg}",
        *_vs_trap(test_data, "VS", "vs_ebreak", "cp_henvcfg_dte0", regs),
        f"LI(x{temp_reg}, 1 << CAUSE_BREAKPOINT)",
        f"csrc hedeleg, x{temp_reg}",
        "",
        "# Turn henvcfg.DTE back on and clear vsstatus.SDT, whose value while it was read-only zero is not specified",
        *_henvcfg_dte("csrs", temp_reg),
        *sdt,
        f"csrc vsstatus, x{temp_reg}",
    ]
    test_data.int_regs.return_registers(regs)
    return lines


# (bin, vsstatus bits set before, CSR instruction): each write either sets SDT, which clears SIE whatever the write
# gives SIE, or sets SIE, which takes effect only if the same write clears SDT
_SDT_SIE_WRITES = (
    ("set_sdt_and_sie", "0", "csrs {csr}, x{val}   # SDT = SIE = 1 in one write", _SDT_SIE),
    ("set_sdt_with_sie", "SSTATUS_SIE", "csrs {csr}, x{val}   # SDT = 1 with SIE already 1", "SSTATUS_SDT"),
    ("set_sie_with_sdt", "SSTATUS_SDT", "csrs {csr}, x{val}   # SIE = 1 with SDT already 1", "SSTATUS_SIE"),
    ("clear_sdt_set_sie", "SSTATUS_SDT", "csrw {csr}, x{val}   # SDT = 0 and SIE = 1 in one write", None),
)


def _vs_sdt_sie_tests(test_data: TestData) -> list[str]:
    """cp_vs_sdt_sie: setting vsstatus.SDT by a CSR write clears vsstatus.SIE, from HS-mode and from VS-mode."""
    val_reg, mask_reg, rd = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_vs_sdt_sie",
            "With menvcfg.DTE = henvcfg.DTE = 1, write vsstatus from HS-mode and sstatus from VS-mode: set SDT and SIE\n"
            "together, set SDT with SIE = 1, set SIE with SDT = 1, and write SDT = 0 with SIE = 1.  Read SDT and SIE.\n"
            "hideleg = 0, so vsstatus.SIE enables no interrupt",
        ),
        f"LI(x{mask_reg}, {_SDT_SIE})",
    ]
    for mode, csr in (("HS", "vsstatus"), ("VS", "sstatus")):
        lines.append("")
        for name, before, write, value in _SDT_SIE_WRITES:
            setup = [f"csrc vsstatus, x{mask_reg}"]
            if before != "0":
                setup.extend([f"LI(x{val_reg}, {before})", f"csrs vsstatus, x{val_reg}"])
            if value is None:
                # vsstatus with SDT = 0 and SIE = 1, the other fields unchanged
                operand = [
                    f"csrr x{val_reg}, {csr}",
                    f"LI(x{rd}, SSTATUS_SDT)",
                    f"not x{rd}, x{rd}",
                    f"and x{val_reg}, x{val_reg}, x{rd}",
                    f"ori x{val_reg}, x{val_reg}, SSTATUS_SIE",
                ]
            else:
                operand = [f"LI(x{val_reg}, {value})"]
            lines.extend(
                [
                    *setup,
                    *(["RVTEST_TSBI_GOTO_VSMODE"] if mode == "VS" else []),
                    *operand,
                    test_data.add_testcase(f"{mode.lower()}_{name}", "cp_vs_sdt_sie", _CG),
                    write.format(csr=csr, val=val_reg),
                    f"csrr x{rd}, {csr}",
                    f"and x{rd}, x{rd}, x{mask_reg}",
                    write_sigupd(rd, test_data),
                    *(["RVTEST_TSBI_GOTO_SMODE"] if mode == "VS" else []),
                ]
            )
    lines.append(f"csrc vsstatus, x{mask_reg}")
    test_data.int_regs.return_registers([val_reg, mask_reg, rd])
    return lines


@add_priv_test_generator(
    "Ssdbltrp",
    required_extensions=["Ssdbltrp", "H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssdbltrph(test_data: TestData) -> list[TestChunk]:
    """Generate the Ssdbltrp_H tests: vsstatus.SDT across SRET and traps, and henvcfg.DTE = 0."""
    tc = test_data.begin_test_chunk("H")
    tc.code.extend(_sret_sdt_tests(test_data))
    test_chunks = [test_data.end_test_chunk()]
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk("H_trap")
    tc.code.extend(
        [
            *_DTE_ON,
            *_henvcfg_dte("csrs", temp_reg),
            *_vs_trap_sdt_tests(test_data),
            *_vs_sdt_target_tests(test_data),
            *_henvcfg_dte0_tests(test_data),
            *_vs_sdt_sie_tests(test_data),
            *_henvcfg_dte("csrc", temp_reg),
            *_DTE_OFF,
        ]
    )
    test_data.int_regs.return_registers([temp_reg])
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


def _menvcfg_dte(op: str, reg: int) -> list[str]:
    """menvcfg.DTE from M-mode."""
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, MENVCFG_DTE)",
        f"{op} menvcfg, x{reg}",
        "#else",
        f"LI(x{reg}, MENVCFGH_DTE)",
        f"{op} menvcfgh, x{reg}",
        "#endif",
    ]


def _m_dte(op: str, reg: int) -> list[str]:
    """menvcfg.DTE and henvcfg.DTE from M-mode."""
    return [*_menvcfg_dte(op, reg), *_henvcfg_dte(op, reg)]


def _m_xret_to(instr: str, mode: str, reg: int, target: str) -> list[str]:
    """From M-mode, set up ``instr`` (mret or sret) to return to ``mode`` (VS, VU, or for mret S) at ``target``."""
    if instr == "mret":
        mpv_op = "csrc" if mode == "S" else "csrs"
        mpv = [
            "#if __riscv_xlen == 64",
            f"LI(x{reg}, MSTATUS_MPV)",
            f"{mpv_op} mstatus, x{reg}",
            "#else",
            f"LI(x{reg}, MSTATUSH_MPV)",
            f"{mpv_op} mstatush, x{reg}",
            "#endif",
        ]
        return [
            f"LI(x{reg}, MSTATUS_MPP)",
            f"csrc mstatus, x{reg}",
            *([f"LI(x{reg}, MPP_SMODE)", f"csrs mstatus, x{reg}"] if mode in ("VS", "S") else []),
            *(gated(mpv, "defined(H_SUPPORTED)") if mode == "S" else mpv),
            f"LA(x{reg}, {target})",
            f"csrw mepc, x{reg}",
        ]
    return [
        f"LI(x{reg}, SSTATUS_SPP)",
        f"{'csrs' if mode == 'VS' else 'csrc'} sstatus, x{reg}",
        f"LI(x{reg}, HSTATUS_SPV)",
        f"csrs hstatus, x{reg}",
        f"LA(x{reg}, {target})",
        f"csrw sepc, x{reg}",
    ]


# (bin, exception cause, trapping instruction, gate)
_DOUBLE_TRAPS = (
    ("ebreak", "CAUSE_BREAKPOINT", "ebreak", None),
    ("load_access_fault", "CAUSE_LOAD_ACCESS", "lw x{rd}, 0(x{addr})", _LOAD_FAULT_GATE),
)


def _sdt_traps_to_m(test_data: TestData, mode: str, coverpoint: str, covergroup: str, delegate: bool) -> list[str]:
    """From M-mode, enter ``mode`` (VS or S) by MRET with xstatus.SDT = 1 and raise each trap in _DOUBLE_TRAPS.

    With ``delegate``, medeleg (and for VS-mode hedeleg) send the trap to ``mode``, so it is a double trap; otherwise
    medeleg = 0 sends it to M-mode.  M-mode presets xstatus, xepc, xcause and xtval and points mtvec just past the
    trapping instruction.  Back in M-mode, the test puts mtvec back, clears mstatus.MDT, MPV and GVA, and records
    mstatus.MPP, MPV and GVA, mcause, mtval2 (double traps only), mepc, mtval for ebreak, and the x CSRs.  medeleg
    and hedeleg start and end at 0.
    """
    x = mode.lower()
    deleg = ["medeleg", "hedeleg"] if mode == "VS" else ["medeleg"]
    save_mtvec, addr_reg, temp_reg, rd, rd2 = test_data.int_regs.get_registers(5)
    lines = []
    for name, cause, trap, gate in _DOUBLE_TRAPS:
        testcase = test_data.add_testcase(name, coverpoint, covergroup)
        label = test_data.current_testcase_label
        handler = f"{label}_mtvec"
        body = [
            "",
            *([f"LI(x{temp_reg}, 1 << {cause})", *[f"csrw {csr}, x{temp_reg}" for csr in deleg]] if delegate else []),
            f"# {x}status.SDT = SPIE = 1 and SPP = 0, the opposite of what the trap would write; {x}epc, {x}cause, {x}tval",
            f"LI(x{temp_reg}, SSTATUS_SDT | SSTATUS_SPIE)",
            f"csrs {x}status, x{temp_reg}",
            f"LI(x{temp_reg}, SSTATUS_SPP)",
            f"csrc {x}status, x{temp_reg}",
            f"LA(x{temp_reg}, {label})",
            f"csrw {x}epc, x{temp_reg}",
            f"csrw {x}tval, x{temp_reg}",
            f"LI(x{temp_reg}, CAUSE_ILLEGAL_INSTRUCTION)",
            f"csrw {x}cause, x{temp_reg}",
            f"csrr x{save_mtvec}, mtvec",
            f"andi x{temp_reg}, x{save_mtvec}, 3   # keep the MODE the DUT uses",
            f"LA(x{rd}, {handler})",
            f"or x{rd}, x{rd}, x{temp_reg}",
            f"csrw mtvec, x{rd}",
            *([f"LI_FIXED_LEN(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)"] if gate else []),
            *_m_xret_to("mret", mode, temp_reg, label),
            "mret",
            testcase,
            trap.format(rd=rd, addr=addr_reg),
            *tvec_alignment("mtvec"),
            f"{handler}:",
            f"csrw mtvec, x{save_mtvec}",
            f"csrr x{rd}, mstatus",
            f"LI(x{temp_reg}, MSTATUS_MPP)",
            f"and x{rd}, x{rd}, x{temp_reg}",
            "# Record MPV and GVA, then clear them and MDT (Smdbltrp), so a later trap into M-mode is not a double trap",
            "#if __riscv_xlen == 64",
            f"csrr x{rd2}, mstatus",
            f"srli x{rd2}, x{rd2}, 32",
            f"LI(x{temp_reg}, MSTATUS_MPV | MSTATUS_GVA | MSTATUS_MDT)",
            f"csrc mstatus, x{temp_reg}",
            "#else",
            f"csrr x{rd2}, mstatush",
            f"LI(x{temp_reg}, MSTATUSH_MPV | MSTATUSH_GVA | MSTATUSH_MDT)",
            f"csrc mstatush, x{temp_reg}",
            "#endif",
            f"andi x{rd2}, x{rd2}, MSTATUSH_MPV | MSTATUSH_GVA",
            write_sigupd(rd, test_data),
            write_sigupd(rd2, test_data),
            f"csrr x{rd}, mcause",
            write_sigupd(rd, test_data),
            # Ssdbltrp defines mtval2 only for double traps
            *([f"csrr x{rd}, mtval2", write_sigupd(rd, test_data)] if delegate else []),
            f"csrr x{rd}, mepc",
            f"LA(x{temp_reg}, {label})",
            f"sub x{rd}, x{rd}, x{temp_reg}",
            write_sigupd(rd, test_data),
            # An access-fault address may be reported as another invalid address, so only ebreak's mtval is recorded
            *([] if gate else [f"csrr x{rd}, mtval", write_sigupd(rd, test_data)]),
            f"csrr x{rd}, {x}status",
            f"LI(x{temp_reg}, SSTATUS_SDT | SSTATUS_SPP | SSTATUS_SPIE | SSTATUS_SIE)",
            f"and x{rd}, x{rd}, x{temp_reg}",
            write_sigupd(rd, test_data),
            f"csrr x{rd}, {x}cause",
            write_sigupd(rd, test_data),
            f"LA(x{temp_reg}, {label})",
            f"csrr x{rd}, {x}epc",
            f"sub x{rd}, x{rd}, x{temp_reg}",
            write_sigupd(rd, test_data),
            f"csrr x{rd}, {x}tval",
            f"sub x{rd}, x{rd}, x{temp_reg}",
            write_sigupd(rd, test_data),
            f"LI(x{temp_reg}, SSTATUS_SDT | SSTATUS_SPIE)",
            f"csrc {x}status, x{temp_reg}",
        ]
        lines.extend(gated(body, gate))
    if delegate:
        lines.extend(f"csrw {csr}, zero" for csr in deleg)
    test_data.int_regs.return_registers([save_mtvec, addr_reg, temp_reg, rd, rd2])
    return lines


def _vs_double_trap_tests(test_data: TestData) -> list[str]:
    """cp_vs_double_trap: a trap into VS-mode with vsstatus.SDT = 1 is a double trap taken in M-mode."""
    return [
        comment_banner(
            "cp_vs_double_trap",
            "With menvcfg.DTE = henvcfg.DTE = 1, vsstatus.SDT = 1 and medeleg = hedeleg = {cause}, ebreak or a load\n"
            "access fault in VS-mode is a double trap: mcause = 16, mtval2 = the cause, mepc and mtval as for the\n"
            "trap, mstatus.MPP = S and MPV = 1, and vsstatus, vsepc, vscause and vstval unchanged",
        ),
        *_sdt_traps_to_m(test_data, "VS", "cp_vs_double_trap", _HSM_CG, delegate=True),
    ]


def _m_xret_sdt_tests(test_data: TestData) -> list[str]:
    """cp_m_xret_vsstatus_sdt: with Smdbltrp, MRET and SRET in M-mode clear vsstatus.SDT only when they return to
    VU-mode, and clear sstatus.SDT when they return to VS-mode or VU-mode.  SRET in M-mode to HS-mode is left out:
    whether it clears sstatus.SDT is disputed."""
    temp_reg, rd, mask_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_m_xret_vsstatus_sdt",
            "With menvcfg.DTE = henvcfg.DTE = 1 and vsstatus.SDT = sstatus.SDT = 1, MRET and SRET in M-mode to\n"
            "VS-mode and VU-mode.  Back in M-mode, read vsstatus.SDT and sstatus.SDT",
        ),
        f"LI(x{mask_reg}, SSTATUS_SDT)",
    ]
    for instr in ("mret", "sret"):
        for mode in ("VS", "VU"):
            name = f"{instr}_to_{mode.lower()}"
            testcase = test_data.add_testcase(name, "cp_m_xret_vsstatus_sdt", _HSM_CG)
            target = f"{test_data.current_testcase_label}_{mode.lower()}"
            lines.extend(
                [
                    "",
                    f"csrs vsstatus, x{mask_reg}",
                    f"csrs sstatus, x{mask_reg}",
                    *_m_xret_to(instr, mode, temp_reg, target),
                    testcase,
                    instr,
                    f"{target}:",
                    "RVTEST_TSBI_GOTO_MMODE",
                    *_record_sdt(test_data, rd, mask_reg, name, "cp_m_xret_vsstatus_sdt", _HSM_CG),
                ]
            )
    lines.extend([f"csrc vsstatus, x{mask_reg}", f"csrc sstatus, x{mask_reg}"])
    test_data.int_regs.return_registers([temp_reg, rd, mask_reg])
    return gated(lines, "defined(SMDBLTRP_SUPPORTED)")


@add_priv_test_generator(
    "Ssdbltrp",
    required_extensions=["Sm", "Ssdbltrp", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_ssdbltrphsm(test_data: TestData) -> list[TestChunk]:
    """Generate the Ssdbltrp_HSm tests: double traps from VS-mode, and MRET and SRET in M-mode."""
    tc = test_data.begin_test_chunk("HSm")
    temp_reg = test_data.int_regs.get_register()
    tc.code.extend(_m_dte("csrs", temp_reg))
    test_data.int_regs.return_registers([temp_reg])
    tc.code.extend([*_vs_double_trap_tests(test_data), *_m_xret_sdt_tests(test_data)])
    temp_reg = test_data.int_regs.get_register()
    tc.code.extend(_m_dte("csrc", temp_reg))
    test_data.int_regs.return_registers([temp_reg])
    return [test_data.end_test_chunk()]


_SM_CG = "Ssdbltrp_Sm_cg"


def _s_ebreak(test_data: TestData, name: str, coverpoint: str, regs: list[int], s_code: list[str]) -> list[str]:
    """From M-mode, enter S-mode by MRET, run ``s_code``, and execute an ebreak that medeleg[3] sends to S-mode.

    stvec points just past the ebreak, so the trap resumes there in S-mode instead of in the framework's S-mode
    handler, whose SRET would clear sstatus.SDT.  The test returns to M-mode, puts stvec back, and records
    sstatus.SDT and scause.
    """
    save_stvec, temp_reg, rd = regs
    testcase = test_data.add_testcase(name, coverpoint, _SM_CG)
    label = test_data.current_testcase_label
    handler = f"{label}_stvec"
    return [
        f"csrr x{save_stvec}, stvec",
        f"andi x{temp_reg}, x{save_stvec}, 3   # keep the MODE the DUT uses",
        f"LA(x{rd}, {handler})",
        f"or x{rd}, x{rd}, x{temp_reg}",
        f"csrw stvec, x{rd}",
        *_m_xret_to("mret", "S", temp_reg, f"{label}_smode"),
        "mret",
        f"{label}_smode:",
        *s_code,
        testcase,
        "ebreak",
        *tvec_alignment("stvec"),
        f"{handler}:",
        "RVTEST_TSBI_GOTO_MMODE",
        f"csrw stvec, x{save_stvec}",
        f"csrr x{rd}, sstatus",
        f"LI(x{temp_reg}, SSTATUS_SDT)",
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
        f"csrr x{rd}, scause",
        write_sigupd(rd, test_data),
    ]


def _s_trap_sdt_tests(test_data: TestData) -> list[str]:
    """cp_s_trap_sdt: a breakpoint from S-mode delegated to S-mode with sstatus.SDT = 0 sets sstatus.SDT."""
    regs = test_data.int_regs.get_registers(3)
    temp_reg = regs[1]
    lines = [
        comment_banner(
            "cp_s_trap_sdt",
            "With menvcfg.DTE = 1, sstatus.SDT = 0 and medeleg[3] = 1, ebreak in S-mode is an ordinary trap into\n"
            "S-mode, which sets sstatus.SDT",
        ),
        f"LI(x{temp_reg}, SSTATUS_SDT)",
        f"csrc sstatus, x{temp_reg}",
        f"LI(x{temp_reg}, 1 << CAUSE_BREAKPOINT)",
        f"csrw medeleg, x{temp_reg}",
        *_s_ebreak(test_data, "ebreak", "cp_s_trap_sdt", regs, []),
        "csrw medeleg, zero",
        f"LI(x{temp_reg}, SSTATUS_SDT)",
        f"csrc sstatus, x{temp_reg}",
    ]
    test_data.int_regs.return_registers(regs)
    return lines


def _menvcfg_dte0_tests(test_data: TestData) -> list[str]:
    """cp_menvcfg_dte0: menvcfg.DTE = 0 makes sstatus.SDT read-only zero and disables double traps in S-mode.

    sstatus.SDT is set while menvcfg.DTE = 1, so reads and traps with menvcfg.DTE = 0 must ignore a stored 1.
    """
    regs = test_data.int_regs.get_registers(3)
    _, temp_reg, rd = regs
    sdt = f"LI(x{temp_reg}, SSTATUS_SDT)"
    s_code = [
        test_data.add_testcase("s_read", "cp_menvcfg_dte0", _SM_CG),
        f"csrr x{rd}, sstatus",
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
        test_data.add_testcase("s_write", "cp_menvcfg_dte0", _SM_CG),
        f"csrs sstatus, x{temp_reg}",
        f"csrr x{rd}, sstatus",
        f"and x{rd}, x{rd}, x{temp_reg}",
        write_sigupd(rd, test_data),
    ]
    lines = [
        comment_banner(
            "cp_menvcfg_dte0",
            "Set sstatus.SDT with menvcfg.DTE = 1, then clear menvcfg.DTE.  In S-mode, sstatus.SDT reads 0, a write\n"
            "of 1 leaves it 0, and ebreak with medeleg[3] = 1 is an ordinary trap into S-mode",
        ),
        sdt,
        f"csrs sstatus, x{temp_reg}",
        *_menvcfg_dte("csrc", temp_reg),
        f"LI(x{temp_reg}, 1 << CAUSE_BREAKPOINT)",
        f"csrw medeleg, x{temp_reg}",
        *_s_ebreak(test_data, "s_ebreak", "cp_menvcfg_dte0", regs, [sdt, *s_code]),
        "csrw medeleg, zero",
        "",
        "# Turn menvcfg.DTE back on and clear sstatus.SDT, whose value while it was read-only zero is not specified",
        *_menvcfg_dte("csrs", temp_reg),
        sdt,
        f"csrc sstatus, x{temp_reg}",
    ]
    test_data.int_regs.return_registers(regs)
    return lines


@add_priv_test_generator(
    "Ssdbltrp",
    required_extensions=["Sm", "Ssdbltrp", "S"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_ssdbltrpsm(test_data: TestData) -> list[TestChunk]:
    """Generate the Ssdbltrp_Sm tests: traps from S-mode with sstatus.SDT = 0 and 1, and menvcfg.DTE = 0."""
    tc = test_data.begin_test_chunk("Sm")
    temp_reg = test_data.int_regs.get_register()
    tc.code.extend(_menvcfg_dte("csrs", temp_reg))
    test_data.int_regs.return_registers([temp_reg])
    tc.code.extend(
        [
            comment_banner(
                "cp_s_double_trap",
                "With menvcfg.DTE = 1, sstatus.SDT = 1 and medeleg = {cause}, ebreak or a load access fault in S-mode\n"
                "is a double trap: mcause = 16, mtval2 = the cause, mepc and mtval as for the trap, mstatus.MPP = S and\n"
                "MPV = 0, and sstatus, sepc, scause and stval unchanged",
            ),
            *_sdt_traps_to_m(test_data, "S", "cp_s_double_trap", _SM_CG, delegate=True),
            comment_banner(
                "cp_s_sdt_mtrap",
                "With menvcfg.DTE = 1, sstatus.SDT = 1 and medeleg = 0, ebreak or a load access fault in S-mode is an\n"
                "ordinary trap into M-mode (mcause = the cause), and sstatus, sepc, scause and stval are unchanged",
            ),
            *_sdt_traps_to_m(test_data, "S", "cp_s_sdt_mtrap", _SM_CG, delegate=False),
            *_s_trap_sdt_tests(test_data),
            *_menvcfg_dte0_tests(test_data),
        ]
    )
    temp_reg = test_data.int_regs.get_register()
    tc.code.extend(_menvcfg_dte("csrc", temp_reg))
    test_data.int_regs.return_registers([temp_reg])
    return [test_data.end_test_chunk()]
