# SPDX-License-Identifier: Apache-2.0
"""H suite: trap-control bits (VTSR, VTW, VTVM, TSR, TW, TVM), validity of the hypervisor instructions,
FS/VS context status with V=1, cache-block enables in henvcfg, supervisor CSRs without a VS copy, and SRET
in VS-mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

import hlib
from aigen import POOL_TRAP, TestFile
from hlib import (
    FORMS,
    HSTATUS,
    HYP,
    ILLEGAL,
    ISSUE,
    MSTATUS_TSR,
    MSTATUS_TVM,
    MSTATUS_TW,
    READS,
    SRET,
    VIRTUAL,
    WFI,
    csr_num,
    csr_window,
    enc_csr,
    hfence_gvma,
    hfence_vvma,
    hinval_gvma,
    hinval_vvma,
    hlsv,
    hs_bits,
    hs_read,
    m_bits,
    sfence_vma,
    sinval_vma,
    word,
)

if TYPE_CHECKING:
    from aigen import Expect

MUT = hlib.MUT
SVINVAL = "defined(SVINVAL_SUPPORTED)"
F = "defined(F_SUPPORTED)"
V = "defined(V_SUPPORTED)"
CBOZ = "defined(ZICBOZ_SUPPORTED)"
CBOM = "defined(ZICBOM_SUPPORTED)"
SVI_FILE = "src/priv/svinval.adoc"

# Expectation switches for mutate.py: each models a plausible design bug (AI_MUTANT=<key>).
MUTANTS = {
    "vtsr_ignored": "hstatus.VTSR=1 does not trap SRET in VS-mode",
    "vtsr_illegal": "SRET in VS-mode with VTSR=1 raises illegal- instead of virtual-instruction",
    "vtsr_traps_hs": "hstatus.VTSR=1 also traps SRET in HS-mode",
    "vtw_illegal": "WFI in VS-mode with VTW=1 raises illegal- instead of virtual-instruction",
    "vtw0_traps": "WFI in VS-mode with VTW=0, TW=0 and a wake-up pending raises virtual-instruction",
    "tw_virtual": "WFI in VS-mode with TW=1 raises virtual- instead of illegal-instruction",
    "vu_wfi_illegal": "WFI in VU-mode with TW=0 raises illegal- instead of virtual-instruction",
    "vu_sret_illegal": "SRET/SFENCE in VU-mode raise illegal- instead of virtual-instruction",
    "vtvm_ignored": "hstatus.VTVM=1 does not trap satp, SFENCE.VMA or SINVAL.VMA in VS-mode",
    "vtvm_illegal": "VTVM traps raise illegal- instead of virtual-instruction",
    "vtvm_traps_hs": "hstatus.VTVM=1 also traps satp in HS-mode",
    "vtvm_traps_wfence": "hstatus.VTVM=1 traps SFENCE.W.INVAL in VS-mode",
    "tvm_affects_vs": "mstatus.TVM=1 traps satp and SFENCE.VMA in VS-mode",
    "tsr_affects_vs": "mstatus.TSR=1 traps SRET in VS-mode",
    "tw_ignored_vu": "mstatus.TW=1 does not affect WFI in VU-mode",
    "tvm_hgatp_ok": "mstatus.TVM=1 does not stop HS-mode hgatp access",
    "tvm_traps_vvma": "mstatus.TVM=1 traps HFENCE.VVMA in HS-mode",
    "tvm_vs_hgatp_illegal": "with mstatus.TVM=1, VS-mode hgatp access raises illegal-instruction",
    "hfence_u_hu": "hstatus.HU=1 lets U-mode execute HFENCE",
    "hfence_vs_illegal": "HFENCE in VS-mode raises illegal- instead of virtual-instruction",
    "hlv_vs_illegal": "HLV/HSV in VS/VU-mode raise illegal- instead of virtual-instruction",
    "hu_ignored": "hstatus.HU=1 does not enable HLV/HSV in U-mode",
    "hu0_allows": "HLV/HSV execute in U-mode with hstatus.HU=0",
    "hsv_vs_writes": "a trapping HSV in VS-mode still writes memory",
    "xtval_virtual_other": "a virtual-instruction trap writes stval with a value that is neither 0 nor the bits",
    "fs_virtual": "FS=0 in vsstatus raises virtual- instead of illegal-instruction",
    "fs_hs_ignored": "sstatus.FS=0 does not disable floating point in VS-mode",
    "fs_dirty_vs_only": "modifying floating-point state in VS-mode does not set sstatus.FS to Dirty",
    "fs_dirty_v0": "modifying floating-point state in HS-mode sets vsstatus.FS to Dirty",
    "sd_uses_hs_fs": "vsstatus.SD follows the HS-level sstatus.FS",
    "cbze_illegal": "henvcfg.CBZE=0 makes CBO.ZERO illegal- instead of virtual-instruction in VS-mode",
    "cbze_ignored": "henvcfg.CBZE=0 does not disable CBO.ZERO in VS-mode",
    "cbze_affects_hs": "henvcfg.CBZE=0 disables CBO.ZERO in HS-mode",
    "cbze_vu_ignores_senvcfg": "senvcfg.CBZE=0 does not disable CBO.ZERO in VU-mode",
    "cbze_menvcfg_virtual": "menvcfg.CBZE=0 makes CBO.ZERO virtual- instead of illegal-instruction in VS-mode",
    "cbcfe_ignored": "henvcfg.CBCFE=0 does not disable CBO.CLEAN/FLUSH in VS-mode",
    "cbie_ignored": "henvcfg.CBIE=00 does not disable CBO.INVAL in VS-mode",
    "cbie_menvcfg_virtual": "menvcfg.CBIE=00 makes CBO.INVAL virtual- instead of illegal-instruction in VS-mode",
    "scounteren_shadowed": "a VS-mode write of scounteren does not reach the HS-level scounteren",
    "sret_v1_spie": "SRET in VS-mode leaves vsstatus.SPIE unchanged",
    "sret_v1_spp": "SRET in VS-mode leaves vsstatus.SPP unchanged",
    "sret_v1_sie": "SRET in VS-mode leaves vsstatus.SIE unchanged",
}


# ---------------------------------------------------------------- helpers
class VTest(TestFile):
    """TestFile with a 4 KiB-aligned scratch page and labels valid for rule names that contain '-'."""

    def __init__(self, *a: object, scratch: bool = False, **kw: object) -> None:
        super().__init__(*a, **kw)
        self.scratch = scratch
        self.sym = self.rule.replace("-", "_")

    def label(self, stem: str) -> str:
        self._lab += 1
        return f"{self.sym}_{stem}_{self._lab}"

    def render(self) -> str:
        s = super().render()
        if self.scratch:
            extra = "  .p2align 12\nai_scratch:\n  .space 4096\n"
            s = s.replace("\nRVTEST_DATA_END", "\n" + extra + "RVTEST_DATA_END", 1)
        return s


def new(rule: str, required: list[str] | None = None, **kw: object) -> VTest:
    kw.setdefault("boot", "S")
    kw.setdefault("pool", POOL_TRAP)
    kw.setdefault("march", hlib.MARCH)
    return VTest(hlib.SUITE, rule, required=required or hlib.REQ, **kw)


def new_sm(rule: str, required: list[str] | None = None, **kw: object) -> VTest:
    kw["boot"] = "M"
    kw["suffix"] = "_Sm"
    return new(rule, required or [*hlib.REQ, "Sm"], **kw)


def iw(t: TestFile, mode: str, e: int, note: str, expect: Expect, desc: str, more: list[str] = (),
       pre: list[str] = (), tval: Expect | None = None) -> str:
    """One instruction (encoding e) in `mode` inside a trap window; illegal and virtual traps must leave xtval
    0 or the instruction bits (or `tval`). `pre` lines run in the mode before it (not part of the window's
    first line)."""
    alts = expect if isinstance(expect, list) else [expect]
    if tval is None:
        tval = [0, e] if any(a in (ILLEGAL, VIRTUAL) for a in alts) else None
    if pre:
        lab = t.label(f"in_{mode}")
        t.allow(1)
        if mode != t.cur:
            t.enter(mode)
        for ln in pre:
            t.emit(ln)
        t.emit(f"{lab}:", 0)
        t.emit(word(e, note))
        for ln in more:
            t.emit(ln)
        if mode != t.cur:
            t.leave()
        t.outcome(expect, lab, f"{note} ({desc}) in {mode}-mode", tval, origin=mode)
        return lab
    return t.window(mode, [word(e, note), *more], expect, f"{note} ({desc})", tval)


def iw_tsbi(t: TestFile, mode: str, e: int, note: str, expect: Expect, desc: str) -> str:
    alts = expect if isinstance(expect, list) else [expect]
    tval = [0, e] if any(a in (ILLEGAL, VIRTUAL) for a in alts) else None
    return hlib.window_tsbi(t, mode, [word(e, note)], expect, f"{note} ({desc})", tval)


def hst(t: TestFile, field: str, on: bool) -> None:
    hs_bits(t, "hstatus", HSTATUS[field], on, f"hstatus.{field} = {int(on)}")


def mst(t: TestFile, bits: int, on: bool, name: str) -> None:
    m_bits(t, "mstatus", bits, on, f"M-mode: mstatus.{name} = {int(on)}")


def la(t: TestFile, reg: str, sym: str) -> None:
    t.emit(f"LA({reg}, {sym})", 2)


def set_field(t: TestFile, name: str, mask: int, val: int, note: str) -> None:
    """HS-mode: write field `mask` of CSR `name` (by number) with val (already shifted)."""
    num = hex(csr_num(name))
    t.comment(note)
    t.li("x7", mask)
    t.emit(f"csrc {num}, x7  // {name}")
    if val:
        t.li("x7", val)
        t.emit(f"csrs {num}, x7  // {name}")


def vs_wake(t: TestFile, on: bool) -> None:
    """A VS-level software interrupt that VS-mode sees pending and locally enabled but globally disabled
    (hideleg[2]=1, hvip.VSSIP=1, hie.VSSIE=1, vsstatus.SIE=0): it wakes a WFI in VS-mode without being
    taken. Never enter VU-mode while it is on (VU-mode would take it)."""
    t.comment(f"VS-mode wake-up source {'on' if on else 'off'}")
    if on:
        hs_bits(t, "vsstatus", 2, False, "vsstatus.SIE = 0")
        for n in ("hideleg", "hie", "hvip"):
            hs_bits(t, n, 4, True, f"{n}[2] = 1")
    else:
        for n in ("hvip", "hie", "hideleg"):
            hs_bits(t, n, 4, False, f"{n}[2] = 0")


def hs_wake(t: TestFile, on: bool) -> None:
    """A supervisor software interrupt pending and enabled in sie with sstatus.SIE=0 (not taken in HS-mode);
    it wakes a WFI in HS-mode. Never enter a lower mode while it is on."""
    t.comment(f"HS-mode wake-up source {'on' if on else 'off'}")
    if on:
        hs_bits(t, "sstatus", 2, False, "sstatus.SIE = 0")
        hs_bits(t, "sie", 2, True, "sie.SSIE = 1")
        hs_bits(t, "sip", 2, True, "sip.SSIP = 1")
    else:
        hs_bits(t, "sip", 2, False, "sip.SSIP = 0")
        hs_bits(t, "sie", 2, False, "sie.SSIE = 0")


def eq(t: TestFile, a: str, b: str, lab: str, desc: str) -> None:
    t.emit(f"xor x5, {a}, {b}")
    t.emit("seqz x5, x5")
    t.check_bool("x5", lab, desc)


ISSUE_HSQ = (
    "HS-qualified (hypervisor.adoc, Virtual Instruction): an instruction is HS-qualified if it would be valid in "
    "HS-mode for some register operands, assuming mstatus.TVM=0 and TSR=0."
)


# ---------------------------------------------------------------- VTSR / SRET
def vs_sret_window(t: TestFile, expect: Expect, desc: str, spp: int = 1) -> str:
    """VS-mode SRET with vsepc = the instruction after it and vsstatus.SPP = spp, so an SRET that wrongly
    executes continues in place (in VS or VU)."""
    after = t.label("after")
    la(t, "x7", after)
    t.emit(f"csrw {hex(csr_num('vsepc'))}, x7  // vsepc = after the sret")
    hs_bits(t, "vsstatus", 0x100, bool(spp), f"vsstatus.SPP = {spp}")
    lab = t.label("in_VS")
    t.allow(1)
    t.enter("VS")
    t.emit(f"{lab}:", 0)
    t.emit(word(SRET, "sret"))
    t.emit(f"{after}:", 0)
    t.leave()
    t.outcome(expect, lab, f"sret ({desc}) in VS-mode", [0, SRET] if expect != "ok" else None, origin="VS")
    return lab


def gen_vtsr() -> list[TestFile]:
    tests = []
    t = new("hstatus_vtsr_op")
    t.describe(
        source=HYP,
        rule_text="When VTSR=1, an attempt in VS-mode to execute SRET raises a virtual-instruction exception.",
        context="VTSR is the VS-mode analogue of mstatus.TSR. It applies in VS-mode only: HS-mode SRET is "
        "governed by mstatus.TSR, and VU-mode SRET always raises virtual-instruction "
        "(H_virtinst_vu_sret_sfence). SRET is entered with vsepc pointing just past it, so one that wrongly "
        "executes continues in place.",
        issues=ISSUE_HSQ,
        plan="1. VTSR=1: SRET in VS-mode raises virtual-instruction (xepc the SRET, xtval 0 or its bits, from "
        "VS), with vsstatus.SPP=1 and with SPP=0.\n"
        "2. VTSR=0: SRET in VS-mode executes without a trap.\n"
        "3. VTSR=1 does not affect HS-mode: SRET in HS-mode with SPV=0, SPP=1 returns to HS-mode without a "
        "trap.\n"
        "4. VTSR=1 back to 0: SRET in VS-mode executes again (the bit is not sticky).",
    )
    trap = "ok" if MUT == "vtsr_ignored" else (ILLEGAL if MUT == "vtsr_illegal" else VIRTUAL)
    hst(t, "VTSR", True)
    vs_sret_window(t, trap, "hstatus.VTSR=1, vsstatus.SPP=1", 1)
    vs_sret_window(t, trap, "hstatus.VTSR=1, vsstatus.SPP=0", 0)
    # HS-mode SRET with VTSR=1
    after = t.label("hsafter")
    la(t, "x7", after)
    t.emit(f"csrw {hex(csr_num('sepc'))}, x7  // sepc = after the sret")
    hs_bits(t, "sstatus", 0x100, True, "sstatus.SPP = 1 (return to HS)")
    hst(t, "SPV", False)
    lab = t.label("in_S")
    t.allow(1)
    t.emit(f"{lab}:", 0)
    t.emit(word(SRET, "sret"))
    t.emit(f"{after}:", 0)
    t.outcome(VIRTUAL if MUT == "vtsr_traps_hs" else "ok", lab, "sret in HS-mode (hstatus.VTSR=1)",
              [0, SRET], origin="S")
    hst(t, "VTSR", False)
    vs_sret_window(t, "ok", "hstatus.VTSR=0 again", 1)
    tests.append(t)

    t = new("H_virtinst_vs_sret_vtsr1")
    t.describe(
        source=HYP,
        rule_text="in VS-mode, attempts to execute SRET when hstatus.VTSR=1",
        context="One of the cases that raise a virtual-instruction exception. The trap goes to HS-mode "
        "(hedeleg cannot delegate cause 22). hstatus_vtsr_op covers the enable sweep; this test checks the "
        "trap's fields and that the SRET had no effect.",
        issues=ISSUE_HSQ,
        plan="1. VTSR=1, every combination of vsstatus.SPP, SPIE and SIE: SRET in VS-mode raises "
        "virtual-instruction with xepc the SRET, xtval 0 or 0x10200073, and SPV=1, SPP=1 recorded.\n"
        "2. The trapping SRET changes nothing: vsstatus.SPP, SPIE and SIE and vsepc keep their values.",
    )
    hst(t, "VTSR", True)
    vsepc = csr_num("vsepc")
    for spp in (0, 1):
        for spie in (0, 1):
            for sie in (0, 1):
                bits = (spp << 8) | (spie << 5) | (sie << 1)
                set_field(t, "vsstatus", 0x122, bits, f"vsstatus SPP={spp} SPIE={spie} SIE={sie}")
                desc = f"VTSR=1, vsstatus.SPP={spp} SPIE={spie} SIE={sie}"
                after = t.label("after")
                la(t, "x7", after)
                t.emit(f"csrw {hex(vsepc)}, x7")
                lab = t.label("in_VS")
                t.allow(1)
                t.enter("VS")
                t.emit(f"{lab}:", 0)
                t.emit(word(SRET, "sret"))
                t.emit(f"{after}:", 0)
                t.leave()
                t.outcome(ILLEGAL if MUT == "vtsr_illegal" else VIRTUAL, lab, f"sret ({desc}) in VS-mode",
                          [0, SRET], origin="VS")
                hs_read(t, "x7", "vsstatus")
                t.check_masked("x7", 0x122, bits, lab, f"{desc}: the trapping sret leaves vsstatus.SPP/SPIE/SIE")
                hs_read(t, "x7", "vsepc")
                la(t, "x8", after)
                eq(t, "x7", "x8", lab, f"{desc}: the trapping sret leaves vsepc")
    set_field(t, "vsstatus", 0x122, 0, "vsstatus SPP=SPIE=SIE=0")
    hst(t, "VTSR", False)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- WFI
def wfi(t: TestFile, mode: str, expect: Expect, desc: str) -> str:
    return iw(t, mode, WFI, "wfi", expect, desc)


def gen_wfi() -> list[TestFile]:
    tests = []
    vtw_trap = ILLEGAL if MUT == "vtw_illegal" else VIRTUAL
    tw_trap = VIRTUAL if MUT == "tw_virtual" else ILLEGAL

    t = new("hstatus_vtw_op")
    t.describe(
        source=HYP,
        rule_text="When VTW=1 (and assuming mstatus.TW=0), an attempt in VS-mode to execute WFI raises a "
        "virtual-instruction exception if the WFI does not complete within an implementation-specific, bounded "
        "time limit.",
        context="A WFI may complete (no trap) or, with VTW=1, raise virtual-instruction after a bounded time, so "
        "both are legal with VTW=1; illegal-instruction is not. With VTW=0 and TW=0, VS-mode WFI may wait "
        "for an interrupt, so those cases provide a wake-up source: a VS-level software interrupt delegated to "
        "VS-mode (hideleg[2]=1, hvip.VSSIP=1), enabled in vsie and globally disabled (vsstatus.SIE=0), which "
        "makes WFI complete without being taken. HS-mode uses sip.SSIP the same way.",
        plan="1. VTW=1, no interrupt pending: VS-mode WFI completes or raises virtual-instruction (xtval 0 or "
        "0x10500073, from VS).\n"
        "2. VTW=1 with the wake-up source: completes or raises virtual-instruction.\n"
        "3. VTW=0 with the wake-up source: WFI completes without a trap.\n"
        "4. VTW=1 does not affect HS-mode: with an HS wake-up source, HS-mode WFI completes without a trap.\n"
        "5. VTW back to 0: VS-mode WFI with the wake-up source completes again.",
    )
    hst(t, "VTW", True)
    wfi(t, "VS", ["ok", vtw_trap], "hstatus.VTW=1, mstatus.TW=0, nothing pending")
    vs_wake(t, True)
    wfi(t, "VS", ["ok", vtw_trap], "hstatus.VTW=1, mstatus.TW=0, wake-up pending")
    hst(t, "VTW", False)
    wfi(t, "VS", VIRTUAL if MUT == "vtw0_traps" else "ok", "hstatus.VTW=0, mstatus.TW=0, wake-up pending")
    vs_wake(t, False)
    hst(t, "VTW", True)
    hs_wake(t, True)
    wfi(t, "S", "ok", "hstatus.VTW=1 in HS-mode, HS wake-up pending")
    hs_wake(t, False)
    hst(t, "VTW", False)
    vs_wake(t, True)
    wfi(t, "VS", "ok", "hstatus.VTW=0 again, wake-up pending")
    vs_wake(t, False)
    tests.append(t)

    t = new("vtw_virtinstr")
    t.describe(
        source=HYP,
        rule_text="An implementation may have WFI always raise a virtual-instruction exception in VS-mode when "
        "VTW=1 (and mstatus.TW=0), even if there are pending globally-disabled interrupts when the instruction "
        "is executed.",
        context="This permits the trap; it does not require it. The test checks that whatever happens with a "
        "pending, globally disabled VS-level interrupt is one of the two legal outcomes, that the trap is a "
        "virtual-instruction exception with the right fields, and that the pending interrupt is not taken.",
        plan="1. VTW=1, TW=0, vsstatus.SIE=0, with each VS-level interrupt (software through hvip.VSSIP, timer "
        "through hvip.VSTIP, external through hvip.VSEIP) delegated to VS-mode, pending and enabled in vsie: "
        "VS-mode WFI completes or raises virtual-instruction (xepc the WFI, xtval 0 or its bits, from VS); the "
        "interrupt is never taken (the window permits one trap and checks its cause).",
    )
    hst(t, "VTW", True)
    hs_bits(t, "vsstatus", 2, False, "vsstatus.SIE = 0")
    for bit, name in ((4, "software"), (0x40, "timer"), (0x400, "external")):
        for n in ("hideleg", "hie", "hvip"):
            hs_bits(t, n, bit, True, f"{n}[{bit.bit_length() - 1}] = 1")
        wfi(t, "VS", ["ok", vtw_trap], f"hstatus.VTW=1, VS-level {name} interrupt pending, vsstatus.SIE=0")
        for n in ("hvip", "hie", "hideleg"):
            hs_bits(t, n, bit, False, f"{n}[{bit.bit_length() - 1}] = 0")
    hst(t, "VTW", False)
    tests.append(t)

    t = new("H_virtinst_wfi_vtw1_tw0")
    t.describe(
        source=HYP,
        rule_text="in VS-mode, attempts to execute WFI when hstatus.VTW=1 and mstatus.TW=0, unless the "
        "instruction completes within an implementation-specific, bounded time;",
        context="With mstatus.TW=1, a WFI below M-mode that does not complete raises illegal-instruction (TW "
        "affects all modes except M, mstatus_modes); the VTW rule assumes TW=0. So the trap cause is fixed by "
        "TW: 22 when TW=0 and VTW=1, 2 when TW=1. Cases without a wake-up source cannot hang: VTW=1 or TW=1 "
        "bound the wait.",
        issues=ISSUE_HSQ,
        plan="1. (VTW, TW) = (1, 0): VS-mode WFI completes or raises virtual-instruction, with and without a "
        "wake-up source.\n"
        "2. (0, 1) and (1, 1): VS-mode WFI completes or raises illegal-instruction (never virtual), with and "
        "without a wake-up source.\n"
        "3. (0, 0) with a wake-up source: WFI completes without a trap.",
    )
    for vtw, tw in ((1, 0), (0, 1), (1, 1), (0, 0)):
        hst(t, "VTW", bool(vtw))
        mst(t, MSTATUS_TW, bool(tw), "TW")
        exp: Expect = (["ok", tw_trap] if tw else (["ok", vtw_trap] if vtw else "ok"))
        if vtw or tw:
            wfi(t, "VS", exp, f"hstatus.VTW={vtw}, mstatus.TW={tw}, nothing pending")
        vs_wake(t, True)
        wfi(t, "VS", exp, f"hstatus.VTW={vtw}, mstatus.TW={tw}, wake-up pending")
        vs_wake(t, False)
    hst(t, "VTW", False)
    mst(t, MSTATUS_TW, False, "TW")
    tests.append(t)

    t = new("H_virtinst_vu_wfi_tw0")
    t.describe(
        source=HYP,
        rule_text="in VU-mode, attempts to execute WFI when mstatus.TW=0",
        context="One of the cases that raise a virtual-instruction exception. WFI may still complete within a "
        "bounded time, so no trap is also legal. In U-mode (V=0) with S-mode present, WFI raises "
        "illegal-instruction under the same proviso; with TW=1 the VU-mode cause is illegal-instruction too. "
        "hstatus.VTW applies to VS-mode only. No wake-up source is used: VU-mode would take any enabled "
        "VS-level interrupt.",
        issues=ISSUE_HSQ,
        plan="1. TW=0, VTW=0 and VTW=1: VU-mode WFI completes or raises virtual-instruction (xtval 0 or the "
        "bits, from VU), never illegal-instruction.\n"
        "2. TW=0: U-mode WFI completes or raises illegal-instruction.\n"
        "3. TW=1: VU-mode WFI completes or raises illegal-instruction.",
    )
    vu = ["ok", ILLEGAL if MUT == "vu_wfi_illegal" else VIRTUAL]
    for vtw in (0, 1):
        hst(t, "VTW", bool(vtw))
        wfi(t, "VU", vu, f"mstatus.TW=0, hstatus.VTW={vtw}")
    hst(t, "VTW", False)
    wfi(t, "U", ["ok", ILLEGAL], "mstatus.TW=0, V=0")
    mst(t, MSTATUS_TW, True, "TW")
    wfi(t, "VU", ["ok", VIRTUAL if MUT == "tw_ignored_vu" else ILLEGAL], "mstatus.TW=1")
    mst(t, MSTATUS_TW, False, "TW")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- VU sret/sfence
def gen_vu_sret() -> list[TestFile]:
    t = new("H_virtinst_vu_sret_sfence", scratch=False)
    t.describe(
        source=HYP,
        rule_text="or to execute a supervisor instruction (SRET or SFENCE);",
        context="Continues \"in VU-mode, attempts to execute WFI when mstatus.TW=0\": in VU-mode, SRET and the "
        "SFENCE instructions raise virtual-instruction, since they are HS-qualified. Svinval adds SINVAL.VMA, "
        "SFENCE.W.INVAL and SFENCE.INVAL.IR, which raise virtual-instruction in VU-mode too "
        "(Svinval_virtual_instruction_vu_vs, Svinval_sfence_w_inval_inval_vu_mode). In U-mode (V=0) they "
        "raise illegal-instruction. The SRET is entered with vsepc just past it and vsstatus.SPP=0.",
        issues=ISSUE_HSQ,
        plan="1. VU-mode SRET raises virtual-instruction with hstatus.VTSR=0 and 1.\n"
        "2. VU-mode SFENCE.VMA with rs1/rs2 = x0/x0, x6/x0, x0/x8 and x6/x8 raises virtual-instruction, with "
        "hstatus.VTVM=0 and 1.\n"
        "3. With Svinval: SINVAL.VMA, SFENCE.W.INVAL and SFENCE.INVAL.IR raise virtual-instruction in "
        "VU-mode.\n"
        "4. Contrast: the same instructions in U-mode raise illegal-instruction.\n"
        "All traps: xepc the instruction, xtval 0 or its bits, from VU (or U).",
    )
    trap = ILLEGAL if MUT == "vu_sret_illegal" else VIRTUAL
    hs_bits(t, "vsstatus", 0x100, False, "vsstatus.SPP = 0")
    for vtsr in (0, 1):
        hst(t, "VTSR", bool(vtsr))
        after = t.label("after")
        la(t, "x7", after)
        t.emit(f"csrw {hex(csr_num('vsepc'))}, x7")
        iw(t, "VU", SRET, "sret", trap, f"hstatus.VTSR={vtsr}", more=[f"{after}:"])
    hst(t, "VTSR", False)
    t.li("x6", 0x1000)
    t.li("x8", 1)
    for vtvm in (0, 1):
        hst(t, "VTVM", bool(vtvm))
        for rs1, rs2 in ((0, 0), (6, 0), (0, 8), (6, 8)):
            iw(t, "VU", sfence_vma(rs1, rs2), f"sfence.vma x{rs1}, x{rs2}", trap, f"hstatus.VTVM={vtvm}")
    hst(t, "VTVM", False)
    with t.only_if(SVINVAL):
        for e, note in ((sinval_vma(6, 8), "sinval.vma x6, x8"), (0x18000073, "sfence.w.inval"),
                        (0x18100073, "sfence.inval.ir")):
            iw(t, "VU", e, note, trap, "Svinval")
    for e, note in ((SRET, "sret"), (sfence_vma(6, 8), "sfence.vma x6, x8")):
        iw(t, "U", e, note, ILLEGAL, "V=0")
    with t.only_if(SVINVAL):
        for e, note in ((sinval_vma(6, 8), "sinval.vma x6, x8"), (0x18000073, "sfence.w.inval"),
                        (0x18100073, "sfence.inval.ir")):
            iw(t, "U", e, note, ILLEGAL, "V=0, Svinval")
    return [t]


# ---------------------------------------------------------------- VTVM / TVM
SATP = csr_num("satp")


def satp_forms(t: TestFile, mode: str, expect: str, desc: str, forms: list | None = None) -> None:
    """CSR instruction forms on satp in `mode`. For forms that may succeed, the source is 0 (csrrw/csrrs) or
    all ones (csrrc), so vsatp stays Bare and zero; immediate write forms are used only when a trap is
    expected."""
    for form in forms or FORMS:
        if expect == "ok" and form[1] in (5, 7):
            continue
        t.emit("li x6, -1" if form[1] == 3 else "li x6, 0")
        csr_window(t, mode, "satp", form, expect, desc)


def gen_vtvm() -> list[TestFile]:
    tests = []
    vt = "ok" if MUT == "vtvm_ignored" else ("illegal" if MUT == "vtvm_illegal" else "virtual")
    vtc = {"ok": "ok", "illegal": ILLEGAL, "virtual": VIRTUAL}[vt]

    t = new("hstatus_vtvm_op")
    t.describe(
        source=HYP,
        rule_text="When VTVM=1, an attempt in VS-mode to execute SFENCE.VMA or SINVAL.VMA or to access CSR satp "
        "raises a virtual-instruction exception.",
        context="VTVM is the VS-mode analogue of mstatus.TVM. It does not affect HS-mode, SFENCE.W.INVAL or "
        "SFENCE.INVAL.IR (Svinval: always permitted in VS-mode), or HFENCE.VVMA (hfence-vvma_tvm). satp writes "
        "that may succeed keep vsatp Bare and zero.",
        issues=ISSUE_HSQ,
        plan="1. VTVM=1: in VS-mode, a read and a write of satp, SFENCE.VMA (x0/x0 and x6/x8) and, with "
        "Svinval, SINVAL.VMA raise virtual-instruction (xtval 0 or the bits, from VS).\n"
        "2. VTVM=0: the same succeed.\n"
        "3. VTVM=1 does not affect HS-mode satp and SFENCE.VMA, or VS-mode SFENCE.W.INVAL and "
        "SFENCE.INVAL.IR.\n"
        "4. VTVM=1 again after 0: traps again.",
    )
    t.li("x8", 1)
    for vtvm, exp in ((1, vt), (0, "ok"), (1, vt)):
        hst(t, "VTVM", bool(vtvm))
        expc = {"ok": "ok", "illegal": ILLEGAL, "virtual": VIRTUAL}[exp]
        satp_forms(t, "VS", exp, f"hstatus.VTVM={vtvm}", [FORMS[0], FORMS[1]])
        t.li("x6", 0x1000)
        iw(t, "VS", sfence_vma(), "sfence.vma x0, x0", expc, f"hstatus.VTVM={vtvm}")
        iw(t, "VS", sfence_vma(6, 8), "sfence.vma x6, x8", expc, f"hstatus.VTVM={vtvm}")
        with t.only_if(SVINVAL):
            iw(t, "VS", sinval_vma(6, 8), "sinval.vma x6, x8", expc, f"hstatus.VTVM={vtvm}")
    hst(t, "VTVM", True)
    satp_forms(t, "S", "virtual" if MUT == "vtvm_traps_hs" else "ok", "hstatus.VTVM=1 in HS-mode",
               [FORMS[0], FORMS[1]])
    t.li("x6", 0x1000)
    iw(t, "S", sfence_vma(6, 8), "sfence.vma x6, x8", "ok", "hstatus.VTVM=1 in HS-mode")
    with t.only_if(SVINVAL):
        for e, note in ((0x18000073, "sfence.w.inval"), (0x18100073, "sfence.inval.ir")):
            iw(t, "VS", e, note, VIRTUAL if MUT == "vtvm_traps_wfence" else "ok", "hstatus.VTVM=1")
    hst(t, "VTVM", False)
    tests.append(t)

    t = new("H_virtinst_vs_sfence_sinval_satp_vtvm1")
    t.describe(
        source=HYP,
        rule_text="in VS-mode, attempts to execute an SFENCE.VMA or SINVAL.VMA instruction or to access satp, "
        "when hstatus.VTVM=1.",
        context="One of the cases that raise a virtual-instruction exception. hstatus_vtvm_op covers the enable "
        "and its non-effects; this test covers every operand form, and the independence from mstatus.TVM "
        "(which affects HS-mode only).",
        issues=ISSUE_HSQ,
        plan="1. VTVM=1, mstatus.TVM=0: all eight CSR instruction forms on satp, SFENCE.VMA with rs1/rs2 = "
        "x0/x0, x6/x0, x0/x8, x6/x8, and (Svinval) SINVAL.VMA with the same operands, each raise "
        "virtual-instruction in VS-mode with xepc the instruction and xtval 0 or its bits.\n"
        "2. VTVM=1, mstatus.TVM=1: the same cause (virtual-instruction) for a satp read, SFENCE.VMA and "
        "SINVAL.VMA.",
    )
    hst(t, "VTVM", True)
    satp_forms(t, "VS", vt, "hstatus.VTVM=1")
    t.li("x6", 0x2000)
    t.li("x8", 3)
    for rs1, rs2 in ((0, 0), (6, 0), (0, 8), (6, 8)):
        iw(t, "VS", sfence_vma(rs1, rs2), f"sfence.vma x{rs1}, x{rs2}", vtc, "hstatus.VTVM=1")
        with t.only_if(SVINVAL):
            iw(t, "VS", sinval_vma(rs1, rs2), f"sinval.vma x{rs1}, x{rs2}", vtc, "hstatus.VTVM=1")
    mst(t, MSTATUS_TVM, True, "TVM")
    satp_forms(t, "VS", vt, "hstatus.VTVM=1, mstatus.TVM=1", [FORMS[0]])
    iw(t, "VS", sfence_vma(6, 8), "sfence.vma x6, x8", vtc, "hstatus.VTVM=1, mstatus.TVM=1")
    with t.only_if(SVINVAL):
        iw(t, "VS", sinval_vma(6, 8), "sinval.vma x6, x8", vtc, "hstatus.VTVM=1, mstatus.TVM=1")
    mst(t, MSTATUS_TVM, False, "TVM")
    hst(t, "VTVM", False)
    tests.append(t)
    return tests


def gen_mstatus_modes() -> list[TestFile]:
    tests = []
    t = new("mstatus_modes")
    t.describe(
        source=HYP,
        rule_text="The TSR and TVM fields of mstatus affect execution only in HS-mode, not in VS-mode. The TW "
        "field affects execution in all modes except M-mode.",
        context="TSR is tested in mstatus_modes_Sm: with TSR=1 the HS-mode trap handler's own SRET would trap, "
        "so that part runs with traps taken in M-mode. A WFI with TW=1 may still complete within a bounded "
        "time, so no trap is also legal.",
        plan="1. mstatus.TVM=1, hstatus.VTVM=0: in VS-mode, satp read and write (of zero), SFENCE.VMA and "
        "(Svinval) SINVAL.VMA succeed; in HS-mode, a satp read and SFENCE.VMA raise illegal-instruction.\n"
        "2. mstatus.TW=1: WFI in HS, U, VS and VU-mode completes or raises illegal-instruction.",
    )
    mst(t, MSTATUS_TVM, True, "TVM")
    vs_exp = "illegal" if MUT == "tvm_affects_vs" else "ok"
    satp_forms(t, "VS", vs_exp, "mstatus.TVM=1, hstatus.VTVM=0", [FORMS[0], FORMS[1], FORMS[4]])
    t.li("x6", 0x1000)
    t.li("x8", 1)
    iw(t, "VS", sfence_vma(6, 8), "sfence.vma x6, x8", hlib.CAUSE[vs_exp], "mstatus.TVM=1, hstatus.VTVM=0")
    with t.only_if(SVINVAL):
        iw(t, "VS", sinval_vma(6, 8), "sinval.vma x6, x8", hlib.CAUSE[vs_exp], "mstatus.TVM=1, hstatus.VTVM=0")
    csr_window(t, "S", "satp", FORMS[0], "illegal", "mstatus.TVM=1 in HS-mode")
    iw(t, "S", sfence_vma(6, 8), "sfence.vma x6, x8", ILLEGAL, "mstatus.TVM=1 in HS-mode")
    mst(t, MSTATUS_TVM, False, "TVM")
    mst(t, MSTATUS_TW, True, "TW")
    for mode in ("S", "U", "VS", "VU"):
        wfi(t, mode, ["ok", ILLEGAL], "mstatus.TW=1")
    mst(t, MSTATUS_TW, False, "TW")
    tests.append(t)

    t = new_sm("mstatus_modes")
    t.describe(
        source=HYP,
        rule_text="The TSR and TVM fields of mstatus affect execution only in HS-mode, not in VS-mode. The TW "
        "field affects execution in all modes except M-mode.",
        context="The TSR part (mstatus_modes covers TVM and TW). The test boots to M-mode, where traps are not "
        "delegated, so the HS-mode SRET that TSR=1 makes trap is handled in M-mode. VS-mode is entered with a "
        "T-SBI GOTO (no SRET), and VS-mode SRET returns to vsepc with vsstatus.SPP=1.",
        plan="1. mstatus.TSR=1, hstatus.VTSR=0: SRET in VS-mode executes without a trap.\n"
        "2. mstatus.TSR=1: SRET in HS-mode raises illegal-instruction.",
    )
    t.emit("li x7, 0x100")
    t.emit(f"csrs {hex(csr_num('vsstatus'))}, x7  // vsstatus.SPP = 1")
    t.li("x7", HSTATUS["VTSR"])
    t.emit(f"csrc {hex(csr_num('hstatus'))}, x7  // hstatus.VTSR = 0")
    t.li("x7", MSTATUS_TSR)
    t.emit("csrs mstatus, x7  // mstatus.TSR = 1")
    after = t.label("after")
    la(t, "x7", after)
    t.emit(f"csrw {hex(csr_num('vsepc'))}, x7")
    lab = t.label("in_VS")
    t.allow(1)
    hlib.enter_tsbi(t, "VS")
    t.emit(f"{lab}:", 0)
    t.emit(word(SRET, "sret"))
    t.emit(f"{after}:", 0)
    t.leave()
    t.outcome(ILLEGAL if MUT == "tsr_affects_vs" else "ok", lab, "sret in VS-mode (mstatus.TSR=1, VTSR=0)",
              [0, SRET], origin="VS")
    # HS-mode SRET with TSR=1: enter S with mret, sret there traps to M
    after = t.label("hsafter")
    la(t, "x7", after)
    t.emit("csrw sepc, x7")
    lab = t.label("in_S")
    t.allow(1)
    t.enter("S")
    t.emit(f"{lab}:", 0)
    t.emit(word(SRET, "sret"))
    t.emit(f"{after}:", 0)
    t.leave()
    t.outcome(ILLEGAL, lab, "sret in HS-mode (mstatus.TSR=1)", [0, SRET], origin="S")
    t.li("x7", MSTATUS_TSR)
    t.emit("csrc mstatus, x7  // mstatus.TSR = 0")
    tests.append(t)
    return tests


def gen_tvm_hfence() -> list[TestFile]:
    tests = []
    t = new("mstatus_tvm_hs")
    t.describe(
        source=HYP,
        rule_text="Setting TVM=1 prevents HS-mode from accessing hgatp or executing HFENCE.GVMA or HINVAL.GVMA, "
        "but has no effect on accesses to vsatp or instructions HFENCE.VVMA or HINVAL.VVMA.",
        context="Prevented HS-mode accesses raise illegal-instruction (Svinval_illegal_instruction_tvm for "
        "HINVAL.GVMA). hgatp and vsatp writes carry zero (Bare), the value they already hold.",
        plan="1. TVM=1, HS-mode: all eight forms on hgatp, HFENCE.GVMA (x0/x0, x6/x8) and (Svinval) HINVAL.GVMA "
        "raise illegal-instruction.\n"
        "2. TVM=1, HS-mode: read and write of vsatp, HFENCE.VVMA (x0/x0, x6/x8) and HINVAL.VVMA succeed.\n"
        "3. TVM=0: hgatp read and write and HFENCE.GVMA succeed in HS-mode.",
    )
    mst(t, MSTATUS_TVM, True, "TVM")
    hexp = "ok" if MUT == "tvm_hgatp_ok" else "illegal"
    for form in FORMS:
        t.emit("li x6, -1" if form[1] == 3 else "li x6, 0")
        if hexp == "ok" and form[1] in (5, 7):
            continue
        csr_window(t, "S", "hgatp", form, hexp, "mstatus.TVM=1 in HS-mode")
    t.li("x6", 0x400)
    t.li("x8", 1)
    for rs1, rs2 in ((0, 0), (6, 8)):
        iw(t, "S", hfence_gvma(rs1, rs2), f"hfence.gvma x{rs1}, x{rs2}", hlib.CAUSE[hexp], "mstatus.TVM=1")
        with t.only_if(SVINVAL):
            iw(t, "S", hinval_gvma(rs1, rs2), f"hinval.gvma x{rs1}, x{rs2}", hlib.CAUSE[hexp], "mstatus.TVM=1")
    for form in (FORMS[0], FORMS[1], FORMS[2]):
        t.emit("li x6, 0")
        csr_window(t, "S", "vsatp", form, "ok", "mstatus.TVM=1 in HS-mode")
    vexp = ILLEGAL if MUT == "tvm_traps_vvma" else "ok"
    for rs1, rs2 in ((0, 0), (6, 8)):
        iw(t, "S", hfence_vvma(rs1, rs2), f"hfence.vvma x{rs1}, x{rs2}", vexp, "mstatus.TVM=1")
        with t.only_if(SVINVAL):
            iw(t, "S", hinval_vvma(rs1, rs2), f"hinval.vvma x{rs1}, x{rs2}", vexp, "mstatus.TVM=1")
    mst(t, MSTATUS_TVM, False, "TVM")
    csr_window(t, "S", "hgatp", FORMS[0], "ok", "mstatus.TVM=0")
    t.emit("li x6, 0")
    csr_window(t, "S", "hgatp", FORMS[1], "ok", "mstatus.TVM=0")
    iw(t, "S", hfence_gvma(), "hfence.gvma x0, x0", "ok", "mstatus.TVM=0")
    tests.append(t)

    t = new("hgatp_tvm_illegal")
    t.describe(
        source=HYP,
        rule_text="When mstatus.TVM=1, attempts to read or write hgatp while executing in HS-mode will raise an "
        "illegal-instruction exception.",
        context="TVM concerns HS-mode only: M-mode access is unaffected, and VS/VU-mode access raises "
        "virtual-instruction regardless of TVM (the virtual-instruction rule assumes TVM=0). hgatp holds Bare "
        "(zero); writes that may succeed carry zero.",
        issues=ISSUE_HSQ,
        plan="1. TVM=1: all eight CSR instruction forms on hgatp in HS-mode raise illegal-instruction (xtval 0 or "
        "the bits).\n"
        "2. TVM=1: M-mode reads hgatp (T-SBI) without a trap and gets Bare.\n"
        "3. TVM=1: VS-mode and VU-mode reads of hgatp raise virtual-instruction.\n"
        "4. TVM=0: the read forms and a write of zero succeed in HS-mode.",
    )
    mst(t, MSTATUS_TVM, True, "TVM")
    for form in FORMS:
        t.emit("li x6, -1" if form[1] == 3 else "li x6, 0")
        csr_window(t, "S", "hgatp", form, "ok" if MUT == "tvm_hgatp_ok" and form[1] not in (5, 7) else "illegal",
                   "mstatus.TVM=1 in HS-mode")
    lab = t.label("m")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "HGATP")
    t.check("a0", 0, lab, "M-mode read of hgatp with mstatus.TVM=1 returns Bare")
    for mode in ("VS", "VU"):
        csr_window(t, mode, "hgatp", FORMS[0], "illegal" if MUT == "tvm_vs_hgatp_illegal" else "virtual",
                   "mstatus.TVM=1")
    mst(t, MSTATUS_TVM, False, "TVM")
    for form in (FORMS[0], FORMS[6], FORMS[1]):
        t.emit("li x6, 0")
        csr_window(t, "S", "hgatp", form, "ok", "mstatus.TVM=0")
    tests.append(t)

    t = new("hfence-vvma_tvm")
    t.describe(
        source=HYP,
        rule_text="Neither mstatus.TVM nor hstatus.VTVM causes HFENCE.VVMA to trap.",
        context="Svinval's HINVAL.VVMA has the same permissions as HFENCE.VVMA. Executed in HS-mode.",
        plan="1. For (mstatus.TVM, hstatus.VTVM) = (0,0), (1,0), (0,1), (1,1): HFENCE.VVMA with rs1/rs2 = x0/x0, "
        "x6/x0, x0/x8, x6/x8 and (Svinval) HINVAL.VVMA x6/x8 execute in HS-mode without a trap.",
    )
    t.li("x6", 0x3000)
    t.li("x8", 2)
    for tvm, vtvm in ((0, 0), (1, 0), (0, 1), (1, 1)):
        mst(t, MSTATUS_TVM, bool(tvm), "TVM")
        hst(t, "VTVM", bool(vtvm))
        desc = f"mstatus.TVM={tvm}, hstatus.VTVM={vtvm}"
        exp = ILLEGAL if (MUT == "tvm_traps_vvma" and tvm) else "ok"
        for rs1, rs2 in ((0, 0), (6, 0), (0, 8), (6, 8)):
            iw(t, "S", hfence_vvma(rs1, rs2), f"hfence.vvma x{rs1}, x{rs2}", exp, desc)
        with t.only_if(SVINVAL):
            iw(t, "S", hinval_vvma(6, 8), "hinval.vvma x6, x8", exp, desc)
    mst(t, MSTATUS_TVM, False, "TVM")
    hst(t, "VTVM", False)
    tests.append(t)

    t = new("hfence-vvma_hfence-gvma_exceptions")
    t.describe(
        source=HYP,
        rule_text="Attempts to execute HFENCE.VVMA or HFENCE.GVMA when V=1 cause a virtual-instruction "
        "exception, while attempts to do the same in U-mode cause an illegal-instruction exception. Attempting "
        "to execute HFENCE.GVMA in HS-mode when mstatus.TVM=1 also causes an illegal-instruction exception.",
        context="hstatus.HU=1 enables only the hypervisor loads and stores in U-mode, not the fences. With "
        "mstatus.TVM=1, HFENCE.GVMA in VS-mode is still HS-qualified (TVM is assumed 0), so it raises "
        "virtual-instruction.",
        issues=ISSUE_HSQ,
        plan="1. VS-mode and VU-mode: HFENCE.VVMA and HFENCE.GVMA with x0/x0 and x6/x8 raise "
        "virtual-instruction.\n"
        "2. U-mode with hstatus.HU=0 and HU=1: both raise illegal-instruction.\n"
        "3. mstatus.TVM=1: HFENCE.GVMA raises illegal-instruction in HS-mode and virtual-instruction in VS-mode; "
        "HFENCE.VVMA succeeds in HS-mode.\n"
        "All traps: xepc the fence, xtval 0 or its bits, origin the mode.",
    )
    vtrap = ILLEGAL if MUT == "hfence_vs_illegal" else VIRTUAL
    t.li("x6", 0x400)
    t.li("x8", 1)
    for mode in ("VS", "VU"):
        for f, nm in ((hfence_vvma, "hfence.vvma"), (hfence_gvma, "hfence.gvma")):
            for rs1, rs2 in ((0, 0), (6, 8)):
                iw(t, mode, f(rs1, rs2), f"{nm} x{rs1}, x{rs2}", vtrap, "V=1")
    for hu in (0, 1):
        hst(t, "HU", bool(hu))
        for f, nm in ((hfence_vvma, "hfence.vvma"), (hfence_gvma, "hfence.gvma")):
            exp = "ok" if (MUT == "hfence_u_hu" and hu) else ILLEGAL
            iw(t, "U", f(6, 8), f"{nm} x6, x8", exp, f"U-mode, hstatus.HU={hu}")
    hst(t, "HU", False)
    mst(t, MSTATUS_TVM, True, "TVM")
    iw(t, "S", hfence_gvma(6, 8), "hfence.gvma x6, x8", ILLEGAL, "HS-mode, mstatus.TVM=1")
    iw(t, "VS", hfence_gvma(6, 8), "hfence.gvma x6, x8", vtrap, "VS-mode, mstatus.TVM=1")
    iw(t, "S", hfence_vvma(6, 8), "hfence.vvma x6, x8", "ok", "HS-mode, mstatus.TVM=1")
    mst(t, MSTATUS_TVM, False, "TVM")
    tests.append(t)

    t = new("hfence-vvma_mode")
    t.describe(
        source=HYP,
        rule_text="HFENCE.VVMA is valid only in M-mode or HS-mode. Its effect is much the same as temporarily "
        "entering VS-mode and executing SFENCE.VMA.",
        context="Only validity is tested here; the ordering it provides is a memory-management property. The "
        "M-mode part is hfence-vvma_mode_Sm.",
        plan="1. HS-mode: HFENCE.VVMA with x0/x0, x6/x0, x0/x8 and x6/x8 executes without a trap.\n"
        "2. U-mode raises illegal-instruction; VS-mode and VU-mode raise virtual-instruction.",
    )
    t.li("x6", 0x5000)
    t.li("x8", 7)
    for rs1, rs2 in ((0, 0), (6, 0), (0, 8), (6, 8)):
        iw(t, "S", hfence_vvma(rs1, rs2), f"hfence.vvma x{rs1}, x{rs2}", "ok", "HS-mode")
    iw(t, "U", hfence_vvma(6, 8), "hfence.vvma x6, x8", ILLEGAL, "U-mode")
    for mode in ("VS", "VU"):
        iw(t, mode, hfence_vvma(6, 8), "hfence.vvma x6, x8", vtrap, "V=1")
    tests.append(t)

    t = new_sm("hfence-vvma_mode")
    t.describe(
        source=HYP,
        rule_text="HFENCE.VVMA is valid only in M-mode or HS-mode.",
        context="The M-mode part of hfence-vvma_mode, including with mstatus.TVM=1 and MPRV=0.",
        plan="1. M-mode: HFENCE.VVMA with x0/x0 and x6/x8 executes without a trap, with mstatus.TVM=0 and 1.",
    )
    t.li("x6", 0x5000)
    t.li("x8", 7)
    for tvm in (0, 1):
        t.li("x7", MSTATUS_TVM)
        t.emit(f"{'csrs' if tvm else 'csrc'} mstatus, x7  // mstatus.TVM = {tvm}")
        for rs1, rs2 in ((0, 0), (6, 8)):
            iw(t, "M", hfence_vvma(rs1, rs2), f"hfence.vvma x{rs1}, x{rs2}", "ok", f"M-mode, mstatus.TVM={tvm}")
    t.li("x7", MSTATUS_TVM)
    t.emit("csrc mstatus, x7")
    tests.append(t)

    t = new("hfence-gvma_op")
    t.describe(
        source=HYP,
        rule_text="hfence.gvma is valid only in HS-mode when mstatus[tvm]=0, or in M-mode (irrespective of "
        "mstatus[tvm]).",
        context="Only validity is tested; the ordering guarantee is a G-stage translation property. The M-mode "
        "part is hfence-gvma_op_Sm.",
        plan="1. HS-mode, TVM=0: HFENCE.GVMA with x0/x0, x6/x0, x0/x8, x6/x8 executes without a trap.\n"
        "2. HS-mode, TVM=1: raises illegal-instruction.\n"
        "3. U-mode raises illegal-instruction; VS and VU raise virtual-instruction (with TVM=0 and 1).",
    )
    t.li("x6", 0x100)
    t.li("x8", 3)
    for rs1, rs2 in ((0, 0), (6, 0), (0, 8), (6, 8)):
        iw(t, "S", hfence_gvma(rs1, rs2), f"hfence.gvma x{rs1}, x{rs2}", "ok", "HS-mode, mstatus.TVM=0")
    iw(t, "U", hfence_gvma(6, 8), "hfence.gvma x6, x8", ILLEGAL, "U-mode")
    for tvm in (0, 1):
        mst(t, MSTATUS_TVM, bool(tvm), "TVM")
        if tvm:
            iw(t, "S", hfence_gvma(6, 8), "hfence.gvma x6, x8", "ok" if MUT == "tvm_hgatp_ok" else ILLEGAL,
               "HS-mode, mstatus.TVM=1")
        for mode in ("VS", "VU"):
            iw(t, mode, hfence_gvma(6, 8), "hfence.gvma x6, x8", vtrap, f"mstatus.TVM={tvm}")
    mst(t, MSTATUS_TVM, False, "TVM")
    tests.append(t)

    t = new_sm("hfence-gvma_op")
    t.describe(
        source=HYP,
        rule_text="hfence.gvma is valid only in HS-mode when mstatus[tvm]=0, or in M-mode (irrespective of "
        "mstatus[tvm]).",
        context="The M-mode part of hfence-gvma_op.",
        plan="1. M-mode: HFENCE.GVMA with x0/x0 and x6/x8 executes without a trap with mstatus.TVM=0 and 1.",
    )
    t.li("x6", 0x100)
    t.li("x8", 3)
    for tvm in (0, 1):
        t.li("x7", MSTATUS_TVM)
        t.emit(f"{'csrs' if tvm else 'csrc'} mstatus, x7  // mstatus.TVM = {tvm}")
        for rs1, rs2 in ((0, 0), (6, 8)):
            iw(t, "M", hfence_gvma(rs1, rs2), f"hfence.gvma x{rs1}, x{rs2}", "ok", f"M-mode, mstatus.TVM={tvm}")
    t.li("x7", MSTATUS_TVM)
    t.emit("csrc mstatus, x7")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- HLV / HSV validity
LOADS = ["hlv.b", "hlv.bu", "hlv.h", "hlv.hu", "hlv.w", "hlvx.hu", "hlvx.wu", "hlv.wu", "hlv.d"]
STORES = ["hsv.b", "hsv.h", "hsv.w", "hsv.d"]
RV64ONLY = {"hlv.wu", "hlv.d", "hsv.d"}
SCR_VAL = 0x5A5A5A5A


def hls_line(name: str) -> tuple[str, int]:
    """x6 = address (scratch, or code for HLVX), x7 = load result, x8 = store data."""
    if name in STORES:
        return hlsv(name, "x0", "x6", "x8")
    return hlsv(name, "x7", "x6")


def hls_addr(t: TestFile, name: str) -> None:
    if name.startswith("hlvx"):
        la(t, "x6", "rvtest_code_begin")
    else:
        la(t, "x6", "ai_scratch")


def scratch_fill(t: TestFile) -> None:
    la(t, "x6", "ai_scratch")
    t.li("x7", SCR_VAL)
    t.emit("sw x7, 0(x6)")
    t.emit("sw x7, 4(x6)")


def scratch_check(t: TestFile, lab: str, desc: str, written: int = 0) -> None:
    """The first scratch word holds SCR_VAL, or (written = store width) the store of 0x12345678 over it."""
    la(t, "x6", "ai_scratch")
    t.emit("lw x7, 0(x6)")
    exp = {0: SCR_VAL, 1: 0x5A5A5A78, 2: 0x5A5A5678, 4: 0x12345678, 8: 0x12345678}[written]
    from aigen import X
    t.check("x7", X(exp, exp | (0xFFFFFFFF << 32 if exp >> 31 else 0)), lab, desc)


def hls_window(t: TestFile, mode: str, name: str, expect: Expect, desc: str, store_check: bool = False) -> str:
    line, e = hls_line(name)
    hls_addr(t, name)
    t.li("x8", 0x12345678)
    if store_check:
        scratch_fill(t)
        hls_addr(t, name)
    alts = expect if isinstance(expect, list) else [expect]
    tval = [0, e] if any(a in (ILLEGAL, VIRTUAL) for a in alts) else None
    lab = t.window(mode, [line], expect, f"{name} ({desc})", tval)
    if store_check:
        if expect != "ok":
            w = hlib.HLSV[name][2] if (MUT == "hsv_vs_writes" and mode in ("VS", "VU")) else 0
            scratch_check(t, lab, f"a trapping {name} in {mode}-mode does not write memory", w)
    return lab


def each_hls(t: TestFile, fn) -> None:  # noqa: ANN001
    for name in LOADS + STORES:
        if name in RV64ONLY:
            with t.rv64_only():
                fn(name)
        else:
            fn(name)


def gen_hlsv() -> list[TestFile]:
    tests = []
    hv = ILLEGAL if MUT == "hlv_vs_illegal" else VIRTUAL

    t = new("hlsv_mode", scratch=True)
    t.describe(
        source=HYP,
        rule_text="The hypervisor virtual-machine load and store instructions are valid only in M-mode or "
        "HS-mode, or in U-mode when hstatus.HU=1.",
        context="vsatp and hgatp are Bare, so the accesses go to the physical address in the register. Loads "
        "and stores use a scratch page; HLVX reads the test's code, which is executable and readable. The "
        "M-mode part is hlsv_mode_Sm.",
        plan="1. HS-mode: every HLV, HLVX and HSV (HLV.WU, HLV.D and HSV.D on RV64) executes without a trap.\n"
        "2. U-mode with hstatus.HU=1: the same.\n"
        "3. U-mode with HU=0 raises illegal-instruction; VS and VU raise virtual-instruction (one load and one "
        "store each).",
    )
    each_hls(t, lambda n: hls_window(t, "S", n, "ok", "HS-mode"))
    hst(t, "HU", True)
    each_hls(t, lambda n: hls_window(t, "U", n, ILLEGAL if MUT == "hu_ignored" else "ok", "U-mode, hstatus.HU=1"))
    hst(t, "HU", False)
    for n in ("hlv.w", "hsv.w"):
        hls_window(t, "U", n, "ok" if MUT == "hu0_allows" else ILLEGAL, "U-mode, hstatus.HU=0")
        for mode in ("VS", "VU"):
            hls_window(t, mode, n, hv, "V=1")
    tests.append(t)

    t = new_sm("hlsv_mode", scratch=True)
    t.describe(
        source=HYP,
        rule_text="The hypervisor virtual-machine load and store instructions are valid only in M-mode or "
        "HS-mode, or in U-mode when hstatus.HU=1.",
        context="The M-mode part of hlsv_mode, with vsatp and hgatp Bare.",
        plan="1. M-mode: every HLV, HLVX and HSV executes without a trap, with hstatus.HU=0.",
    )
    each_hls(t, lambda n: hls_window(t, "M", n, "ok", "M-mode"))
    tests.append(t)

    t = new("hlsv_virtinst", scratch=True)
    t.describe(
        source=HYP,
        rule_text="Attempts to execute a virtual-machine load/store instruction (HLV, HLVX, or HSV) when V=1 "
        "cause a virtual-instruction exception.",
        context="The instructions are HS-qualified, so V=1 gives virtual-instruction, not illegal-instruction. "
        "hstatus.HU concerns U-mode only.",
        issues=ISSUE_HSQ,
        plan="1. VS-mode and VU-mode, hstatus.HU=0: every HLV, HLVX and HSV raises virtual-instruction (xepc the "
        "instruction, xtval 0 or its bits, origin the mode).\n"
        "2. The same with hstatus.HU=1 (a load and a store).\n"
        "3. A trapping HSV writes nothing: the scratch words keep their value.",
    )
    for mode in ("VS", "VU"):
        each_hls(t, lambda n, mode=mode: hls_window(t, mode, n, hv, "hstatus.HU=0", store_check=n in STORES))
    hst(t, "HU", True)
    for mode in ("VS", "VU"):
        for n in ("hlv.hu", "hsv.b"):
            hls_window(t, mode, n, hv, "hstatus.HU=1", store_check=n in STORES)
    hst(t, "HU", False)
    tests.append(t)

    t = new("hlsv_illegalinst", scratch=True)
    t.describe(
        source=HYP,
        rule_text="Attempts to execute one of these same instructions from U-mode when hstatus.HU=0 cause an "
        "illegal-instruction exception.",
        context="These same instructions: HLV, HLVX and HSV.",
        plan="1. U-mode, HU=0: every HLV, HLVX and HSV raises illegal-instruction (xepc, xtval 0 or the bits, "
        "from U); a trapping HSV writes nothing.\n"
        "2. Setting HU=1 then 0 again: HLV.B and HSV.B raise illegal-instruction again (HU=0 is not sticky).",
    )
    ie = "ok" if MUT == "hu0_allows" else ILLEGAL
    each_hls(t, lambda n: hls_window(t, "U", n, ie, "U-mode, hstatus.HU=0", store_check=n in STORES))
    hst(t, "HU", True)
    hls_window(t, "U", "hlv.b", "ok", "U-mode, hstatus.HU=1")
    hst(t, "HU", False)
    for n in ("hlv.b", "hsv.b"):
        hls_window(t, "U", n, ie, "U-mode, hstatus.HU=0 again", store_check=n in STORES)
    tests.append(t)

    t = new("hstatus_hu_op", scratch=True)
    t.describe(
        source=HYP,
        rule_text="Field HU (Hypervisor in U-mode) controls whether the virtual-machine load/store instructions, "
        "HLV, HLVX, and HSV, can be used also in U-mode. When HU=1, these instructions can be executed in U-mode "
        "the same as in HS-mode. When HU=0, all hypervisor instructions cause an illegal-instruction exception "
        "in U-mode.",
        context="\"The same as in HS-mode\" includes the data: with vsatp and hgatp Bare, a U-mode HLV returns "
        "what an HS-mode HLV returns, and a U-mode HSV writes memory. HU never enables HFENCE or HINVAL in "
        "U-mode (hfence-vvma_hfence-gvma_exceptions).",
        plan="1. HU=1: U-mode HSV.W writes a value that HS-mode reads back; HLV.W, HLV.HU and HLV.B in U-mode "
        "return the same values as plain loads in HS-mode.\n"
        "2. HU=1: HFENCE.VVMA and HFENCE.GVMA (and HINVAL.VVMA/GVMA with Svinval) in U-mode raise "
        "illegal-instruction.\n"
        "3. HU=0: HLV.W and HSV.W, and the fences, raise illegal-instruction in U-mode.",
    )
    hst(t, "HU", True)
    la(t, "x6", "ai_scratch")
    t.li("x8", 0x76543210)
    line, _ = hlsv("hsv.w", "x0", "x6", "x8")
    lab = t.window("U", [line], ILLEGAL if MUT == "hu_ignored" else "ok", "hsv.w (hstatus.HU=1)")
    la(t, "x6", "ai_scratch")
    t.emit("lw x7, 0(x6)")
    t.check("x7", 0x76543210, lab, "a U-mode HSV.W with HU=1 writes memory")
    t.li("x8", -0x665)  # 0xFFFFF99B: sign bits set in the word, halfword and byte
    t.emit("sw x8, 4(x6)")
    for n, off, v32, v64 in (("hlv.w", 4, -0x665, -0x665), ("hlv.hu", 4, 0xF99B, 0xF99B), ("hlv.b", 4, -0x65, -0x65)):
        t.emit(f"addi x6, x6, {off}")
        line, _ = hlsv(n, "x7", "x6")
        lab = t.window("U", [line], ILLEGAL if MUT == "hu_ignored" else "ok", f"{n} (hstatus.HU=1)")
        from aigen import X
        t.check("x7", X(v32 & 0xFFFFFFFF, v64 & (2**64 - 1)), lab, f"a U-mode {n} with HU=1 returns the memory "
                "value, extended as in HS-mode")
        la(t, "x6", "ai_scratch")
    t.li("x6", 0x400)
    t.li("x8", 1)
    fences = [(hfence_vvma(6, 8), "hfence.vvma x6, x8"), (hfence_gvma(6, 8), "hfence.gvma x6, x8")]
    for e, note in fences:
        iw(t, "U", e, note, "ok" if MUT == "hfence_u_hu" else ILLEGAL, "U-mode, hstatus.HU=1")
    with t.only_if(SVINVAL):
        for e, note in ((hinval_vvma(6, 8), "hinval.vvma x6, x8"), (hinval_gvma(6, 8), "hinval.gvma x6, x8")):
            iw(t, "U", e, note, ILLEGAL, "U-mode, hstatus.HU=1")
    hst(t, "HU", False)
    for n in ("hlv.w", "hsv.w"):
        hls_window(t, "U", n, "ok" if MUT == "hu0_allows" else ILLEGAL, "U-mode, hstatus.HU=0")
    t.li("x6", 0x400)
    t.li("x8", 1)
    for e, note in fences:
        iw(t, "U", e, note, ILLEGAL, "U-mode, hstatus.HU=0")
    tests.append(t)

    t = new("H_virtinst_vu_vs_hinst", scratch=True)
    t.describe(
        source=HYP,
        rule_text="in VS-mode or VU-mode, attempts to execute a hypervisor instruction (HLV, HLVX, HSV, or "
        "HFENCE);",
        context="One of the cases that raise a virtual-instruction exception. With Svinval, HINVAL.VVMA and "
        "HINVAL.GVMA also raise virtual-instruction in VS and VU (Svinval_virtual_instruction_vu_vs). "
        "hlsv_virtinst covers every load and store form.",
        issues=ISSUE_HSQ,
        plan="1. VS-mode and VU-mode: HFENCE.VVMA and HFENCE.GVMA with x0/x0, x6/x0, x0/x8, x6/x8; HINVAL.VVMA "
        "and HINVAL.GVMA (Svinval); HLV.W, HLVX.HU and HSV.W: each raises virtual-instruction (xepc, xtval 0 or "
        "the bits, origin the mode).\n"
        "2. The same with mstatus.TVM=1 and hstatus.VTVM=1 for HFENCE.GVMA and HFENCE.VVMA (still "
        "virtual-instruction).",
    )
    vtrap = ILLEGAL if MUT in ("hfence_vs_illegal", "hlv_vs_illegal") else VIRTUAL
    for mode in ("VS", "VU"):
        t.li("x6", 0x2000)
        t.li("x8", 5)
        for rs1, rs2 in ((0, 0), (6, 0), (0, 8), (6, 8)):
            iw(t, mode, hfence_vvma(rs1, rs2), f"hfence.vvma x{rs1}, x{rs2}", vtrap, "V=1")
            iw(t, mode, hfence_gvma(rs1, rs2), f"hfence.gvma x{rs1}, x{rs2}", vtrap, "V=1")
        with t.only_if(SVINVAL):
            iw(t, mode, hinval_vvma(6, 8), "hinval.vvma x6, x8", vtrap, "V=1")
            iw(t, mode, hinval_gvma(6, 8), "hinval.gvma x6, x8", vtrap, "V=1")
        for n in ("hlv.w", "hlvx.hu", "hsv.w"):
            hls_window(t, mode, n, vtrap, "V=1")
    mst(t, MSTATUS_TVM, True, "TVM")
    hst(t, "VTVM", True)
    t.li("x6", 0x2000)
    t.li("x8", 5)
    for mode in ("VS", "VU"):
        iw(t, mode, hfence_gvma(6, 8), "hfence.gvma x6, x8", vtrap, "mstatus.TVM=1, hstatus.VTVM=1")
        iw(t, mode, hfence_vvma(6, 8), "hfence.vvma x6, x8", vtrap, "mstatus.TVM=1, hstatus.VTVM=1")
    hst(t, "VTVM", False)
    mst(t, MSTATUS_TVM, False, "TVM")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- xtval
def gen_xtval() -> list[TestFile]:
    t = new("H_virtinst_xtval", scratch=True)
    t.describe(
        source=HYP,
        rule_text="On a virtual-instruction trap, mtval or stval is written the same as for an "
        "illegal-instruction trap.",
        context="For an illegal-instruction trap, stval holds 0 or the faulting instruction's bits; which one is "
        "an implementation choice, and supervisor.adoc (norm:stval) lets it depend on the underlying event. So "
        "each virtual-instruction trap must leave stval 0 or the instruction bits, like an illegal-instruction "
        "trap; equality with the illegal-instruction trap of the same encoding in U-mode is not required (a "
        "V=0 privilege fault and a V=1 virtual-instruction trap may count as different events). Both traps go "
        "to HS-mode; the U-mode one is run as a reference point.",
        plan="1. For a CSR read of hstatus, a CSR write of sscratch, SRET, SFENCE.VMA x6, x8, HFENCE.VVMA, "
        "HFENCE.GVMA, HLV.W and HSV.W: the VU-mode virtual-instruction trap leaves stval 0 or the instruction "
        "bits, and so does the U-mode illegal-instruction trap of the same encoding.",
    )
    hs_bits(t, "vsstatus", 0x100, False, "vsstatus.SPP = 0")
    cases = [
        (enc_csr(0x600, 2, 7, 0), "csrr x7, hstatus"),
        (enc_csr(0x140, 1, 0, 6), "csrw sscratch, x6"),
        (SRET, "sret"),
        (sfence_vma(6, 8), "sfence.vma x6, x8"),
        (hfence_vvma(6, 8), "hfence.vvma x6, x8"),
        (hfence_gvma(0, 8), "hfence.gvma x0, x8"),
        (hlsv("hlv.w", "x7", "x6")[1], "hlv.w x7, (x6)"),
        (hlsv("hsv.w", "x0", "x6", "x8")[1], "hsv.w x8, (x6)"),
    ]
    for e, note in cases:
        if "sscratch" in note:
            hs_read(t, "x6", "sscratch")  # a wrong success writes the same value
        elif "hlv" in note or "hsv" in note:
            la(t, "x6", "ai_scratch")
        else:
            t.li("x6", 0x1000)
        t.li("x8", 1)
        iw(t, "U", e, note, ILLEGAL, "U-mode")
        # mutant: a virtual-instruction trap writes stval differently (here: the low bit of the bits flipped)
        vt = [e ^ 1] if MUT == "xtval_virtual_other" else [0, e]
        if note == "sret":
            after = t.label("after")
            la(t, "x7", after)
            t.emit(f"csrw {hex(csr_num('vsepc'))}, x7")
            iw(t, "VU", e, note, VIRTUAL, "VU-mode", more=[f"{after}:"], tval=vt)
        else:
            if "sscratch" in note:
                hs_read(t, "x6", "sscratch")
            iw(t, "VU", e, note, VIRTUAL, "VU-mode", tval=vt)
    return [t]


# ---------------------------------------------------------------- FS / VS / SD
FS_MASK, VS_MASK = 0x6000, 0x600
FMV_X_W = 0xE00003D3  # fmv.x.w x7, f0 (reads FP state)
FMV_W_X = 0xF00000D3  # fmv.w.x f1, x0 (writes f1)
FCSR_R = enc_csr(0x003, 2, 7, 0)  # csrr x7, fcsr
FFLAGS_W = enc_csr(0x001, 1, 0, 0)  # csrw fflags, x0
FRM_W = enc_csr(0x002, 1, 0, 0)  # csrw frm, x0
FCSR_W = enc_csr(0x003, 1, 0, 0)  # csrw fcsr, x0
VXRM_W = enc_csr(0x00A, 1, 0, 0)  # csrw vxrm, x0
VCSR_W = enc_csr(0x00F, 1, 0, 0)  # csrw vcsr, x0
VSETVLI = 0x000073D7  # vsetvli x7, x0, e8, m1
VSTART_R = enc_csr(0x008, 2, 7, 0)  # csrr x7, vstart


def fs(t: TestFile, csr: str, v: int) -> None:
    set_field(t, csr, FS_MASK, v << 13, f"{csr}.FS = {v}")


def vsf(t: TestFile, csr: str, v: int) -> None:
    set_field(t, csr, VS_MASK, v << 9, f"{csr}.VS = {v}")


def gen_fs() -> list[TestFile]:
    tests = []
    fsq = VIRTUAL if MUT == "fs_virtual" else ILLEGAL

    t = new("H_illegalinst_xstatus_fs_vs")
    t.describe(
        source=HYP,
        rule_text="Fields FS and VS in registers sstatus and vsstatus deviate from the usual HS-qualified rule. "
        "If an instruction is prevented from executing because FS or VS is zero in either sstatus or vsstatus, "
        "the exception raised is always an illegal-instruction exception, never a virtual-instruction "
        "exception.",
        context="With V=1 both the HS-level sstatus.FS and vsstatus.FS are in effect (vsstatus_fs_op), likewise "
        "VS. Accesses to fcsr and the vector CSRs are prevented the same way as the instructions. Instructions "
        "are .word encodings: fmv.x.w x7, f0 and csrr x7, fcsr (F); vsetvli x7, x0, e8, m1 and csrr x7, vstart "
        "(V).",
        issues=ISSUE_HSQ,
        plan="1. F: in VS-mode and VU-mode, for (sstatus.FS, vsstatus.FS) = (0,3), (3,0), (0,0): fmv.x.w and an "
        "fcsr read raise illegal-instruction (xtval 0 or the bits, from the mode); with (3,3) they succeed.\n"
        "2. V: the same for vsetvli and a vstart read with the VS fields.\n"
        "3. HS-mode with sstatus.FS=0 (and VS=0): illegal-instruction.",
    )
    with t.only_if(F):
        for hsf, vsfv in ((0, 3), (3, 0), (0, 0), (3, 3)):
            fs(t, "sstatus", hsf)
            fs(t, "vsstatus", vsfv)
            ok = hsf and vsfv or (MUT == "fs_hs_ignored" and vsfv)
            for mode in ("VS", "VU"):
                for e, note in ((FMV_X_W, "fmv.x.w x7, f0"), (FCSR_R, "csrr x7, fcsr")):
                    iw(t, mode, e, note, "ok" if ok else fsq, f"sstatus.FS={hsf}, vsstatus.FS={vsfv}")
        fs(t, "sstatus", 0)
        iw(t, "S", FMV_X_W, "fmv.x.w x7, f0", ILLEGAL, "HS-mode, sstatus.FS=0")
        fs(t, "sstatus", 3)
        fs(t, "vsstatus", 3)
    with t.only_if(V):
        for hsv, vsv in ((0, 3), (3, 0), (0, 0), (3, 3)):
            vsf(t, "sstatus", hsv)
            vsf(t, "vsstatus", vsv)
            ok = hsv and vsv
            for mode in ("VS", "VU"):
                for e, note in ((VSETVLI, "vsetvli x7, x0, e8, m1"), (VSTART_R, "csrr x7, vstart")):
                    iw(t, mode, e, note, "ok" if ok else fsq, f"sstatus.VS={hsv}, vsstatus.VS={vsv}")
        vsf(t, "sstatus", 0)
        iw(t, "S", VSETVLI, "vsetvli x7, x0, e8, m1", ILLEGAL, "HS-mode, sstatus.VS=0")
        vsf(t, "sstatus", 3)
        vsf(t, "vsstatus", 3)
    tests.append(t)

    for kind in ("fs", "vs"):
        rule = f"vsstatus_{kind}_op"
        t = new(rule)
        is_f = kind == "fs"
        fld, mask, sh = ("FS", FS_MASK, 13) if is_f else ("VS", VS_MASK, 9)
        modify = [(FMV_W_X, "fmv.w.x f1, x0"), (FFLAGS_W, "csrw fflags, x0"), (FRM_W, "csrw frm, x0"),
                  (FCSR_W, "csrw fcsr, x0")] if is_f else \
            [(VSETVLI, "vsetvli x7, x0, e8, m1"), (VXRM_W, "csrw vxrm, x0"), (VCSR_W, "csrw vcsr, x0")]
        readi = (FMV_X_W, "fmv.x.w x7, f0") if is_f else (VSTART_R, "csrr x7, vstart")
        what = "floating-point" if is_f else "vector"
        t.describe(
            source=HYP,
            rule_text=(
                "When V=1, both vsstatus.FS and the HS-level sstatus.FS are in effect. Attempts to execute a "
                "floating-point instruction when either field is 0 (Off) raise an illegal-instruction exception. "
                "Modifying the floating-point state when V=1 causes both fields to be set to 3 (Dirty)."
                if is_f else
                "Similarly, when V=1, both vsstatus.VS and the HS-level sstatus.VS are in effect. Attempts to "
                "execute a vector instruction when either field is 0 (Off) raise an illegal-instruction "
                "exception. Modifying the vector state when V=1 causes both fields to be set to 3 (Dirty)."
            ),
            context=f"{fld} encodings: 0 Off, 1 Initial, 2 Clean, 3 Dirty. Whether an instruction that does not "
            f"modify {what} state may set Dirty is left open, so Dirty is checked only after modifications. When "
            f"V=0, vsstatus does not affect the machine: modifying {what} state in HS-mode sets sstatus.{fld} "
            f"only.",
            plan=f"1. Every (sstatus.{fld}, vsstatus.{fld}) pair in 0..3: a {what} instruction in VS-mode "
            "succeeds when both are nonzero and raises illegal-instruction otherwise.\n"
            f"2. For (1,1), (1,2), (2,1) and (2,2): each {what}-state-modifying instruction ("
            + ", ".join(n for _, n in modify) + f") in VS-mode, and in VU-mode for (1,2), leaves both fields "
            "Dirty (3).\n"
            f"3. V=0: with sstatus.{fld}=1 and vsstatus.{fld}=1, the same modification in HS-mode sets "
            f"sstatus.{fld}=3 and leaves vsstatus.{fld}=1.",
        )
        cond = F if is_f else V
        with t.only_if(cond):
            for a in range(4):
                for b in range(4):
                    set_field(t, "sstatus", mask, a << sh, f"sstatus.{fld} = {a}")
                    set_field(t, "vsstatus", mask, b << sh, f"vsstatus.{fld} = {b}")
                    ok = a and b or (MUT == "fs_hs_ignored" and b)
                    iw(t, "VS", readi[0], readi[1], "ok" if ok else ILLEGAL, f"sstatus.{fld}={a}, vsstatus.{fld}={b}")
            for a, b, mode in ((1, 1, "VS"), (1, 2, "VS"), (2, 1, "VS"), (2, 2, "VS"), (1, 2, "VU")):
                for e, note in modify:
                    set_field(t, "sstatus", mask, a << sh, f"sstatus.{fld} = {a}")
                    set_field(t, "vsstatus", mask, b << sh, f"vsstatus.{fld} = {b}")
                    lab = iw(t, mode, e, note, "ok", f"sstatus.{fld}={a}, vsstatus.{fld}={b}")
                    hs_read(t, "x7", "sstatus")
                    t.check_masked("x7", mask, (a << sh) if MUT == "fs_dirty_vs_only" else mask, lab,
                                   f"{note} in {mode}-mode sets sstatus.{fld} to Dirty")
                    hs_read(t, "x7", "vsstatus")
                    t.check_masked("x7", mask, mask, lab, f"{note} in {mode}-mode sets vsstatus.{fld} to Dirty")
            for e, note in modify:
                set_field(t, "sstatus", mask, 1 << sh, f"sstatus.{fld} = 1")
                set_field(t, "vsstatus", mask, 1 << sh, f"vsstatus.{fld} = 1")
                lab = iw(t, "S", e, note, "ok", f"HS-mode, sstatus.{fld}=1, vsstatus.{fld}=1")
                hs_read(t, "x7", "sstatus")
                t.check_masked("x7", mask, mask, lab, f"{note} in HS-mode sets sstatus.{fld} to Dirty")
                hs_read(t, "x7", "vsstatus")
                t.check_masked("x7", mask, mask if MUT == "fs_dirty_v0" else (1 << sh), lab,
                               f"{note} in HS-mode leaves vsstatus.{fld} (V=0)")
            set_field(t, "sstatus", mask, mask, f"sstatus.{fld} = 3")
            set_field(t, "vsstatus", mask, mask, f"vsstatus.{fld} = 3")
        tests.append(t)

    t = new("vsstatus_sd_xs_op")
    from aigen import X
    sd = X(1 << 31, 1 << 63)
    t.describe(
        source=HYP,
        rule_text="Read-only fields SD and XS summarize the extension context status as it is visible to VS-mode "
        "only. For example, the value of the HS-level sstatus.FS does not affect vsstatus.SD.",
        context="SD is 1 when FS, VS or XS in the same register is Dirty (3). XS is read-only; with no "
        "additional user extensions it is 0. vsstatus is read in HS-mode and, as sstatus, in VS-mode.",
        plan="1. vsstatus.FS=3 (F) or vsstatus.VS=3 (V): vsstatus.SD=1 with sstatus.FS=0 and VS=0 (HS SD=0).\n"
        "2. vsstatus.FS=0, VS=0 with sstatus.FS=3 (HS SD=1): vsstatus.SD=0, also read in VS-mode as "
        "sstatus.SD.\n"
        "3. vsstatus.FS and VS each 1 or 2: SD=0.\n"
        "4. Writing ones to vsstatus.XS and SD does not change them.",
    )
    num = hex(csr_num("vsstatus"))

    def sd_check(want: int, desc: str, in_vs: bool = False) -> None:
        lab = t.label("sd")
        t.emit(f"{lab}:", 0)
        hs_read(t, "x7", "vsstatus")
        t.check_masked("x7", sd, sd if want else 0, lab, f"vsstatus.SD ({desc})")
        if in_vs:
            lab = t.window("VS", [f"csrr x7, {hex(csr_num('sstatus'))}  // sstatus (V=1: vsstatus)"], "ok",
                           "read sstatus")
            t.check_masked("x7", sd, sd if want else 0, lab, f"sstatus.SD read in VS-mode ({desc})")

    def setfs(h: int, v: int) -> None:
        with t.only_if(F):
            fs(t, "sstatus", h)
            fs(t, "vsstatus", v)

    def setvs(h: int, v: int) -> None:
        with t.only_if(V):
            vsf(t, "sstatus", h)
            vsf(t, "vsstatus", v)

    with t.only_if(F):
        setfs(0, 3)
        setvs(0, 0)
        sd_check(1, "vsstatus.FS=3, sstatus.FS=0")
    with t.only_if(V):
        setfs(0, 0)
        setvs(0, 3)
        sd_check(1, "vsstatus.VS=3, sstatus.VS=0")
    with t.only_if(f"{F} || {V}"):
        setfs(3, 0)
        setvs(3, 0)
        sd_check(1 if MUT == "sd_uses_hs_fs" else 0, "vsstatus FS=VS=0, sstatus FS=VS=3", in_vs=True)
        for v in (1, 2):
            setfs(3, v)
            setvs(3, v)
            sd_check(1 if MUT == "sd_uses_hs_fs" else 0, f"vsstatus FS=VS={v}, sstatus FS=VS=3")
        setfs(3, 0)
        setvs(3, 0)
    hs_read(t, "x8", "vsstatus")
    lab = t.label("xs")
    t.emit(f"{lab}:", 0)
    t.li("x7", 0x18000)
    t.emit(f"csrs {num}, x7  // try to set XS")
    hs_read(t, "x7", "vsstatus")
    t.emit("xor x7, x7, x8")
    t.check_masked("x7", X(0x80018000, (1 << 63) | 0x18000), 0, lab, "writing XS in vsstatus changes neither XS nor SD")
    setfs(3, 3)
    setvs(3, 3)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- CBO enables
CBIE, CBCFE, CBZE = 0x30, 0x40, 0x80


def cbo(imm: int, rs1: int = 6) -> int:
    return (imm << 20) | (rs1 << 15) | 0x200F


CBO_ZERO, CBO_CLEAN, CBO_FLUSH, CBO_INVAL = cbo(4), cbo(1), cbo(2), cbo(0)


def env(t: TestFile, which: str, bits: int, val: int) -> None:
    """Set field `bits` of menvcfg (T-SBI), henvcfg or senvcfg (HS-mode) to val (shifted)."""
    if which == "menvcfg":
        m_bits(t, "menvcfg", bits, False, f"M-mode: menvcfg field {hex(bits)} = 0")
        if val:
            m_bits(t, "menvcfg", val, True, f"M-mode: menvcfg field {hex(bits)} |= {hex(val)}")
    else:
        set_field(t, which, bits, val, f"{which} field {hex(bits)} = {hex(val)}")


def cbo_win(t: TestFile, mode: str, e: int, note: str, expect: Expect, desc: str, zero_check: bool = False) -> str:
    la(t, "x6", "ai_scratch")
    if zero_check:
        t.li("x7", 0x5A5A)
        t.emit("sw x7, 0(x6)")
    lab = iw(t, mode, e, note + " (x6 = scratch block)", expect, desc)
    if zero_check:
        la(t, "x6", "ai_scratch")
        t.emit("lw x7, 0(x6)")
        t.check("x7", 0 if expect == "ok" else 0x5A5A, lab, f"{note} {'zeroes' if expect == 'ok' else 'leaves'} "
                "the block")
    return lab


def gen_cbo() -> list[TestFile]:
    tests = []
    vt = ILLEGAL if MUT == "cbze_illegal" else VIRTUAL

    t = new("henvcfg_cbze", scratch=True)
    t.describe(
        source=HYP,
        rule_text="The Zicboz extension adds the CBZE (Cache Block Zero instruction enable) field to henvcfg. The "
        "CBZE field applies to execution of the cache block zero instruction (CBO.ZERO) in privilege modes VS "
        "and VU, and only when the instruction is HS-qualified. If the instruction is not HS-qualified, it "
        "raises an illegal-instruction exception. If the instruction is HS-qualified and the CBZE field is set "
        "to 1, the instruction is enabled for execution; otherwise, if the CBZE field is set to 0, it raises a "
        "virtual-instruction exception. When the Zicboz extension is not implemented, CBZE is read-only zero.",
        context="CBO.ZERO is HS-qualified when menvcfg.CBZE=1. In VU-mode, senvcfg.CBZE applies as well "
        "(H_scsrs_nomatch); its denial is HS-qualified, so it is a virtual-instruction exception too. The "
        "instruction zeroes the cache block containing x6, a 4 KiB-aligned scratch page.",
        issues=ISSUE_HSQ,
        plan="1. Zicboz, menvcfg.CBZE=1, senvcfg.CBZE=1: henvcfg.CBZE=1, CBO.ZERO in VS and VU zeroes the block; "
        "henvcfg.CBZE=0, it raises virtual-instruction and the block keeps its data.\n"
        "2. henvcfg.CBZE=1, senvcfg.CBZE=0: VU-mode raises virtual-instruction, VS-mode still zeroes.\n"
        "3. menvcfg.CBZE=0: VS and VU raise illegal-instruction for both henvcfg.CBZE values; HS-mode raises "
        "illegal-instruction.\n"
        "4. henvcfg.CBZE=0 does not affect HS-mode: CBO.ZERO zeroes the block.\n"
        "5. Without Zicboz: henvcfg.CBZE reads 0 after a write of 1.",
    )
    with t.only_if(CBOZ):
        for h in (1, 0):
            env(t, "henvcfg", CBZE, CBZE * h)
            for mode in ("VS", "VU"):
                exp = "ok" if (h or MUT == "cbze_ignored") else vt
                cbo_win(t, mode, CBO_ZERO, "cbo.zero", exp, f"menvcfg.CBZE=1, henvcfg.CBZE={h}, senvcfg.CBZE=1", True)
        env(t, "henvcfg", CBZE, CBZE)
        env(t, "senvcfg", CBZE, 0)
        cbo_win(t, "VU", CBO_ZERO, "cbo.zero", "ok" if MUT == "cbze_vu_ignores_senvcfg" else VIRTUAL,
                "henvcfg.CBZE=1, senvcfg.CBZE=0", True)
        cbo_win(t, "VS", CBO_ZERO, "cbo.zero", "ok", "henvcfg.CBZE=1, senvcfg.CBZE=0", True)
        env(t, "senvcfg", CBZE, CBZE)
        env(t, "menvcfg", CBZE, 0)
        mexp = VIRTUAL if MUT == "cbze_menvcfg_virtual" else ILLEGAL
        for h in (1, 0):
            env(t, "henvcfg", CBZE, CBZE * h)
            for mode in ("VS", "VU"):
                cbo_win(t, mode, CBO_ZERO, "cbo.zero", mexp, f"menvcfg.CBZE=0, henvcfg.CBZE={h}", True)
        cbo_win(t, "S", CBO_ZERO, "cbo.zero", ILLEGAL, "HS-mode, menvcfg.CBZE=0", True)
        env(t, "menvcfg", CBZE, CBZE)
        env(t, "henvcfg", CBZE, 0)
        cbo_win(t, "S", CBO_ZERO, "cbo.zero", vt if MUT == "cbze_affects_hs" else "ok", "HS-mode, henvcfg.CBZE=0",
                True)
        env(t, "henvcfg", CBZE, CBZE)
    with t.only_if("!defined(ZICBOZ_SUPPORTED) && defined(S1P12P0_OR_LATER_SUPPORTED)"):
        hs_bits(t, "henvcfg", CBZE, True, "henvcfg.CBZE = 1")
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        hs_read(t, "x7", "henvcfg")
        t.check_masked("x7", CBZE, 0, lab, "henvcfg.CBZE is read-only zero without Zicboz")
    tests.append(t)

    t = new("henvcfg_cbcfe", scratch=True)
    t.describe(
        source=HYP,
        rule_text="The Zicbom extension adds the CBCFE (Cache Block Clean and Flush instruction Enable) field to "
        "henvcfg. When V=1, if the CBO.CLEAN and CBO.FLUSH instructions are not HS-qualified, they raise an "
        "illegal-instruction exception. If the instructions are HS-qualified and the CBCFE field is set to 1, "
        "the instructions are enabled for execution; otherwise, if the CBCFE field is set to 0, they raise a "
        "virtual-instruction exception. When the Zicbom extension is not implemented, CBCFE is read-only zero.",
        context="HS-qualified means menvcfg.CBCFE=1. In VU-mode senvcfg.CBCFE applies too.",
        issues=ISSUE_HSQ,
        plan="1. Zicbom, menvcfg.CBCFE=1, senvcfg.CBCFE=1: henvcfg.CBCFE=1, CBO.CLEAN and CBO.FLUSH succeed in VS "
        "and VU; henvcfg.CBCFE=0, they raise virtual-instruction.\n"
        "2. henvcfg.CBCFE=1, senvcfg.CBCFE=0: virtual-instruction in VU-mode, success in VS-mode.\n"
        "3. menvcfg.CBCFE=0: illegal-instruction in VS and VU for both henvcfg values.\n"
        "4. henvcfg.CBCFE=0 does not affect HS-mode.\n"
        "5. Without Zicbom: henvcfg.CBCFE reads 0 after a write of 1.",
    )
    with t.only_if(CBOM):
        for h in (1, 0):
            env(t, "henvcfg", CBCFE, CBCFE * h)
            for mode in ("VS", "VU"):
                for e, n in ((CBO_CLEAN, "cbo.clean"), (CBO_FLUSH, "cbo.flush")):
                    cbo_win(t, mode, e, n, "ok" if (h or MUT == "cbcfe_ignored") else VIRTUAL,
                            f"menvcfg.CBCFE=1, henvcfg.CBCFE={h}")
        env(t, "henvcfg", CBCFE, CBCFE)
        env(t, "senvcfg", CBCFE, 0)
        cbo_win(t, "VU", CBO_FLUSH, "cbo.flush", VIRTUAL, "henvcfg.CBCFE=1, senvcfg.CBCFE=0")
        cbo_win(t, "VS", CBO_FLUSH, "cbo.flush", "ok", "henvcfg.CBCFE=1, senvcfg.CBCFE=0")
        env(t, "senvcfg", CBCFE, CBCFE)
        env(t, "menvcfg", CBCFE, 0)
        for h in (1, 0):
            env(t, "henvcfg", CBCFE, CBCFE * h)
            for mode in ("VS", "VU"):
                cbo_win(t, mode, CBO_CLEAN, "cbo.clean", ILLEGAL, f"menvcfg.CBCFE=0, henvcfg.CBCFE={h}")
        env(t, "menvcfg", CBCFE, CBCFE)
        env(t, "henvcfg", CBCFE, 0)
        cbo_win(t, "S", CBO_FLUSH, "cbo.flush", "ok", "HS-mode, henvcfg.CBCFE=0")
        env(t, "henvcfg", CBCFE, CBCFE)
    with t.only_if("!defined(ZICBOM_SUPPORTED) && defined(S1P12P0_OR_LATER_SUPPORTED)"):
        hs_bits(t, "henvcfg", CBCFE, True, "henvcfg.CBCFE = 1")
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        hs_read(t, "x7", "henvcfg")
        t.check_masked("x7", CBCFE, 0, lab, "henvcfg.CBCFE is read-only zero without Zicbom")
    tests.append(t)

    def probe_cbie(reg: str) -> None:
        """reg = 1 if henvcfg.CBIE reads 01 or 11 (enabled), 0 if 00."""
        hs_read(t, reg, "henvcfg")
        t.emit(f"srli {reg}, {reg}, 4")
        t.emit(f"andi {reg}, {reg}, 1")

    t = new("henvcfg_cbie", scratch=True)
    t.describe(
        source=HYP,
        rule_text="The Zicbom extension adds the CBIE (Cache Block Invalidate instruction Enable) WARL field to "
        "henvcfg. The CBIE field controls execution of the cache block invalidate instruction (CBO.INVAL) in "
        "privilege modes VS and VU. The encoding 0b10 is reserved. When the Zicbom extension is not "
        "implemented, CBIE is read-only zero.",
        context="CBIE is WARL, so after writing 01 or 11 the test reads the field and accepts whichever legal "
        "value is held, branching on it: 01 and 11 enable CBO.INVAL (as a flush or an invalidate), 00 denies "
        "it with virtual-instruction (cbo-inval_h_mode_veq1_op). The reserved 10 is never written. "
        "menvcfg.CBIE=11 and senvcfg.CBIE=11 (the boot values).",
        plan="1. Zicbom: henvcfg.CBIE=00: CBO.INVAL raises virtual-instruction in VS and VU.\n"
        "2. henvcfg.CBIE written 01 and 11: the read-back value is 00, 01 or 11 (never 10); if nonzero, "
        "CBO.INVAL succeeds in VS and VU, otherwise it raises virtual-instruction.\n"
        "3. Without Zicbom: henvcfg.CBIE reads 0 after a write of 11.",
    )
    with t.only_if(CBOM):
        env(t, "menvcfg", CBIE, CBIE)
        env(t, "henvcfg", CBIE, 0)
        for mode in ("VS", "VU"):
            cbo_win(t, mode, CBO_INVAL, "cbo.inval", "ok" if MUT == "cbie_ignored" else VIRTUAL, "henvcfg.CBIE=00")
        for w in (0x10, 0x30):
            env(t, "henvcfg", CBIE, w)
            lab = t.label("rb")
            t.emit(f"{lab}:", 0)
            hs_read(t, "x7", "henvcfg")
            t.emit("andi x7, x7, 0x30")
            t.emit("addi x7, x7, -0x20")
            t.emit("snez x7, x7")
            t.check_bool("x7", lab, f"henvcfg.CBIE after writing {w >> 4:02b} is not the reserved 10")
            probe_cbie("x1")
            t.either(
                "x1",
                lambda w=w: [cbo_win(t, m, CBO_INVAL, "cbo.inval", "ok", f"henvcfg.CBIE written {w >> 4:02b}, enabled")
                             for m in ("VS", "VU")],
                lambda w=w: [cbo_win(t, m, CBO_INVAL, "cbo.inval", VIRTUAL, f"henvcfg.CBIE written {w >> 4:02b}, "
                                     "reads 00") for m in ("VS", "VU")],
            )
        env(t, "henvcfg", CBIE, CBIE)
    with t.only_if("!defined(ZICBOM_SUPPORTED) && defined(S1P12P0_OR_LATER_SUPPORTED)"):
        hs_bits(t, "henvcfg", CBIE, True, "henvcfg.CBIE = 11")
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        hs_read(t, "x7", "henvcfg")
        t.check_masked("x7", CBIE, 0, lab, "henvcfg.CBIE is read-only zero without Zicbom")
    tests.append(t)

    t = new("cbo-inval_h_mode_veq1_op", scratch=True)
    t.describe(
        source=HYP,
        rule_text="When V=1, if the CBO.INVAL instruction is not HS-qualified, it raises an illegal-instruction "
        "exception. If the instruction is HS-qualified and the CBIE field is set to 0b01 or 0b11, the "
        "instruction is enabled for execution; otherwise, it raises a virtual-instruction exception.",
        context="CBO.INVAL is HS-qualified when menvcfg.CBIE is not 00. The CBIE fields are WARL: after each "
        "write the test reads menvcfg.CBIE (T-SBI) and henvcfg.CBIE and branches on whether each is nonzero. "
        "In VU-mode senvcfg.CBIE also applies (kept at 11 here, except one case).",
        issues=ISSUE_HSQ,
        plan="1. For menvcfg.CBIE written 00, 01, 11 and henvcfg.CBIE written 00, 01, 11: CBO.INVAL in VS and "
        "VU raises illegal-instruction if menvcfg.CBIE reads 00; otherwise succeeds if henvcfg.CBIE reads "
        "nonzero, else raises virtual-instruction.\n"
        "2. menvcfg.CBIE=11, henvcfg.CBIE=11, senvcfg.CBIE=00: VU-mode raises virtual-instruction, VS-mode "
        "succeeds.",
    )
    with t.only_if(CBOM):
        for mv in (0, 0x10, 0x30):
            env(t, "menvcfg", CBIE, mv)
            t.tsbi_csr("READ", "MENVCFG")
            t.emit("srli x1, a0, 4")
            t.emit("andi x1, x1, 3")
            for hv in (0, 0x10, 0x30):
                env(t, "henvcfg", CBIE, hv)
                probe_cbie("x8")
                desc = f"menvcfg.CBIE written {mv >> 4:02b}, henvcfg.CBIE written {hv >> 4:02b}"

                def m_on(desc: str = desc) -> None:
                    t.either(
                        "x8",
                        lambda: [cbo_win(t, m, CBO_INVAL, "cbo.inval", "ok", desc + " (both enabled)")
                                 for m in ("VS", "VU")],
                        lambda: [cbo_win(t, m, CBO_INVAL, "cbo.inval", VIRTUAL, desc + " (henvcfg.CBIE reads 00)")
                                 for m in ("VS", "VU")],
                    )

                mexp = VIRTUAL if MUT == "cbie_menvcfg_virtual" else ILLEGAL
                t.either("x1", m_on, lambda desc=desc: [cbo_win(t, m, CBO_INVAL, "cbo.inval", mexp,
                                                                 desc + " (menvcfg.CBIE reads 00)")
                                                         for m in ("VS", "VU")])
        env(t, "menvcfg", CBIE, CBIE)
        env(t, "henvcfg", CBIE, CBIE)
        env(t, "senvcfg", CBIE, 0)
        cbo_win(t, "VU", CBO_INVAL, "cbo.inval", VIRTUAL, "senvcfg.CBIE=00, henvcfg.CBIE=11")
        cbo_win(t, "VS", CBO_INVAL, "cbo.inval", "ok", "senvcfg.CBIE=00, henvcfg.CBIE=11")
        env(t, "senvcfg", CBIE, CBIE)
    tests.append(t)

    t = new("cbo-inval_h_mode_enabled_op", scratch=True)
    t.describe(
        source=HYP,
        rule_text="If CBO.INVAL is enabled in HS-mode to perform a flush operation, then when the instruction is "
        "enabled in VS- or VU-mode it performs a flush operation, even if CBIE is set to 0b11. Otherwise, when "
        "the instruction is enabled for execution, its behavior depends on the CBIE encoding, as follows:",
        context="HS-mode performs a flush when menvcfg.CBIE=01. A flush writes dirty data back, so a value "
        "stored to the block just before CBO.INVAL is still read afterwards; an invalidate may discard it. On "
        "a hart without caches both read the stored value, so the test can only catch a discarding "
        "invalidate. menvcfg.CBIE is WARL: if 01 is not held, the case is skipped.",
        plan="1. menvcfg.CBIE=01 (if held), henvcfg.CBIE=11, senvcfg.CBIE=11: in VS-mode and VU-mode, a store "
        "of a new value to the scratch block followed by CBO.INVAL leaves the new value readable (flush, not "
        "invalidate).\n"
        "2. The same with henvcfg.CBIE=01.",
    )
    with t.only_if(CBOM):
        env(t, "menvcfg", CBIE, 0x10)
        t.tsbi_csr("READ", "MENVCFG")
        t.emit("srli x1, a0, 4")
        t.emit("andi x1, x1, 3")
        t.emit("addi x1, x1, -1")
        t.emit("seqz x1, x1")  # 1 if menvcfg.CBIE reads 01

        def flush_cases() -> None:
            for hv in (0x30, 0x10):
                env(t, "henvcfg", CBIE, hv)
                for mode in ("VS", "VU"):
                    la(t, "x6", "ai_scratch")
                    t.li("x7", 0x1111)
                    t.emit("sw x7, 8(x6)")
                    t.emit("fence")
                    val = 0x2222 + hv
                    lab = t.label(f"in_{mode}")
                    t.allow(1)
                    t.enter(mode)
                    t.li("x7", val)
                    t.emit("sw x7, 8(x6)")
                    t.emit(f"{lab}:", 0)
                    t.emit(word(CBO_INVAL, "cbo.inval (x6)"))
                    t.emit("lw x7, 8(x6)")
                    t.leave()
                    t.outcome("ok", lab, f"cbo.inval in {mode}-mode (menvcfg.CBIE=01, henvcfg.CBIE={hv >> 4:02b})")
                    t.check("x7", val, lab, f"cbo.inval in {mode}-mode flushes: the stored value survives")
        t.either("x1", flush_cases, lambda: t.comment("menvcfg.CBIE cannot hold 01"))
        env(t, "menvcfg", CBIE, CBIE)
        env(t, "henvcfg", CBIE, CBIE)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- senvcfg / scounteren with V=1
def gen_nomatch() -> list[TestFile]:
    t = new("H_scsrs_nomatch", scratch=True)
    t.describe(
        source=HYP,
        rule_text="Some standard supervisor CSRs (senvcfg, scounteren, and scontext, possibly others) have no "
        "matching VS CSR. These supervisor CSRs continue to have their usual function and accessibility even "
        "when V=1, except with VS-mode and VU-mode substituting for HS-mode and U-mode.",
        context="So a VS-mode write of scounteren or senvcfg changes the one register HS-mode sees, and that "
        "register gates VU-mode as it gates U-mode. scounteren bits are WARL (each writable or read-only "
        "zero), so values are compared with the mask of writable bits. scontext (Sdtrig) is not tested: its "
        "presence is a parameter.",
        plan="1. VS-mode reads scounteren and senvcfg without a trap and gets HS-mode's values.\n"
        "2. VS-mode writes scounteren = P and HS-mode reads P & W, where W is the writable mask (HS-mode writes "
        "all ones and reads W first).\n"
        "3. With Zicntr and scounteren.CY writable and mcounteren.CY, hcounteren.CY set: after VS-mode clears "
        "scounteren.CY, a VU-mode cycle read raises virtual-instruction; after VS-mode sets it, the read "
        "succeeds.\n"
        "4. Zicboz: VS-mode clears senvcfg.CBZE; HS-mode reads it as 0, and VU-mode CBO.ZERO raises "
        "virtual-instruction; VS-mode sets it again and VU-mode CBO.ZERO succeeds.",
    )
    sc = hex(csr_num("scounteren"))
    se = hex(csr_num("senvcfg"))
    t.emit("li x7, -1")
    t.emit(f"csrw {sc}, x7  // scounteren = all ones")
    hs_read(t, "x1", "scounteren")  # W
    lab = t.window("VS", [f"csrr x7, {sc}  // scounteren"], "ok", "read scounteren")
    eq(t, "x7", "x1", lab, "a VS-mode read of scounteren returns HS-mode's scounteren")
    with t.only_if("defined(S1P12P0_OR_LATER_SUPPORTED)"):
        hs_read(t, "x8", "senvcfg")
        lab = t.window("VS", [f"csrr x7, {se}  // senvcfg"], "ok", "read senvcfg")
        eq(t, "x7", "x8", lab, "a VS-mode read of senvcfg returns HS-mode's senvcfg")
    t.li("x6", 0x5)
    lab = t.window("VS", [f"csrw {sc}, x6  // scounteren = 0x5"], "ok", "write scounteren")
    hs_read(t, "x7", "scounteren")
    t.emit("and x8, x1, x6")
    if MUT == "scounteren_shadowed":
        t.emit("mv x8, x1")
    eq(t, "x7", "x8", lab, "a VS-mode write of scounteren reaches HS-mode's scounteren (0x5 & writable bits)")
    t.emit("li x7, -1")
    t.emit(f"csrw {sc}, x7")
    with t.only_if("defined(ZICNTR_SUPPORTED)"):
        m_bits(t, "mcounteren", 1, True, "mcounteren.CY = 1")
        t.tsbi_csr("READ", "MCOUNTEREN")
        hs_read(t, "x8", "hcounteren")
        t.emit("and x8, x8, a0")
        t.emit("and x8, x8, x1")
        t.emit("andi x8, x8, 1")  # CY usable in all three

        def cy() -> None:
            t.li("x6", 1)
            t.window("VS", [f"csrc {sc}, x6  // clear scounteren.CY"], "ok", "clear scounteren.CY")
            cw = enc_csr(0xC00, 2, 7, 0)
            iw(t, "VU", cw, "csrr x7, cycle", "ok" if MUT == "scounteren_shadowed" else VIRTUAL,
               "scounteren.CY cleared by VS-mode")
            t.li("x6", 1)
            t.window("VS", [f"csrs {sc}, x6  // set scounteren.CY"], "ok", "set scounteren.CY")
            iw(t, "VU", cw, "csrr x7, cycle", "ok", "scounteren.CY set by VS-mode")

        t.either("x8", cy, lambda: t.comment("CY not writable in every counter-enable register"))
    t.emit("li x7, -1")
    t.emit(f"csrw {sc}, x7")
    with t.only_if(CBOZ):
        t.li("x6", CBZE)
        lab = t.window("VS", [f"csrc {se}, x6  // senvcfg.CBZE = 0"], "ok", "clear senvcfg.CBZE")
        hs_read(t, "x7", "senvcfg")
        t.check_masked("x7", CBZE, CBZE if MUT == "scounteren_shadowed" else 0, lab,
                       "a VS-mode write of senvcfg reaches HS-mode's senvcfg")
        cbo_win(t, "VU", CBO_ZERO, "cbo.zero", VIRTUAL, "senvcfg.CBZE cleared by VS-mode")
        t.li("x6", CBZE)
        t.window("VS", [f"csrs {se}, x6  // senvcfg.CBZE = 1"], "ok", "set senvcfg.CBZE")
        cbo_win(t, "VU", CBO_ZERO, "cbo.zero", "ok", "senvcfg.CBZE set by VS-mode", True)
    return [t]


# ---------------------------------------------------------------- SRET in VS-mode
def gen_sret_v1() -> list[TestFile]:
    t = new("sret_v1")
    t.describe(
        source=HYP,
        rule_text="When executed in VS-mode (i.e., V=1), SRET sets the privilege mode according to <<h-vspp>>, "
        "in vsstatus sets SPP=0, SIE=SPIE, and SPIE=1, and lastly sets pc=vsepc.",
        context="h-vspp: vsstatus.SPP=0 gives VU-mode, SPP=1 VS-mode (V stays 1). The target is a label after "
        "the SRET; a register marks a fall-through. The mode reached is identified by a read of sstatus, which "
        "succeeds in VS-mode and raises virtual-instruction in VU-mode. hstatus.VTSR=0. No interrupts are "
        "pending, so SIE=1 is harmless.",
        plan="1. For vsstatus.SPP in {0, 1} and (SPIE, SIE) in {00, 01, 10, 11}: SRET in VS-mode continues at "
        "vsepc (not at the next instruction), in VS-mode when SPP=1 and VU-mode when SPP=0.\n"
        "2. Afterwards vsstatus.SPP=0, SIE=old SPIE, SPIE=1.\n"
        "3. vsepc is unchanged.",
    )
    for spp in (1, 0):
        for spie in (0, 1):
            for sie in (0, 1):
                bits = (spp << 8) | (spie << 5) | (sie << 1)
                set_field(t, "vsstatus", 0x122, bits, f"vsstatus SPP={spp} SPIE={spie} SIE={sie}")
                desc = f"vsstatus.SPP={spp}, SPIE={spie}, SIE={sie}"
                tgt = t.label("target")
                la(t, "x7", tgt)
                t.emit(f"csrw {hex(csr_num('vsepc'))}, x7")
                t.emit("li x9, 0")
                lab = t.label("rd")
                t.allow(1)
                t.enter("VS")
                t.emit(word(SRET, "sret"))
                t.emit("li x9, 1  // fall-through: sret did not jump")
                t.emit(f"{tgt}:", 0)
                t.emit(f"{lab}:", 0)
                t.emit(f"csrr x7, {hex(csr_num('sstatus'))}  // VS: vsstatus; VU: virtual-instruction")
                t.leave()
                t.outcome("ok" if spp else VIRTUAL, lab, f"sret ({desc}): read of sstatus at vsepc",
                          [0, enc_csr(0x100, 2, 7, 0)], origin="VS" if spp else "VU")
                t.check("x9", 0, lab, f"sret ({desc}) jumps to vsepc")
                hs_read(t, "x7", "vsstatus")
                nspp = spp if MUT == "sret_v1_spp" else 0
                nspie = spie if MUT == "sret_v1_spie" else 1
                nsie = sie if MUT == "sret_v1_sie" else spie
                t.check_masked("x7", 0x122, (nspp << 8) | (nspie << 5) | (nsie << 1), lab,
                               f"sret ({desc}) sets vsstatus.SPP=0, SIE=SPIE, SPIE=1")
                hs_read(t, "x7", "vsepc")
                la(t, "x8", tgt)
                eq(t, "x7", "x8", lab, f"sret ({desc}) leaves vsepc")
    set_field(t, "vsstatus", 0x122, 0, "vsstatus SPP=SPIE=SIE=0")
    return [t]


def gen() -> list[TestFile]:
    return (gen_vtsr() + gen_wfi() + gen_vu_sret() + gen_vtvm() + gen_mstatus_modes() + gen_tvm_hfence()
            + gen_hlsv() + gen_xtval() + gen_fs() + gen_cbo() + gen_nomatch() + gen_sret_v1())
