# SPDX-License-Identifier: Apache-2.0
"""H suite: CSR access from each mode, VS CSR substitution, and HS-qualified vs virtual-instruction rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hlib import (
    CSRS,
    HSTATUS,
    hs_bits,
    FORMS,
    HYP,
    ISSUE,
    MSTATUS_TVM,
    MUT,
    READS,
    VS_OF,
    WRITES,
    access_expect,
    csr_num,
    csr_window,
    form_value,
    hs_read,
    insn_window,
    m_bits,
    new,
    ILLEGAL,
    VIRTUAL,
    MRET,
    SRET,
)

if TYPE_CHECKING:
    from aigen import TestFile

# Expectation switches for mutate.py: each models a plausible design bug (AI_MUTANT=<key>).
MUTANTS = {
    "hgeip_write_virtual": "a VS/VU write of read-only hgeip raises virtual- instead of illegal-instruction",
    "vu_scsr_illegal": "VU-mode access to a supervisor CSR raises illegal- instead of virtual-instruction",
    "mcsr_virtual": "VS/VU access to an M-level CSR raises virtual- instead of illegal-instruction",
    "vscsr_vs_ok": "VS-mode may access a VS CSR by its own address",
    "rv64_high_virtual": "RV64 VS-mode access to a high-half H CSR address raises virtual-instruction",
    "hu_grants_csrs": "hstatus.HU=1 lets U-mode access VS and H CSRs",
    "mret_virtual": "MRET in VS/VU raises virtual- instead of illegal-instruction",
    "ro_counter_write_virtual": "a VS-mode write of a read-only counter raises virtual-instruction",
    "sub_no_write": "a VS-mode write of a supervisor CSR does not reach the VS CSR",
}

H_CSRS = [n for n, (_, c, _) in CSRS.items() if c == "H"]
VS_CSRS = [n for n, (_, c, _) in CSRS.items() if c == "VS"]
HIGH = {"hedelegh", "htimedeltah", "henvcfgh"}

ISSUE_HSQ = (
    "HS-qualified (hypervisor.adoc, Virtual Instruction): an instruction is HS-qualified if it would be valid in "
    "HS-mode for some register operands, assuming mstatus.TVM=0 and TSR=0. A CSR write that HS-mode may not do "
    "(a read-only CSR) is not HS-qualified, so it raises illegal-instruction from VS and VU too."
)


def guarded(t: TestFile, name: str, body) -> None:  # noqa: ANN001
    cond = CSRS[name][2]
    if cond:
        with t.only_if(cond):
            body()
    else:
        body()


def set_x6_for(t: TestFile, form, name: str) -> None:  # noqa: ANN001
    """x6 for a write form: the CSR's current value (read in HS-mode) for csrrw, 0 for csrrs/csrrc, so a
    write that wrongly succeeds leaves the CSR unchanged."""
    if form[1] == 1 and name not in ("satp", "hgatp", "vsatp"):  # HS reads of satp/hgatp trap when TVM=1
        hs_read(t, "x6", name)
    else:
        t.emit("li x6, 0")


def access(t: TestFile, mode: str, name: str, form, desc: str, expect: str | None = None) -> str:  # noqa: ANN001
    if expect is None:
        expect = access_expect(name, mode, form[5])
        if MUT == "hgeip_write_virtual" and name == "hgeip" and mode in ("VS", "VU") and form[5]:
            expect = "virtual"
        if MUT == "vu_scsr_illegal" and CSRS[name][1] in ("S", "SN") and mode == "VU":
            expect = "illegal"
        if MUT == "mcsr_virtual" and CSRS[name][1] == "M" and mode in ("VS", "VU"):
            expect = "virtual"
        if MUT == "vscsr_vs_ok" and CSRS[name][1] == "VS" and mode == "VS":
            expect = "ok"
    if form[5] and expect != "ok":
        if CSRS[name][1] in ("M", "U"):
            t.emit("li x6, 0")
        else:
            set_x6_for(t, form, name)
    return csr_window(t, mode, name, form, expect, desc)


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    tests: list[TestFile] = []

    # ---- H_csrs_hs_not_vs ----
    t = new("H_csrs_hs_not_vs")
    t.describe(
        source=HYP,
        rule_text="Additional CSRs are provided to HS-mode, but not to VS-mode, to manage two-stage address "
        "translation and to control the behavior of a VS-mode guest: hstatus, hedeleg, hideleg, hvip, hip, hie, "
        "hgeip, hgeie, henvcfg, henvcfgh, hcounteren, htimedelta, htimedeltah, htval, htinst, and hgatp.",
        context="henvcfgh, htimedeltah (and hedelegh) exist only on RV32. hgeip is read-only (address 0xE12), so "
        "an HS-mode write raises illegal-instruction. The exact cause of a VS or VU access is "
        "H_virtinst_vu_vs_nonhigh_allowedhs_tvm0.",
        plan="1. HS-mode reads every H CSR without a trap.\n"
        "2. HS-mode writes every writable H CSR with the value it just read (csrrw), without a trap; a write to "
        "hgeip raises illegal-instruction.\n"
        "3. VS-mode reads of every H CSR raise virtual-instruction (they are not provided to VS-mode).",
    )
    for name in H_CSRS:
        def body(name: str = name) -> None:
            csr_window(t, "S", name, FORMS[0], "ok", "HS-mode read")
            if name == "hgeip":
                access(t, "S", name, FORMS[1], "HS-mode write of a read-only CSR", "illegal")
            else:
                hs_read(t, "x6", name)
                csr_window(t, "S", name, FORMS[1], "ok", "HS-mode write of its own value")
            access(t, "VS", name, FORMS[0], "not provided to VS-mode")
        guarded(t, name, body)
    tests.append(t)

    # ---- H_virtinst_vu_vs_nonhigh_allowedhs_tvm0 ----
    t = new("H_virtinst_vu_vs_nonhigh_allowedhs_tvm0")
    t.describe(
        source=HYP,
        rule_text="in VS-mode or VU-mode, attempts to access an implemented non-high-half hypervisor CSR or VS "
        "CSR when the same access (read/write) would be allowed in HS-mode, assuming mstatus.TVM=0;",
        context="One of the cases that raise a virtual-instruction exception (H_cause_virtual_instruction). "
        + ISSUE_HSQ,
        plan="1. Every non-high-half H CSR and VS CSR, from VS-mode and from VU-mode: one read form and one write "
        "form each, rotating so that all eight CSR instruction forms occur (rs1=x0 and uimm=0 are reads). Each "
        "raises virtual-instruction with xtval 0 or the instruction bits, and xPP/xPV record the mode.\n"
        "2. hgeip is read-only: all eight forms in VS-mode; the reads raise virtual-instruction, the writes "
        "(including csrrs/csrrc with a zero-valued rs1 other than x0 and csrrwi) raise illegal-instruction. Its "
        "writes from VU-mode also raise illegal-instruction.\n"
        "3. mstatus.TVM=1 (which denies hgatp to HS-mode): VS and VU reads and writes of hgatp and vsatp still "
        "raise virtual-instruction, because the rule assumes TVM=0.",
    )
    i = 0
    for name in H_CSRS + VS_CSRS:
        if name in HIGH:
            continue

        def body(name: str = name) -> None:
            nonlocal i
            for mode in ("VS", "VU"):
                access(t, mode, name, READS[i % len(READS)], "all enables set")
                access(t, mode, name, WRITES[i % len(WRITES)], "all enables set")
                i += 1
        guarded(t, name, body)
    for form in FORMS:
        access(t, "VS", "hgeip", form, "read-only CSR")
    m_bits(t, "mstatus", MSTATUS_TVM, True, "M-mode: mstatus.TVM = 1")
    for mode in ("VS", "VU"):
        for name in ("hgatp", "vsatp"):
            access(t, mode, name, FORMS[0], "mstatus.TVM=1")
            access(t, mode, name, FORMS[1], "mstatus.TVM=1")
    m_bits(t, "mstatus", MSTATUS_TVM, False, "M-mode: mstatus.TVM = 0")
    tests.append(t)

    # ---- H_virtinst_vu_vs32_high_allowedhs_tvm0 ----
    t = new("H_virtinst_vu_vs32_high_allowedhs_tvm0")
    t.describe(
        source=HYP,
        rule_text="in VS-mode or VU-mode, if XLEN=32, attempts to access an implemented high-half hypervisor "
        "CSR or high-half VS CSR when the same access (read/write) to the CSR's low-half partner would be allowed "
        "in HS-mode, assuming mstatus.TVM=0;",
        context="The high-half H CSRs are hedelegh, htimedeltah and henvcfgh (vstimecmph is covered by the Sstc "
        "suite). On RV64 these addresses are not CSRs: no access is valid in HS-mode, so the instruction is not "
        "HS-qualified and VS-mode access raises illegal-instruction.",
        issues=ISSUE_HSQ,
        plan="1. RV32: HS-mode reads each high-half H CSR without a trap; VS-mode and VU-mode reads and writes "
        "(all eight forms over the three CSRs) raise virtual-instruction; U-mode access raises "
        "illegal-instruction.\n"
        "2. RV64: HS-mode and VS-mode reads of 0x612, 0x615 and 0x61A raise illegal-instruction.",
    )
    with t.rv32_only():
        k = 0
        for name in sorted(HIGH):
            def body(name: str = name) -> None:
                nonlocal k
                csr_window(t, "S", name, FORMS[0], "ok", "HS-mode read")
                for mode in ("VS", "VU"):
                    for _ in range(2):
                        access(t, mode, name, FORMS[k % 8], "RV32 high half")
                        k += 1
                access(t, "U", name, FORMS[k % 8], "RV32 high half")
            guarded(t, name, body)
    with t.rv64_only():
        for name in sorted(HIGH):
            for mode in ("S", "VS"):
                exp = "virtual" if (mode == "VS" and MUT == "rv64_high_virtual") else "illegal"
                csr_window(t, mode, name, FORMS[0], exp, "RV64: not a CSR")
    tests.append(t)

    # ---- H_vscsrs_acc_vs ----
    t = new("H_vscsrs_acc_vs")
    t.describe(
        source=HYP,
        rule_text="When V=1, an attempt to read or write a VS CSR directly by its own separate CSR address "
        "causes a virtual-instruction exception.",
        context="The VS CSRs are vsstatus, vsie, vstvec, vsscratch, vsepc, vscause, vstval, vsip and vsatp "
        "(vstimecmp is covered by the Sstc suite). Write forms carry the CSR's current value (csrrw) or zero "
        "(csrrs/csrrc), so a write that wrongly succeeds changes nothing.",
        plan="1. VS-mode: all eight CSR instruction forms on each VS CSR by its own address raise "
        "virtual-instruction, with xtval 0 or the instruction bits and xPP/xPV recording VS.\n"
        "2. VU-mode (also V=1): a read and a write of each VS CSR raise virtual-instruction.",
    )
    for j, name in enumerate(VS_CSRS):
        for form in FORMS:
            access(t, "VS", name, form, "own address, V=1")
        access(t, "VU", name, READS[j % 2], "own address, V=1")
        access(t, "VU", name, WRITES[j % len(WRITES)], "own address, V=1")
    tests.append(t)

    # ---- H_vscsrs_acc_u ----
    t = new("H_vscsrs_acc_u")
    t.describe(
        source=HYP,
        rule_text="Attempts from U-mode cause an illegal-instruction exception as usual.",
        context="The previous sentence (H_vscsrs_acc_vs) concerns access to a VS CSR by its own address. U-mode "
        "here is V=0. hstatus.HU=1 grants U-mode the hypervisor load/store instructions only, not CSR access.",
        plan="1. U-mode (V=0), hstatus.HU=0: a read and a write of each VS CSR (rotating forms) raise "
        "illegal-instruction with xtval 0 or the instruction bits.\n"
        "2. The same with hstatus.HU=1.\n"
        "3. U-mode access to the H CSRs (hstatus, hgatp, hvip) also raises illegal-instruction, with HU=0 and "
        "HU=1.",
    )
    for hu in (0, 1):
        hs_bits(t, "hstatus", HSTATUS["HU"], bool(hu), f"hstatus.HU = {hu}")
        for j, name in enumerate(VS_CSRS + ["hstatus", "hgatp", "hvip"]):
            exp = "ok" if (MUT == "hu_grants_csrs" and hu) else "illegal"
            access(t, "U", name, READS[j % 2], f"hstatus.HU={hu}", exp)
            access(t, "U", name, WRITES[(j + hu) % len(WRITES)], f"hstatus.HU={hu}", exp)
    hs_bits(t, "hstatus", HSTATUS["HU"], False, "hstatus.HU = 0")
    tests.append(t)

    # ---- H_virtinst_vu_nonhigh_supervisor_allowedhs_tvm0 ----
    t = new("H_virtinst_vu_nonhigh_supervisor_allowedhs_tvm0")
    sup = [n for n, (_, c, _) in CSRS.items() if c in ("S", "SN")]
    t.describe(
        source=HYP,
        rule_text="in VU-mode, attempts to access an implemented non-high-half supervisor CSR when the same access "
        "(read/write) would be allowed in HS-mode, assuming mstatus.TVM=0;",
        context="One of the cases that raise a virtual-instruction exception. The supervisor CSRs tested are "
        + ", ".join(sup)
        + ", and sstateen0 with Ssstateen. In VS-mode the same accesses succeed (on the VS CSR where one "
        "substitutes); in U-mode (V=0) they raise illegal-instruction. stimecmp is covered by the Sstc suite.",
        issues=ISSUE_HSQ,
        plan="1. VU-mode: a read and a write of each supervisor CSR (rotating forms) raise virtual-instruction "
        "with xtval 0 or the instruction bits and xPP/xPV recording VU.\n"
        "2. U-mode (V=0): the same reads raise illegal-instruction.\n"
        "3. VS-mode: the same reads succeed.\n"
        "4. mstatus.TVM=1: VU-mode reads and writes of satp still raise virtual-instruction.",
    )
    for j, name in enumerate(sup + ["sstateen0"]):
        def body(name: str = name, j: int = j) -> None:
            access(t, "VU", name, READS[j % 2], "all enables set")
            access(t, "VU", name, WRITES[j % len(WRITES)], "all enables set")
            access(t, "U", name, READS[(j + 1) % 2], "V=0")
            access(t, "VS", name, READS[j % 2], "VS-mode, all enables set")
        guarded(t, name, body)
    m_bits(t, "mstatus", MSTATUS_TVM, True, "M-mode: mstatus.TVM = 1")
    access(t, "VU", "satp", FORMS[0], "mstatus.TVM=1")
    access(t, "VU", "satp", FORMS[1], "mstatus.TVM=1")
    m_bits(t, "mstatus", MSTATUS_TVM, False, "M-mode: mstatus.TVM = 0")
    tests.append(t)

    # ---- H_cause_virtual_instruction ----
    t = new("H_cause_virtual_instruction")
    mcsrs = [n for n, (_, c, _) in CSRS.items() if c == "M"]
    t.describe(
        source=HYP,
        rule_text="When V=1, a virtual-instruction exception (code 22) is normally raised instead of an "
        "illegal-instruction exception if the attempted instruction is HS-qualified but is prevented from "
        "executing when V=1 either due to insufficient privilege or because the instruction is expressly "
        "disabled by a supervisor or hypervisor CSR such as scounteren or hcounteren. An instruction is "
        "HS-qualified if it would be valid to execute in HS-mode (for some values of the instruction's register "
        "operands), assuming fields TSR and TVM of CSR mstatus are both zero.",
        context="The positive cases are enumerated in the H_virtinst_* rules. This test checks the boundary: "
        "instructions that are not valid in HS-mode raise illegal-instruction from VS and VU, and HS-qualified "
        "ones raise virtual-instruction.",
        issues=ISSUE_HSQ,
        plan="1. M-level CSRs (" + ", ".join(mcsrs) + "): a VS-mode and a VU-mode read raise illegal-instruction.\n"
        "2. MRET from VS and VU raises illegal-instruction; so do MNRET and DRET (not valid outside M-mode or "
        "Debug Mode).\n"
        "3. Writes to read-only counters (cycle, time, instret with Zicntr) from VS-mode, with mcounteren and "
        "hcounteren all set, raise illegal-instruction (HS-mode may not write them either).\n"
        "4. Contrast, HS-qualified: SRET from VU-mode and a VU-mode read of sscratch raise virtual-instruction.",
    )
    for j, name in enumerate(mcsrs):
        for mode in ("VS", "VU"):
            access(t, mode, name, READS[(j + (mode == "VU")) % 2], "M-level CSR")
    for e, note in ((MRET, "mret"), (0x70200073, "mnret"), (0x7B200073, "dret")):
        for mode in ("VS", "VU"):
            exp = VIRTUAL if (MUT == "mret_virtual" and note == "mret") else ILLEGAL
            insn_window(t, mode, e, note, exp, "not valid in HS-mode")
    with t.only_if("defined(ZICNTR_SUPPORTED)"):
        for num, name in ((0xC00, "cycle"), (0xC01, "time"), (0xC02, "instret")):
            exp = "virtual" if MUT == "ro_counter_write_virtual" else "illegal"
            for form in (FORMS[1], FORMS[3], FORMS[5]):
                t.emit("li x6, 0")
                csr_window(t, "VS", name, form, exp, "write to a read-only counter")
    insn_window(t, "VU", SRET, "sret", VIRTUAL, "HS-qualified, insufficient privilege")
    access(t, "VU", "sscratch", FORMS[0], "HS-qualified, insufficient privilege")
    tests.append(t)

    tests += gen_sub()
    tests.append(gen_acc_m_hs())
    return tests


# ---------------------------------------------------------------- VS CSR substitution
SUB_RULES = {
    "vsscratch": ("vsscratch_sz_acc_op", "The vsscratch register is a VSXLEN-bit read/write register that is "
                  "VS-mode's version of supervisor register sscratch, formatted as shown in <<vsscratchreg>>. "
                  "When V=1, vsscratch substitutes for the usual sscratch, so instructions that normally read or "
                  "modify sscratch actually access vsscratch instead. The contents of vsscratch never directly "
                  "affect the behavior of the machine."),
    "vsepc": ("vsepc_sz_acc_op", "The vsepc register is a VSXLEN-bit read/write register that is VS-mode's "
              "version of supervisor register sepc, formatted as shown in <<vsepcreg>>. When V=1, vsepc "
              "substitutes for the usual sepc, so instructions that normally read or modify sepc actually access "
              "vsepc instead. When V=0, vsepc does not directly affect the behavior of the machine."),
    "vscause": ("vscause_sz_acc_op", "The vscause register is a VSXLEN-bit read/write register that is VS-mode's "
                "version of supervisor register scause, formatted as shown in <<vscausereg>>. When V=1, vscause "
                "substitutes for the usual scause, so instructions that normally read or modify scause actually "
                "access vscause instead. When V=0, vscause does not directly affect the behavior of the machine."),
    "vstval": ("vstval_sz_acc_op", "The vstval register is a VSXLEN-bit read/write register that is VS-mode's "
               "version of supervisor register stval, formatted as shown in <<vstvalreg>>. When V=1, vstval "
               "substitutes for the usual stval, so instructions that normally read or modify stval actually "
               "access vstval instead. When V=0, vstval does not directly affect the behavior of the machine."),
    "vstvec": ("vstvec_sz_acc_op", "The vstvec register is a VSXLEN-bit read/write register that is VS-mode's "
               "version of supervisor register stvec, formatted as shown in <<norm:vstvec_img>>. When V=1, vstvec "
               "substitutes for the usual stvec, so instructions that normally read or modify stvec actually "
               "access vstvec instead. When V=0, vstvec does not directly affect the behavior of the machine."),
    "vsstatus": ("vsstatus_sz_acc_op", "The vsstatus register is a VSXLEN-bit read/write register that is "
                 "VS-mode's version of supervisor register sstatus, formatted as shown in <<vsstatusreg-rv32>> "
                 "when VSXLEN=32 and <<vsstatusreg>> when VSXLEN=64. When V=1, vsstatus substitutes for the usual "
                 "sstatus, so instructions that normally read or modify sstatus actually access vsstatus "
                 "instead."),
}


def eq(t: TestFile, a: str, b: str, lab: str, desc: str) -> None:
    """Check that registers a and b are equal (x5 = (a == b))."""
    t.emit(f"xor x5, {a}, {b}")
    t.emit("seqz x5, x5")
    t.check_bool("x5", lab, desc)


def gen_sub() -> list[TestFile]:
    """One test per VS CSR substitution rule, plus H_vscsrs_sub over all of them.

    Fully writable registers (vsscratch) check exact values. The others are WARL or WLRL, so the test writes
    legal values only and compares the VS-mode view with the HS-mode view of the VS CSR. CSRs the framework
    relies on in HS-mode (sscratch, stvec) are written from VS-mode with their own HS-mode value, so a write
    that wrongly lands in the HS CSR leaves it intact and is still caught."""
    tests = []
    # (csr, VS values of the old value and the x6 source per form index, HS-sensitive)
    for vcsr, (rule, text) in SUB_RULES.items():
        scsr = {v: s for s, v in VS_OF.items()}[vcsr]
        t = new(rule)
        sens = scsr in ("sscratch", "stvec")
        ctx = {
            "vsscratch": "sscratch and vsscratch hold the framework's trap save-area pointers, so the test saves "
            "vsscratch and restores it; VS-mode writes carry HS-mode's sscratch value.",
            "vsepc": "vsepc is WARL with the same legal values as sepc; the values used are 4-byte aligned "
            "addresses. HS-mode's own sepc is rewritten by the trap that ends each VS-mode window, so only the "
            "VS CSR is checked.",
            "vscause": "vscause is WLRL, so only legal scause values are written (exception codes 1, 2, 3, 5, 7, "
            "13, 15 and the supervisor interrupt codes); every set or clear form in the test produces a legal "
            "value.",
            "vstval": "vstval is WARL holding the values stval can hold; the values used are small positive "
            "addresses, valid in every translation mode.",
            "vstvec": "stvec holds the framework's HS-mode handler, so VS-mode writes carry HS-mode's stvec "
            "value; MODE is WARL (Direct is always legal), so the test checks consistency between the views.",
            "vsstatus": "The test toggles SUM (bit 18) and MXR (bit 19), which are writable in vsstatus and "
            "harmless while vsatp is Bare, and leaves the other fields alone.",
        }[vcsr]
        t.describe(
            source=HYP,
            rule_text=text,
            context=ctx,
            plan=f"1. HS-mode writes {vcsr} = A. In VS-mode, every CSR instruction form on {scsr} returns A "
            f"(rs1=x0 and uimm=0 forms do not write), and HS-mode then reads the new value from {vcsr}.\n"
            f"2. A VS-mode write of {scsr} does not change HS-mode's {scsr}"
            + (" (checked across the window)." if scsr in ("sscratch", "stvec", "sstatus") else
               " (not checkable: the trap that ends the window rewrites it); the value reaches " + vcsr + ".")
            + f"\n3. VU-mode access to {scsr} raises virtual-instruction (VU-mode never reaches {vcsr}).",
        )
        num_v, num_s = csr_num(vcsr), csr_num(scsr)
        if vcsr == "vsscratch":
            t.emit(f"csrr x1, {hex(num_v)}  // save vsscratch (framework VS save area)")
        if vcsr == "vstvec":
            t.emit(f"csrr x1, {hex(num_v)}  // save vstvec (framework VS handler)")
        if sens:
            plans = [(f, None) for f in FORMS]
        elif vcsr == "vsepc":
            plans = [(FORMS[i], v) for i, v in enumerate(
                [(0x1000, 0), (0x1000, 0x2340), (0x2340, 0x4448), (0x4448, 0x10), (0x4458, 0x4400),
                 (0x58, None), (0x14, None), (0x14, None)])]
        elif vcsr == "vscause":
            plans = [(FORMS[i], v) for i, v in enumerate(
                [(2, 0), (2, 5), (5, 13), (13, 2), (15, 8), (1, None), (0x15, None), (0x15, None)])]
        elif vcsr == "vstval":
            plans = [(FORMS[i], v) for i, v in enumerate(
                [(0x1234, 0), (0x1234, 0x5678), (0x5678, 0x7FF0), (0x7FF0, 0x0F), (0x7FFF, 0xF0),
                 (0x7F0F, None), (0x15, None), (0x1F, None)])]
        else:  # vsstatus: SUM/MXR in x6
            plans = [(FORMS[i], v) for i, v in enumerate(
                [(None, 0), (None, 0x40000), (None, 0xC0000), (None, 0x80000), (None, 0x40000)])]
        for form, vals in plans:
            asm, f3, rd, rs1, kind, writes = form
            line = asm.format(c=hex(num_s)) + f"  // {scsr} (V=1: {vcsr})"
            t.comment(f"{kind} of {scsr} in VS-mode")
            if sens and f3 in (5, 7):
                continue  # an immediate write that wrongly lands in the HS CSR would break the framework
            if sens:
                # x8 = HS-mode value; old vcsr value A = HS value ^ pattern (distinct from it)
                hs_read(t, "x8", scsr)
                t.load("x9", 0x5A0 if vcsr == "vsscratch" else 0x100, "pattern that makes A differ from it")
                t.emit("xor x9, x8, x9")
                t.emit(f"csrw {hex(num_v)}, x9  // {vcsr} = A")
                reads_only = rs1 == 0 and f3 in (2, 3)
                if f3 in (1, 2) and not reads_only:
                    t.emit("mv x6, x8")  # csrrw: the HS value; csrrs: A | HS (HS | HS = HS on a wrong landing)
                elif f3 == 3 and not reads_only:
                    t.emit("not x6, x8")  # csrrc: A & HS (HS & ~~HS = HS on a wrong landing)
                lab = t.window("VS", [line], "ok", f"{kind} of {scsr}")
                hs_read(t, "x6", vcsr)  # new vcsr value (HS view)
                if rd:
                    eq(t, "x7", "x9", lab, f"{kind} of {scsr} in VS-mode returns the old {vcsr}")
                # expected new value of vcsr from A (x9) and the source
                if reads_only or f3 == 6 or MUT == "sub_no_write":
                    exp = "x9"
                elif f3 == 1:
                    exp = "x8"
                elif f3 == 2:
                    t.emit("or x7, x9, x8")
                    exp = "x7"
                elif f3 == 3:
                    t.emit("and x7, x9, x8")
                    exp = "x7"
                else:
                    raise AssertionError(form)
                if vcsr == "vsscratch":
                    eq(t, "x6", exp, lab, f"{kind} of {scsr} in VS-mode leaves the expected value in {vcsr}")
                else:
                    # vstvec is WARL: the HS view equals what VS-mode reads back
                    t.window("VS", [f"csrr x7, {hex(num_s)}  // {scsr}"], "ok", f"read back {scsr}")
                    eq(t, "x6", "x7", lab, f"the VS-mode view of {scsr} equals HS-mode's {vcsr}")
                hs_read(t, "x7", scsr)
                eq(t, "x7", "x8", lab, f"{kind} of {scsr} in VS-mode leaves HS-mode's {scsr}")
            elif vcsr == "vsstatus":
                old, src = vals
                bits = 0xC0000
                t.li("x7", bits)
                t.emit(f"csrc {hex(num_v)}, x7  // vsstatus.SUM = MXR = 0")
                t.emit(f"csrc {hex(num_s)}, x7  // HS sstatus.SUM = MXR = 0")
                t.li("x7", 0x40000)
                t.emit(f"csrs {hex(num_v)}, x7  // vsstatus.SUM = 1 (A)")
                if src is not None:
                    t.load("x6", src, "source value (SUM/MXR bits)")
                if f3 in (5, 6, 7):
                    continue
                lab = t.window("VS", [line], "ok", f"{kind} of {scsr}")
                if rd:
                    t.load("x5", bits, "SUM|MXR")
                    t.emit("and x7, x7, x5")
                    t.check("x7", 0x40000, lab, f"{kind} of sstatus in VS-mode returns vsstatus (SUM=1, MXR=0)")
                _, new_v = form_value(form, 0x40000, src or 0, 32)
                if MUT == "sub_no_write":
                    new_v = 0x40000
                hs_read(t, "x7", vcsr)
                t.check_masked("x7", bits, new_v & bits, lab, f"{kind} of sstatus in VS-mode lands in vsstatus")
                hs_read(t, "x7", scsr)
                t.check_masked("x7", bits, 0, lab, f"{kind} of sstatus in VS-mode leaves HS sstatus.SUM/MXR = 0")
            else:
                old, src = vals
                t.load("x7", old, f"A, the old {vcsr}")
                t.emit(f"csrw {hex(num_v)}, x7  // {vcsr} = A")
                if src is not None:
                    t.load("x6", src, "source register value")
                lab = t.window("VS", [line], "ok", f"{kind} of {scsr}")
                if rd:
                    t.check("x7", old, lab, f"{kind} of {scsr} in VS-mode returns the old {vcsr}")
                _, new_v = form_value(form, old if MUT != "sub_no_write" else old, src or 0, 32)
                if MUT == "sub_no_write":
                    new_v = old
                if vcsr == "vsepc":
                    new_v &= ~1  # vsepc[0] is always zero
                hs_read(t, "x7", vcsr)
                t.check("x7", new_v, lab, f"{kind} of {scsr} in VS-mode leaves {hex(new_v)} in {vcsr}")
        access(t, "VU", scsr, FORMS[0], f"VU-mode never reaches {vcsr}")
        if vcsr in ("vsscratch", "vstvec"):
            t.emit(f"csrw {hex(num_v)}, x1  // restore {vcsr}")
        tests.append(t)

    # ---- H_vscsrs_sub (overview: every VS CSR is what VS-mode reads) ----
    t = new("H_vscsrs_sub")
    t.describe(
        source=HYP,
        rule_text="When V=1, the VS CSRs substitute for the corresponding supervisor CSRs, taking over all "
        "functions of the usual supervisor CSRs except as specified otherwise. Instructions that normally read "
        "or modify a supervisor CSR shall instead access the corresponding VS CSR.",
        context="The per-CSR tests (vs*_sz_acc_op) check every instruction form. This test checks the read "
        "routing of each pair at once, with HS-mode and VS-mode values that differ. vsie/vsip routing depends "
        "on hideleg and is covered by the interrupt tests; vsatp by H_virtinst_vs_sfence_sinval_satp_vtvm1.",
        plan="1. HS-mode makes vsscratch, vsepc, vscause and vstval differ from their supervisor partners, and "
        "vsstatus.SUM differ from sstatus.SUM.\n"
        "2. A VS-mode read of each supervisor CSR returns the VS CSR's value.",
    )
    t.emit(f"csrr x1, {hex(csr_num('vsscratch'))}  // save vsscratch")
    for vcsr, val in (("vsepc", 0x2468), ("vscause", 13), ("vstval", 0x7654)):
        t.load("x7", val, f"{vcsr} value")
        t.emit(f"csrw {hex(csr_num(vcsr))}, x7  // {vcsr}")
    hs_read(t, "x8", "sscratch")
    t.emit("xori x8, x8, 0x7F0")
    t.emit(f"csrw {hex(csr_num('vsscratch'))}, x8  // vsscratch = sscratch ^ 0x7F0")
    t.li("x7", 0x40000)
    t.emit(f"csrc {hex(csr_num('sstatus'))}, x7  // sstatus.SUM = 0")
    t.emit(f"csrs {hex(csr_num('vsstatus'))}, x7  // vsstatus.SUM = 1")
    for scsr, val in (("sepc", 0x2468), ("scause", 13), ("stval", 0x7654), ("sscratch", None), ("sstatus", None)):
        lab = t.window("VS", [f"csrr x7, {hex(csr_num(scsr))}  // {scsr} (V=1: {VS_OF[scsr]})"], "ok", f"read {scsr}")
        if scsr == "sscratch":
            eq(t, "x7", "x8", lab, "a VS-mode read of sscratch returns vsscratch")
        elif scsr == "sstatus":
            t.check_masked("x7", 0x40000, 0x40000, lab, "a VS-mode read of sstatus returns vsstatus (SUM=1)")
        else:
            t.check("x7", val, lab, f"a VS-mode read of {scsr} returns {VS_OF[scsr]}")
    t.li("x7", 0x40000)
    t.emit(f"csrc {hex(csr_num('vsstatus'))}, x7  // vsstatus.SUM = 0")
    t.emit(f"csrw {hex(csr_num('vsscratch'))}, x1  // restore vsscratch")
    tests.append(t)
    return tests


def gen_acc_m_hs() -> TestFile:
    t = new("H_vscsrs_acc_m_hs")
    t.describe(
        source=HYP,
        rule_text="The VS CSRs can be accessed as themselves only from M-mode or HS-mode.",
        context="vsscratch is fully writable; the framework keeps its VS save-area pointer there, so the test "
        "saves and restores it. vsepc, vscause and vstval are written with legal values. T-SBI performs M-mode "
        "accesses.",
        plan="1. HS-mode: all eight CSR instruction forms on vsscratch, with exact old and new values.\n"
        "2. HS-mode writes vsepc, vscause and vstval and reads them back.\n"
        "3. M-mode writes vsscratch and HS-mode reads the value; HS-mode writes it and M-mode reads the value.",
    )
    num = csr_num("vsscratch")
    t.emit(f"csrr x1, {hex(num)}  // save vsscratch")
    old = t.rand(32) | 0x15
    for form in FORMS:
        asm, f3, rd, rs1, kind, _ = form
        src = t.rand(32)
        t.load("x7", old, "old vsscratch")
        t.emit(f"csrw {hex(num)}, x7")
        t.load("x6", src, "source")
        lab = t.window("S", [asm.format(c=hex(num)) + "  // vsscratch"], "ok", f"{kind} of vsscratch in HS-mode")
        rdv, newv = form_value(form, old, src, 32)
        if rd:
            t.check("x7", old, lab, f"{kind} of vsscratch in HS-mode returns the old value")
        hs_read(t, "x7", "vsscratch")
        t.check("x7", newv, lab, f"{kind} of vsscratch in HS-mode writes {hex(newv)}")
        old = newv | 0x15
    for name, v in (("vsepc", 0x3AB4), ("vscause", 7), ("vstval", 0x6C3)):
        lab = t.label("rt")
        t.load("x7", v, f"{name} value")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(csr_num(name))}, x7  // {name}")
        hs_read(t, "x7", name)
        t.check("x7", v, lab, f"HS-mode write of {name} reads back")
    lab = t.label("m")
    t.emit(f"{lab}:", 0)
    t.load("a1", 0x13579BD, "value M-mode writes")
    t.tsbi_csr("WRITE", "VSSCRATCH", "a1")
    hs_read(t, "x7", "vsscratch")
    t.check("x7", 0x13579BD, lab, "an M-mode write of vsscratch is read in HS-mode")
    t.load("x7", 0x2468ACE, "value HS-mode writes")
    t.emit(f"csrw {hex(num)}, x7")
    t.tsbi_csr("READ", "VSSCRATCH")
    t.check("a0", 0x2468ACE, lab, "an HS-mode write of vsscratch is read in M-mode")
    t.emit(f"csrw {hex(num)}, x1  // restore vsscratch")
    return t
