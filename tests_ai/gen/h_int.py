# SPDX-License-Identifier: Apache-2.0
"""H suite: VS-level and hypervisor interrupts (hvip, hip, hie, hideleg, vsip, vsie, mip/mie aliases, mideleg,
hgeip/hgeie, hstatus.VGEIN, delegation, cause translation and priority).

Interrupt sources: hvip.VSSIP/VSTIP/VSEIP (HS-mode writes), sip.SSIP (HS-mode writes), mip.STIP and mip.SEIP
(M-mode writes through T-SBI; menvcfg.STCE is 0 at boot, so mip.STIP is writable), sip.LCOFIP with Sscofpmf, and
guest external interrupts through the platform (RVTEST_SET_GUEST_EXT_INT_S, which the framework provides when the
DUT implements guest interrupt files: RVTEST_SGEI_INTR_IMPL). The framework handler masks a taken interrupt's
enable bit and clears its source, so several pending interrupts are taken one after another, in priority order,
and recorded in the trap log (4 entries).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hlib import HYP, MUT, X, delay, icause, m_read, new

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import TestFile

MUTANTS = {
    "vsip_no_shift": "vsip/vsie SSIP/STIP/SEIP alias hip/hie at bits 2/6/10 instead of 1/5/9",
    "vsip_ignores_hideleg": "vsip/vsie alias hip/hie even when the hideleg bit is 0",
    "no_cause_translation": "a VS-level interrupt delegated to VS-mode is reported with cause 2/6/10",
    "hs_needs_sie_from_v": "a VS-level interrupt for HS-mode is taken from VS/VU only when sstatus.SIE=1",
    "deleg_taken_in_hs": "HS-mode with SIE=1 takes a VS-level interrupt that hideleg delegates",
    "vu_needs_sie": "a delegated interrupt in VU-mode is taken only when vsstatus.SIE=1",
    "prio_by_number": "simultaneous HS interrupts are taken in decreasing cause-number order",
    "vsti_over_vssi": "VSTI has higher priority than VSSI",
    "hip_vstip_writable": "hip.VSTIP and hip.VSEIP are writable",
    "hip_write_clobbers_hvip": "a write of hip also writes hvip.VSTIP/VSEIP",
    "mideleg_vs_writable": "M-mode can clear the VS-level bits of mideleg",
    "mip_vstip_writable": "an M-mode write of mip.VSTIP/VSEIP sets hip.VSTIP/VSEIP",
    "hideleg_s_bits_writable": "hideleg bits 1, 5 and 9 are writable",
    "hvip_extra_bit": "hvip bit 1 (SSIP) is writable",
    "hgeie_gates_vseip": "hgeie gates the VS-level external interrupt selected by VGEIN",
    "vgein_ignored": "hip.VSEIP ignores hstatus.VGEIN (always 0 from hgeip)",
    "vector_untranslated": "a vectored VS-mode interrupt enters at vstvec + 4*(untranslated cause)",
    "hie_sie_shared": "sie.SSIE also enables the VS-level software interrupt",
    "deleg_routes_to_hs_from_vs": "a delegated interrupt taken from VS-mode goes to HS-mode",
}

# CSR numbers
HVIP, HIP, HIE, HIDELEG = 0x645, 0x644, 0x604, 0x603
VSIP, VSIE, VSSTATUS, VSTVEC = 0x244, 0x204, 0x200, 0x205
SSTATUS, SIP, SIE_CSR = 0x100, 0x144, 0x104
HGEIE, HGEIP, HSTATUS = 0x607, 0xE12, 0x600
SIE, SPIE = 0x2, 0x20
STD = 0x1FFF  # bits 12:0 (bits 13 and up may belong to LCOFI, AIA or the platform)
VS_INTS = [("VSSI", 2), ("VSTI", 6), ("VSEI", 10)]
NAME = {1: "SSI", 5: "STI", 9: "SEI", 2: "VSSI", 6: "VSTI", 10: "VSEI", 12: "SGEI", 13: "LCOFI"}
SGEI = "defined(RVTEST_SGEI_INTR_IMPL)"  # framework provides RVTEST_SET_GUEST_EXT_INT_S (the DUT can raise hgeip)
H_IMPL = "hypervisor.adoc"

ISSUE_ALIAS = (
    "vsip/vsie bits 1, 5 and 9 (SSIP/SSIE, STIP/STIE, SEIP/SEIE) alias hip/hie bits 2, 6 and 10 only while the "
    "matching hideleg bit is set (vsip_vsie_ssi/sti/sei); otherwise they are read-only zero."
)


# ---------------------------------------------------------------- helpers
def csr(n: int, name: str) -> str:
    return f"{hex(n)}  // {name}"


def w(t: TestFile, num: int, name: str, value: int | None = None, reg: str = "x7") -> None:
    """csrw of a small constant (li) or reg."""
    if value is not None:
        t.li(reg, value)
    t.emit(f"csrw {csr(num, name)}".replace("  //", f", {reg}  //", 1))


def cs(t: TestFile, num: int, name: str, bits: int, on: bool) -> None:
    t.li("x7", bits)
    t.emit(f"{'csrs' if on else 'csrc'} {hex(num)}, x7  // {name}")


def rd(t: TestFile, reg: str, num: int, name: str) -> None:
    t.emit(f"csrr {reg}, {csr(num, name)}")


def no_hs_sie(t: TestFile) -> None:
    """sstatus.SIE = SPIE = 0, so neither HS-mode itself nor a later sret/T-SBI return enables HS interrupts."""
    t.li("x7", SIE | SPIE)
    t.emit(f"csrc {hex(SSTATUS)}, x7  // sstatus.SIE/SPIE = 0")


def reset(t: TestFile) -> None:
    t.comment("reset: hvip = hie = hideleg = 0, vsstatus.SIE = sstatus.SIE = SPIE = 0")
    t.emit(f"csrw {hex(HVIP)}, x0  // hvip")
    t.emit(f"csrw {hex(HIE)}, x0  // hie")
    t.emit(f"csrw {hex(HIDELEG)}, x0  // hideleg")
    t.li("x7", SIE)
    t.emit(f"csrc {hex(VSSTATUS)}, x7  // vsstatus.SIE = 0")
    no_hs_sie(t)


def log_word(t: TestFile, reg: str, back: int, word: str) -> None:
    """reg = word `word` (TRAPLOG_*) of the trap-log entry `back` entries before the last (0: the last)."""
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, {-(back + 1)}")
    t.emit("andi x5, x5, RVTEST_TRAP_LOG_N-1")
    t.emit("slli x5, x5, TRAPLOG_ENTRY_SHIFT")
    t.emit("LA(x4, rvtest_trap_log)", 2)
    t.emit("add x4, x4, x5")
    t.emit(f"LREG {reg}, ({word})*REGWIDTH(x4)")


def int_window(t: TestFile, mode: str, desc: str, n: int = 1, hs_sie: int = 1) -> str:
    """Wait 50 iterations in `mode` (S = HS-mode, with sstatus.SIE = hs_sie during the wait; U, VS, VU) inside a
    trap window that permits n traps. HS-mode's SIE and SPIE are cleared first. Returns the window label."""
    no_hs_sie(t)
    lab = t.label(f"int{mode}")
    t.allow(n)
    if mode == "S":
        t.emit(f"{lab}:", 0)
        if hs_sie:
            t.li("x7", SIE)
            t.emit(f"csrs {hex(SSTATUS)}, x7  // sstatus.SIE = 1")
        delay(t)
        t.li("x7", SIE)
        t.emit(f"csrc {hex(SSTATUS)}, x7  // sstatus.SIE = 0")
    else:
        t.enter(mode)
        t.emit(f"{lab}:", 0)
        delay(t)
        t.leave()
    return lab


def taken(t: TestFile, lab: str, mode: str, desc: str, seq: list[tuple[int, int]]) -> None:
    """Close the window and check the traps it took, in order: seq = [(cause code, handler mode 1 HS / 2 VS)].
    An empty seq means no interrupt. The last trap must come from `mode`."""
    if not seq:
        t.outcome("ok", lab, f"{desc}: no interrupt", epc=False)
        return
    if len(seq) == 1:
        code, hm = seq[0]
        t.outcome(
            icause(code),
            lab,
            f"{desc}: {NAME.get(code, code)} taken in {'VS' if hm == 2 else 'HS'}-mode",
            epc=False,
            origin=mode,
        )
        t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
        t.emit("andi x15, x15, 3")
        t.check("x15", hm, lab, f"{desc}: taken by the {'VS' if hm == 2 else 'HS'}-mode handler (2 VS, 1 HS)")
        return
    t.emit("AI_OUTCOME", 20)
    t.check("x13", len(seq), lab, f"{desc}: number of interrupts taken")
    names = ", ".join(NAME.get(c, str(c)) for c, _ in seq)
    for k, (code, hm) in enumerate(seq):
        back = len(seq) - 1 - k
        log_word(t, "x15", back, "TRAPLOG_CAUSE")
        t.check(
            "x15",
            icause(code),
            lab,
            f"{desc}: interrupt {k + 1} of {len(seq)} (order {names}) is {NAME.get(code, code)}",
        )
        log_word(t, "x15", back, "TRAPLOG_VECT")
        t.emit("andi x15, x15, 3")
        t.check("x15", hm, lab, f"{desc}: interrupt {k + 1} taken by the {'VS' if hm == 2 else 'HS'}-mode handler")


def eqb(t: TestFile, a: str, b: str) -> None:
    """x5 = (a == b)."""
    t.emit(f"xor x5, {a}, {b}")
    t.emit("seqz x5, x5")


def geilen_probe(t: TestFile, reg: str = "x9") -> None:
    """reg = hgeie after writing all ones (bits GEILEN:1); hgeie is restored to 0."""
    t.emit("li x7, -1")
    t.emit(f"csrw {hex(HGEIE)}, x7  // hgeie = all ones")
    rd(t, reg, HGEIE, "hgeie: bits GEILEN:1")
    t.emit(f"csrw {hex(HGEIE)}, x0  // hgeie = 0")


def vgein(t: TestFile, v: int) -> None:
    t.li("x7", 0x3F000)
    t.emit(f"csrc {hex(HSTATUS)}, x7  // hstatus.VGEIN = 0")
    if v:
        t.li("x7", v << 12)
        t.emit(f"csrs {hex(HSTATUS)}, x7  // hstatus.VGEIN = {v}")


def raise_gei(t: TestFile, gei: int, on: bool) -> None:
    t.emit(f"RVTEST_{'SET' if on else 'CLR'}_GUEST_EXT_INT_S({gei})", 120)


def expect_bits(t: TestFile, num: int, name: str, mask: int, value: int, lab: str, desc: str) -> None:
    rd(t, "x8", num, name)
    t.check_masked("x8", mask, value, lab, desc)


def here(t: TestFile, stem: str) -> str:
    lab = t.label(stem)
    t.emit(f"{lab}:", 0)
    return lab


def vs_alias_bits(i: int) -> tuple[int, int]:
    """(vsip bit position, hip bit position) for VS-level interrupt i (2, 6, 10), with the vsip_no_shift mutant."""
    return (i if MUT == "vsip_no_shift" else i - 1), i


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    tests += gen_regs()
    tests += gen_routing()
    tests += gen_alias()
    tests += gen_priority()
    tests += gen_m()
    tests += gen_gei()
    return tests


def gen_regs() -> list[TestFile]:
    tests = []

    # ---- hvip_sz_op ----
    t = new("hvip_sz_op")
    t.describe(
        source=HYP,
        rule_text="Register hvip is an HSXLEN-bit read/write register that a hypervisor can write to indicate "
        "virtual interrupts intended for VS-mode. Bits of hvip that are not writable are read-only zeros.",
        context="Bits 2, 6 and 10 (VSSIP, VSTIP, VSEIP) are writable (hvip_acc). Bits 13 and up may be writable "
        "with the AIA, so only bits 12:0 are checked. hie is 0, so nothing is taken.",
        plan="1. Write all ones: bits 12:0 read 0x444. Write zero: they read 0.\n"
        "2. Write each of bits 0 to 12 alone: it reads back only if it is 2, 6 or 10, and no other bit is set "
        "(a shifted or merged field shows up here).\n"
        "3. csrrw returns the old value, csrrs/csrrc change only the named bits.",
    )
    reset(t)
    lab = here(t, "ones")
    w(t, HVIP, "hvip", -1)
    exp = 0x446 if MUT == "hvip_extra_bit" else 0x444
    expect_bits(t, HVIP, "hvip", STD, exp, lab, "hvip after writing all ones (bits 12:0)")
    w(t, HVIP, "hvip", 0)
    expect_bits(t, HVIP, "hvip", STD, 0, lab, "hvip after writing zero (bits 12:0)")
    for b in range(13):
        lab = here(t, f"bit{b}")
        w(t, HVIP, "hvip", 1 << b)
        e = (1 << b) if b in (2, 6, 10) or (b == 1 and MUT == "hvip_extra_bit") else 0
        expect_bits(t, HVIP, "hvip", STD, e, lab, f"hvip after writing bit {b} alone")
    lab = here(t, "forms")
    w(t, HVIP, "hvip", 0x40)
    t.li("x6", 0x404)
    t.emit(f"csrrw x8, {hex(HVIP)}, x6  // hvip: swap")
    t.check_masked("x8", STD, 0x40, lab, "csrrw of hvip returns the old value (VSTIP)")
    t.li("x6", 0x40)
    t.emit(f"csrrs x8, {hex(HVIP)}, x6  // hvip: set VSTIP")
    t.check_masked("x8", STD, 0x404, lab, "csrrs of hvip returns the old value (VSEIP|VSSIP)")
    t.li("x6", 0x4)
    t.emit(f"csrrc x8, {hex(HVIP)}, x6  // hvip: clear VSSIP")
    expect_bits(t, HVIP, "hvip", STD, 0x440, lab, "hvip after set VSTIP and clear VSSIP")
    reset(t)
    tests.append(t)

    # ---- hvip_acc ----
    t = new("hvip_acc")
    t.describe(
        source=HYP,
        rule_text="The standard portion (bits 15:0) of hvip is formatted as shown in <<hvipreg-standard>>. Bits "
        "VSEIP, VSTIP, and VSSIP of hvip are writable. Setting VSEIP=1 in hvip asserts a VS-level external "
        "interrupt; setting VSTIP asserts a VS-level timer interrupt; and setting VSSIP asserts a VS-level software "
        "interrupt.",
        context="Asserting shows in hip (bits 2, 6, 10) and in mip read in M-mode, and makes the interrupt "
        "trappable. henvcfg.STCE is 0 (boot), so hip.VSTIP is hvip.VSTIP alone.",
        plan="1. For each of VSSIP, VSTIP, VSEIP alone: hvip bit set gives exactly that bit in hip (bits 12:0) and "
        "in mip (M-mode read); clearing it clears both.\n"
        "2. Each asserted interrupt, with hie enabling it and hideleg 0, is taken in HS-mode from VS-mode with "
        "cause 2, 6 or 10.",
    )
    reset(t)
    for nm, i in VS_INTS:
        lab = here(t, nm)
        w(t, HVIP, "hvip", 1 << i)
        expect_bits(t, HIP, "hip", STD, 1 << i, lab, f"hip after hvip = {nm}P only")
        m_read(t, "mip")
        t.check_masked("a0", 0x1444, 1 << i, lab, f"mip (M-mode) VS-level bits after hvip = {nm}P only")
        w(t, HVIP, "hvip", 0)
        expect_bits(t, HIP, "hip", STD, 0, lab, f"hip after clearing hvip.{nm}P")
    for nm, i in VS_INTS:
        w(t, HIE, "hie", 1 << i)
        w(t, HVIP, "hvip", 1 << i)
        lab = int_window(t, "VS", nm)
        taken(t, lab, "VS", f"hvip.{nm}P=1, hie.{nm}E=1, hideleg=0, VS-mode", [(i, 1)])
        reset(t)
    tests.append(t)

    # ---- hip_hie_sz_acc ----
    t = new("hip_hie_sz_acc")
    t.describe(
        source=HYP,
        rule_text="Registers hip and hie are HSXLEN-bit read/write registers that supplement HS-level's sip and "
        "sie respectively.",
        context="hie bits 2, 6 and 10 are writable; bit 12 (SGEIE) is writable when GEILEN > 0 (hie_acc), probed "
        "through hgeie. In hip only VSSIP (bit 2) is writable. Bits 13 and up are not checked.",
        plan="1. hie: write all ones, bits 12:0 read 0x1444 when GEILEN > 0, else 0x444 or 0x1444; write zero, they "
        "read 0.\n"
        "2. hip, with hvip = 0: write all ones, bits 12:0 read 0x004 (VSSIP only); write zero, they read 0.\n"
        "3. Read-write register: csrrw of hie returns the old value.",
    )
    reset(t)
    geilen_probe(t, "x9")
    t.emit("andi x9, x9, 2  // GEILEN > 0")
    lab = here(t, "hie")
    w(t, HIE, "hie", -1)
    rd(t, "x8", HIE, "hie")
    t.either(
        "x9",
        lambda: t.check_masked("x8", STD, 0x1444, lab, "hie after all ones, GEILEN > 0"),
        lambda: t.check_masked("x8", STD, [0x444, 0x1444], lab, "hie after all ones, GEILEN = 0"),
    )
    t.li("x6", 0x40)
    t.emit(f"csrrw x8, {hex(HIE)}, x6  // hie: swap")
    t.check_masked("x8", 0xEFF, 0x444, lab, "csrrw of hie returns the old value")
    expect_bits(t, HIE, "hie", STD, 0x40, lab, "hie after csrrw 0x40")
    w(t, HIE, "hie", 0)
    expect_bits(t, HIE, "hie", STD, 0, lab, "hie after writing zero")
    lab = here(t, "hip")
    w(t, HIP, "hip", -1)
    expect_bits(t, HIP, "hip", STD, 0x4, lab, "hip after writing all ones (hvip = 0): only VSSIP is writable")
    w(t, HIP, "hip", 0)
    expect_bits(t, HIP, "hip", STD, 0, lab, "hip after writing zero")
    reset(t)
    tests.append(t)

    # ---- hip_op ----
    t = new("hip_op")
    t.describe(
        source=HYP,
        rule_text="The hip register indicates pending VS-level and hypervisor-specific interrupts",
        context="S-level interrupts (SSI, STI, SEI) are indicated in sip, never in hip (sie_hip_hie_mutex).",
        plan="1. Make SSI (sip.SSIP), STI and SEI (mip.STIP, mip.SEIP through M-mode) pending one at a time: hip "
        "bits 12:0 stay 0.\n"
        "2. Make each VS-level interrupt pending through hvip: hip shows exactly its bit (2, 6, 10), and sip does "
        "not show it (sip bits 2, 6, 10 read 0).",
    )
    reset(t)
    for nm, how in (("SSIP", "sip"), ("STIP", "mip"), ("SEIP", "mip")):
        bit = {"SSIP": 2, "STIP": 0x20, "SEIP": 0x200}[nm]
        lab = here(t, nm)
        if how == "sip":
            cs(t, SIP, "sip", bit, True)
        else:
            t.tsbi_csr("SET", "MIP", imm=bit)
        expect_bits(t, SIP, "sip", bit, bit, lab, f"sip.{nm} is pending")
        expect_bits(t, HIP, "hip", STD, 0, lab, f"hip with only {nm} pending")
        if how == "sip":
            cs(t, SIP, "sip", bit, False)
        else:
            t.tsbi_csr("CLEAR", "MIP", imm=bit)
    for nm, i in VS_INTS:
        lab = here(t, nm)
        w(t, HVIP, "hvip", 1 << i)
        expect_bits(t, HIP, "hip", STD, 1 << i, lab, f"hip with only {nm} pending")
        expect_bits(t, SIP, "sip", 0x444, 0, lab, f"sip bits 2, 6, 10 with only {nm} pending")
    reset(t)
    tests.append(t)

    # ---- hie_op ----
    t = new("hie_op")
    t.describe(
        source=HYP,
        rule_text="hie contains enable bits for the same interrupts",
        context="A VS-level interrupt for HS-mode is enabled only by its hie bit: sie has no VS-level bits.",
        plan="For each VS-level interrupt pending in hvip, hideleg = 0, in VU-mode (always enabled globally):\n"
        "1. hie bit 0 and every sie bit set: not taken.\n"
        "2. hie bit 1: taken in HS-mode with cause 2, 6 or 10.\n"
        "3. Only another hie bit set: not taken.",
    )
    reset(t)
    for nm, i in VS_INTS:
        w(t, HVIP, "hvip", 1 << i)
        t.li("x7", 0x222)
        t.emit(f"csrs {hex(SIE_CSR)}, x7  // sie.SSIE/STIE/SEIE = 1")
        lab = int_window(t, "VU", nm)
        taken(
            t,
            lab,
            "VU",
            f"{nm} pending, hie.{nm}E=0, sie all set",
            [(i, 1)] if MUT == "hie_sie_shared" and i == 2 else [],
        )
        t.li("x7", 0x222)
        t.emit(f"csrc {hex(SIE_CSR)}, x7  // sie = 0")
        other = next(j for _, j in VS_INTS if j != i)
        w(t, HIE, "hie", 1 << other)
        lab = int_window(t, "VU", nm)
        taken(t, lab, "VU", f"{nm} pending, only hie bit {other} set", [])
        w(t, HIE, "hie", 1 << i)
        lab = int_window(t, "VU", nm)
        taken(t, lab, "VU", f"{nm} pending, hie.{nm}E=1", [(i, 1)])
        reset(t)
    tests.append(t)

    # ---- hie_acc ----
    t = new("hie_acc")
    t.describe(
        source=HYP,
        rule_text="A bit in hie shall be writable if the corresponding interrupt can ever become pending in hip. "
        "Bits of hie that are not writable shall be read-only zero.",
        context="VSSI, VSTI and VSEI can become pending (hvip), so hie bits 2, 6, 10 are writable. SGEI can become "
        "pending iff GEILEN > 0 (probed through hgeie). Every other bit of 12:0 is read-only zero: bits 1, 5, 9 "
        "are writable in sie (sie_hip_hie_mutex); 3, 7, 11 are M-level; 0, 4, 8 are reserved.",
        plan="1. Write each of bits 0 to 12 alone: bits 2, 6, 10 read back, bit 12 reads back when GEILEN > 0, "
        "others read 0 (bit 12 may read either when GEILEN = 0).\n"
        "2. Set and clear each of bits 2, 6, 10 with csrs/csrc: only that bit changes.",
    )
    reset(t)
    geilen_probe(t, "x9")
    t.emit("andi x9, x9, 2  // GEILEN > 0")
    for b in range(13):
        lab = here(t, f"bit{b}")
        w(t, HIE, "hie", 1 << b)
        if b == 12:
            rd(t, "x8", HIE, "hie")
            t.either(
                "x9",
                lambda lab=lab: t.check_masked("x8", STD, 0x1000, lab, "hie after writing bit 12, GEILEN > 0"),
                lambda lab=lab: t.check_masked("x8", STD, [0, 0x1000], lab, "hie after writing bit 12, GEILEN = 0"),
            )
        else:
            expect_bits(t, HIE, "hie", STD, (1 << b) if b in (2, 6, 10) else 0, lab, f"hie after writing bit {b} alone")
    w(t, HIE, "hie", 0)
    for nm, i in VS_INTS:
        lab = here(t, nm)
        cs(t, HIE, "hie", 1 << i, True)
        expect_bits(t, HIE, "hie", 0x444, 1 << i, lab, f"hie after csrs {nm}E")
        cs(t, HIE, "hie", 1 << i, False)
        expect_bits(t, HIE, "hie", 0x444, 0, lab, f"hie after csrc {nm}E")
    reset(t)
    tests.append(t)

    # ---- hip_acc ----
    t = new("hip_acc")
    t.describe(
        source=HYP,
        rule_text="If bit i of sie is read-only zero, the same bit in register hip may be writable or may be "
        "read-only. When bit i in hip is writable, a pending interrupt i can be cleared by writing 0 to this bit. If "
        "interrupt i can become pending in hip but bit i in hip is read-only, then either the interrupt can be "
        "cleared by clearing bit i of hvip, or the implementation must provide some other mechanism for clearing the "
        "pending interrupt (which may involve a call to the execution environment).",
        context="hip.VSSIP is writable (an alias of hvip.VSSIP, hip_vssip_vssie_op); hip.VSTIP and hip.VSEIP are "
        "read-only (hip_vstip_acc, hip_vseip_vseie_op) and are cleared through hvip.",
        plan="1. hvip.VSSIP = 1: writing 0 to hip.VSSIP (csrc, and csrw 0) clears the pending interrupt in hip and "
        "hvip.\n"
        "2. hvip.VSTIP = 1 (and VSEIP): csrc of the hip bit leaves it pending in hip and hvip; clearing the hvip bit "
        "clears it.\n"
        "3. A cleared VSSI is no longer taken: with hie.VSSIE=1, VU-mode takes no interrupt after hip.VSSIP is "
        "cleared.",
    )
    reset(t)
    for how in ("csrc", "csrw"):
        lab = here(t, f"vssip_{how}")
        w(t, HVIP, "hvip", 4)
        if how == "csrc":
            cs(t, HIP, "hip", 4, False)
        else:
            w(t, HIP, "hip", 0)
        expect_bits(t, HIP, "hip", 0x444, 0, lab, f"hip.VSSIP after {how} of hip (pending in hvip before)")
        expect_bits(t, HVIP, "hvip", 0x444, 0, lab, f"hvip.VSSIP after {how} of hip")
    w(t, HIE, "hie", 4)
    lab = int_window(t, "VU", "VSSI")
    taken(t, lab, "VU", "hip.VSSIP cleared through hip, hie.VSSIE=1", [])
    w(t, HIE, "hie", 0)
    ro = 0x440 if MUT != "hip_vstip_writable" else 0
    for nm, i in VS_INTS[1:]:
        lab = here(t, nm)
        w(t, HVIP, "hvip", 1 << i)
        cs(t, HIP, "hip", 1 << i, False)
        expect_bits(t, HIP, "hip", 1 << i, (1 << i) & ro, lab, f"hip.{nm}P after csrc of hip (read-only)")
        expect_bits(t, HVIP, "hvip", 1 << i, (1 << i) & ro, lab, f"hvip.{nm}P after csrc of hip")
        cs(t, HVIP, "hvip", 1 << i, False)
        expect_bits(t, HIP, "hip", 1 << i, 0, lab, f"hip.{nm}P after clearing hvip.{nm}P")
    reset(t)
    tests.append(t)

    # ---- sie_hip_hie_mutex ----
    t = new("sie_hip_hie_mutex")
    t.describe(
        source=HYP,
        rule_text="For each writable bit in sie, the corresponding bit shall be read-only zero in both hip and hie. "
        "Hence, the nonzero bits in sie and hie are always mutually exclusive, and likewise for sip and hip.",
        context="Writable masks are found by writing all ones and reading back; sstatus.SIE is 0 throughout and "
        "every register is restored to 0. All bits of the registers are compared, not only 12:0.",
        plan="1. W(sie) = sie after writing all ones; W(hie), W(hip) likewise (hvip = 0). W(sie) & W(hie) = 0 and "
        "W(sie) & W(hip) = 0.\n"
        "2. W(sip) = sip after writing all ones; W(sip) & W(hip) = 0 and W(sip) & W(hie) = 0.\n"
        "3. sie has its writable S-level bits (SSIE, STIE, SEIE: bits 1, 5, 9 all set), so the check is not "
        "vacuous.",
    )
    reset(t)
    t.emit("li x7, -1")
    for num, nm, reg in ((SIE_CSR, "sie", "x6"), (HIE, "hie", "x8"), (HIP, "hip", "x9"), (SIP, "sip", "x1")):
        t.emit(f"csrw {hex(num)}, x7  // {nm} = all ones")
        rd(t, reg, num, nm)
        t.emit(f"csrw {hex(num)}, x0  // {nm} = 0")
    lab = here(t, "mutex")
    t.check_masked("x6", 0x222, 0x222, lab, "sie bits 1, 5, 9 are writable")
    for a, b, d in (
        ("x6", "x8", "W(sie) & W(hie)"),
        ("x6", "x9", "W(sie) & W(hip)"),
        ("x1", "x9", "W(sip) & W(hip)"),
        ("x1", "x8", "W(sip) & W(hie)"),
    ):
        t.emit(f"and x5, {a}, {b}")
        t.check("x5", 0, lab, f"{d} is zero")
    reset(t)
    tests.append(t)

    # ---- hideleg_sz_acc / hideleg_acc ----
    t = new("hideleg_sz_acc")
    t.describe(
        source=HYP,
        rule_text="Register hideleg is an HSXLEN-bit read/write register, formatted as shown in <<norm:hideleg_img>>.",
        context="Bits 2, 6, 10 are writable; 1, 5, 9, 12 are read-only zero (hideleg_acc); bits 0, 3, 4, 7, 8, 11 "
        "are zero because mideleg has them zero or they are reserved (mideleg_hroz). Bit 13 depends on "
        "Shlcofideleg (vsip_vsie_lcofi) and bits 14 and up on the AIA, so only bits 12:0 are checked.",
        plan="1. Write all ones: bits 12:0 read 0x444; write zero: 0.\n"
        "2. Every CSR instruction form on hideleg: csrrw returns the old value; csrrs/csrrc change only the named "
        "writable bits; csrrwi/csrrsi/csrrci write the immediate (bit 2 of 0x15 is VSSI).",
    )
    reset(t)
    lab = here(t, "ones")
    w(t, HIDELEG, "hideleg", -1)
    e = 0x666 if MUT == "hideleg_s_bits_writable" else 0x444
    expect_bits(t, HIDELEG, "hideleg", STD, e, lab, "hideleg after writing all ones (bits 12:0)")
    w(t, HIDELEG, "hideleg", 0)
    expect_bits(t, HIDELEG, "hideleg", STD, 0, lab, "hideleg after writing zero")
    lab = here(t, "forms")
    w(t, HIDELEG, "hideleg", 0x400)
    t.li("x6", 0x44)
    t.emit(f"csrrw x8, {hex(HIDELEG)}, x6  // hideleg: swap")
    t.check_masked("x8", STD, 0x400, lab, "csrrw of hideleg returns the old value")
    t.li("x6", 0x400)
    t.emit(f"csrrs x8, {hex(HIDELEG)}, x6  // hideleg: set bit 10")
    t.check_masked("x8", STD, 0x44, lab, "csrrs of hideleg returns the old value")
    t.li("x6", 0x40)
    t.emit(f"csrrc x8, {hex(HIDELEG)}, x6  // hideleg: clear bit 6")
    expect_bits(t, HIDELEG, "hideleg", STD, 0x404, lab, "hideleg after csrrs 0x400, csrrc 0x40")
    t.emit(f"csrrwi x8, {hex(HIDELEG)}, 0x15  // hideleg = 0x15")
    expect_bits(t, HIDELEG, "hideleg", STD, 0x4, lab, "hideleg after csrrwi 0x15 (bit 2 only)")
    t.emit(f"csrrci x8, {hex(HIDELEG)}, 0x4  // hideleg &= ~4")
    t.check_masked("x8", STD, 0x4, lab, "csrrci of hideleg returns the old value")
    t.emit(f"csrrsi x8, {hex(HIDELEG)}, 0  // read")
    t.check_masked("x8", STD, 0, lab, "hideleg after csrrci 4")
    reset(t)
    tests.append(t)

    t = new("hideleg_acc")
    t.describe(
        source=HYP,
        rule_text="Among bits 15:0 of hideleg, bits 10, 6, and 2 (corresponding to the standard VS-level "
        "interrupts) are writable, and bits 12, 9, 5, and 1 (corresponding to the standard S-level interrupts) are "
        "read-only zeros.",
        context="Bit 12 (SGEI) is never delegated to VS-mode. Bit 13 (LCOFI) is covered by vsip_vsie_lcofi.",
        plan="1. Write each of bits 1, 2, 5, 6, 9, 10, 12 alone: bits 2, 6, 10 read back alone, the others read 0.\n"
        "2. Set each writable bit with csrs while the other two are set, and clear it with csrc: only it changes.\n"
        "3. Writing ones to bits 1, 5, 9, 12 with csrs leaves hideleg unchanged.",
    )
    reset(t)
    for b in (1, 2, 5, 6, 9, 10, 12):
        lab = here(t, f"bit{b}")
        w(t, HIDELEG, "hideleg", 1 << b)
        e = (1 << b) if b in (2, 6, 10) or (MUT == "hideleg_s_bits_writable" and b in (1, 5, 9)) else 0
        expect_bits(t, HIDELEG, "hideleg", 0xFFFF, e, lab, f"hideleg after writing bit {b} alone (bits 15:0)")
    for nm, i in VS_INTS:
        lab = here(t, nm)
        w(t, HIDELEG, "hideleg", 0x444 & ~(1 << i))
        cs(t, HIDELEG, "hideleg", 1 << i, True)
        expect_bits(t, HIDELEG, "hideleg", 0xFFFF, 0x444, lab, f"hideleg after csrs bit {i}")
        cs(t, HIDELEG, "hideleg", 1 << i, False)
        expect_bits(t, HIDELEG, "hideleg", 0xFFFF, 0x444 & ~(1 << i), lab, f"hideleg after csrc bit {i}")
    lab = here(t, "sbits")
    w(t, HIDELEG, "hideleg", 0)
    cs(t, HIDELEG, "hideleg", 0x1222, True)
    e = 0x222 if MUT == "hideleg_s_bits_writable" else 0
    expect_bits(t, HIDELEG, "hideleg", 0xFFFF, e, lab, "hideleg after csrs of bits 1, 5, 9, 12")
    reset(t)
    tests.append(t)

    # ---- hip_vssip_vssie_op ----
    t = new("hip_vssip_vssie_op")
    t.describe(
        source=HYP,
        rule_text="Bits hip.VSSIP and hie.VSSIE are the interrupt-pending and interrupt-enable bits for VS-level "
        "software interrupts. VSSIP in hip is an alias (writable) of the same bit in hvip.",
        plan="1. csrs/csrc of hip.VSSIP set and clear hvip.VSSIP; csrs/csrc of hvip.VSSIP show in hip.\n"
        "2. A csrw of hip with all ones changes only VSSIP in hvip (VSTIP and VSEIP of hvip keep their values, 0 "
        "and 1), and a csrw of hip with 0 clears only VSSIP.\n"
        "3. With hie.VSSIE=1 and hideleg = 0, a VSSI set through hip is taken in HS-mode from VS-mode (cause 2); "
        "with hie.VSSIE=0 it is not.",
    )
    reset(t)
    lab = here(t, "alias")
    cs(t, HIP, "hip", 4, True)
    expect_bits(t, HVIP, "hvip", 0x444, 4, lab, "hvip after csrs hip.VSSIP")
    cs(t, HIP, "hip", 4, False)
    expect_bits(t, HVIP, "hvip", 0x444, 0, lab, "hvip after csrc hip.VSSIP")
    cs(t, HVIP, "hvip", 4, True)
    expect_bits(t, HIP, "hip", 0x444, 4, lab, "hip after csrs hvip.VSSIP")
    cs(t, HVIP, "hvip", 4, False)
    expect_bits(t, HIP, "hip", 0x444, 0, lab, "hip after csrc hvip.VSSIP")
    lab = here(t, "csrw")
    w(t, HVIP, "hvip", 0x400)
    w(t, HIP, "hip", -1)
    e = 0x444 if MUT == "hip_write_clobbers_hvip" else 0x404
    expect_bits(t, HVIP, "hvip", 0x444, e, lab, "hvip after csrw hip = all ones (hvip was VSEIP only)")
    w(t, HIP, "hip", 0)
    e = 0 if MUT == "hip_write_clobbers_hvip" else 0x400
    expect_bits(t, HVIP, "hvip", 0x444, e, lab, "hvip after csrw hip = 0 (VSEIP keeps its value)")
    w(t, HVIP, "hvip", 0)
    cs(t, HIP, "hip", 4, True)
    lab = int_window(t, "VS", "VSSI")
    taken(t, lab, "VS", "hip.VSSIP set through hip, hie.VSSIE=0", [])
    w(t, HIE, "hie", 4)
    lab = int_window(t, "VS", "VSSI")
    taken(t, lab, "VS", "hip.VSSIP set through hip, hie.VSSIE=1", [(2, 1)])
    reset(t)
    tests.append(t)

    # ---- hip_vstip_vstie_acc_op / hip_vstip_defined_v0 ----
    t = new("hip_vstip_vstie_acc_op")
    t.describe(
        source=HYP,
        rule_text="Bits hip[vstip] and hie[vstie] are the interrupt-pending and interrupt-enable bits for VS-level "
        "timer interrupts.",
        context="This test uses hvip.VSTIP as the source; vstimecmp (Sstc) is covered by the Sstc suite. henvcfg.STCE "
        "is 0 at boot.",
        plan="1. hvip.VSTIP = 1 sets hip.VSTIP; hie.VSTIE is writable.\n"
        "2. hideleg[6] = 0: VSTI is taken in HS-mode from VS, VU and U-mode when hie.VSTIE = 1 (cause 6), and not "
        "when hie.VSTIE = 0.\n"
        "3. hideleg[6] = 1: VSTI is taken in VS-mode with vsstatus.SIE = 1 (cause 5), not in HS-mode.",
    )
    reset(t)
    lab = here(t, "pend")
    w(t, HVIP, "hvip", 0x40)
    expect_bits(t, HIP, "hip", 0x40, 0x40, lab, "hip.VSTIP with hvip.VSTIP = 1")
    w(t, HIE, "hie", 0x40)
    expect_bits(t, HIE, "hie", 0x40, 0x40, lab, "hie.VSTIE after writing it")
    for mode in ("VS", "VU", "U"):
        w(t, HVIP, "hvip", 0x40)
        w(t, HIE, "hie", 0x40)
        lab = int_window(t, mode, "VSTI")
        taken(t, lab, mode, f"VSTI pending and enabled, hideleg[6]=0, {mode}-mode", [(6, 1)])
    w(t, HVIP, "hvip", 0x40)
    w(t, HIE, "hie", 0)
    lab = int_window(t, "VS", "VSTI")
    taken(t, lab, "VS", "VSTI pending, hie.VSTIE=0", [])
    w(t, HIDELEG, "hideleg", 0x40)
    w(t, HIE, "hie", 0x40)
    cs(t, VSSTATUS, "vsstatus.SIE", SIE, True)
    lab = int_window(t, "VS", "VSTI")
    taken(t, lab, "VS", "VSTI pending, hideleg[6]=1, vsstatus.SIE=1", [(5, 2)])
    reset(t)
    tests.append(t)

    t = new("hip_vstip_defined_v0")
    t.describe(
        source=HYP,
        rule_text="The hip[vstip] bit remains defined while V=0 as well as V=1.",
        context="Read in HS-mode (V=0) and through mip in M-mode, with hvip.VSTIP as the source.",
        plan="1. In HS-mode, hip.VSTIP follows hvip.VSTIP: 1, then 0, then 1.\n"
        "2. mip.VSTIP read in M-mode agrees.\n"
        "3. After a VS-mode excursion, hip.VSTIP still reads 1 in HS-mode.",
    )
    reset(t)
    for v in (1, 0, 1):
        lab = here(t, f"v{v}")
        w(t, HVIP, "hvip", 0x40 * v)
        expect_bits(t, HIP, "hip", 0x40, 0x40 * v, lab, f"hip.VSTIP in HS-mode with hvip.VSTIP = {v}")
        m_read(t, "mip")
        t.check_masked("a0", 0x40, 0x40 * v, lab, f"mip.VSTIP in M-mode with hvip.VSTIP = {v}")
    lab = t.window("VS", ["nop"], "ok", "VS-mode excursion")
    expect_bits(t, HIP, "hip", 0x40, 0x40, lab, "hip.VSTIP in HS-mode after a VS-mode excursion")
    reset(t)
    tests.append(t)

    # ---- hip_vseip_vseie_op (hvip part; the hgeip part is in gen_gei) ----
    return tests


def gen_routing() -> list[TestFile]:
    tests = []

    # ---- hideleg_hs ----
    t = new("hideleg_hs")
    t.describe(
        source=HYP,
        rule_text="An interrupt i will trap to HS-mode whenever all of the following are true: (a) either the "
        "current operating mode is HS-mode and the SIE bit in the sstatus register is set, or the current operating "
        "mode has less privilege than HS-mode; (b) bit i is set in both sip and sie, or in both hip and hie; and (c) "
        "bit i is not set in hideleg.",
        context="Each VS-level interrupt is made pending through hvip. The modes below HS are VS, VU and U. "
        "HS-mode's SIE and SPIE are cleared before each window, so sstatus.SIE is 0 while VS/VU/U runs.",
        plan="For VSSI, VSTI and VSEI:\n"
        "1. HS-mode, hie bit 1, hideleg bit 0: taken iff sstatus.SIE = 1 (cause 2, 6, 10).\n"
        "2. VS-mode with vsstatus.SIE = 0, VU-mode and U-mode, sstatus.SIE = 0: taken in HS-mode.\n"
        "3. hie bit 0 (and sie's S-level bits set): not taken in HS-mode with SIE = 1 or in VS-mode.\n"
        "4. hideleg bit 1: not taken in HS-mode with SIE = 1, nor in U-mode (VS-level interrupts delegated to VS are "
        "taken only while V = 1).",
    )
    reset(t)
    for nm, i in VS_INTS:

        def setup(en: int = 1, deleg: int = 0, i: int = i) -> None:
            w(t, HIDELEG, "hideleg", deleg << i)
            w(t, HIE, "hie", en << i)
            w(t, HVIP, "hvip", 1 << i)

        t.comment(f"---- {nm} ----")
        for sie_v in (0, 1):
            setup()
            lab = int_window(t, "S", nm, hs_sie=sie_v)
            taken(t, lab, "S", f"{nm}, HS-mode, sstatus.SIE={sie_v}", [(i, 1)] if sie_v else [])
        for mode in ("VS", "VU", "U"):
            setup()
            lab = int_window(t, mode, nm)
            exp = [] if (MUT == "hs_needs_sie_from_v" and mode in ("VS", "VU")) else [(i, 1)]
            taken(t, lab, mode, f"{nm}, {mode}-mode, sstatus.SIE=0", exp)
        setup(en=0)
        t.li("x7", 0x222)
        t.emit(f"csrs {hex(SIE_CSR)}, x7  // sie S-level bits")
        for mode in ("S", "VS"):
            lab = int_window(t, mode, nm)
            taken(t, lab, mode, f"{nm}, hie bit 0, {mode}-mode", [])
        t.li("x7", 0x222)
        t.emit(f"csrc {hex(SIE_CSR)}, x7")
        for mode in ("S", "U"):
            setup(deleg=1)
            lab = int_window(t, mode, nm)
            exp = [(i, 1)] if (MUT == "deleg_taken_in_hs" and mode == "S") else []
            taken(t, lab, mode, f"{nm}, hideleg bit 1, {mode}-mode", exp)
        reset(t)
    tests.append(t)

    # ---- hideleg_op ----
    t = new("hideleg_op")
    t.describe(
        source=HYP,
        rule_text="An interrupt that has been delegated to HS-mode (using mideleg) is further delegated to VS-mode "
        "if the corresponding hideleg bit is set.",
        context="mideleg bits 2, 6, 10 are read-only one, so every VS-level interrupt reaches HS-mode delegation. A "
        "delegated interrupt is enabled by vsie (alias of hie) and, in VS-mode, by vsstatus.SIE; in VU-mode it is "
        "always globally enabled. Interrupts for a more privileged mode are taken first (machine.adoc: interrupts "
        "for higher-privilege modes are serviced before those for lower-privilege modes).",
        plan="For VSSI, VSTI and VSEI with hideleg bit 1 and hie bit 1:\n"
        "1. VS-mode, vsstatus.SIE = 1: taken by the VS-mode handler (xPP/xPV record VS).\n"
        "2. VS-mode, vsstatus.SIE = 0: not taken.\n"
        "3. VU-mode, vsstatus.SIE = 0: taken by the VS-mode handler (from VU).\n"
        "4. Mixed destinations in VS-mode with vsstatus.SIE = 1: VSSI delegated and VSTI not, both pending: VSTI is "
        "taken in HS-mode first, then VSSI in VS-mode.",
    )
    reset(t)
    for nm, i in VS_INTS:
        t.comment(f"---- {nm} ----")
        for mode, vsie in (("VS", 1), ("VS", 0), ("VU", 0)):
            w(t, HIDELEG, "hideleg", 1 << i)
            w(t, HIE, "hie", 1 << i)
            w(t, HVIP, "hvip", 1 << i)
            cs(t, VSSTATUS, "vsstatus.SIE", SIE, bool(vsie))
            lab = int_window(t, mode, nm)
            vu_taken = MUT != "vu_needs_sie"  # VU-mode ignores vsstatus.SIE
            exp = [(i - 1, 2)] if (vsie if mode == "VS" else vu_taken) else []
            if exp and MUT == "deleg_routes_to_hs_from_vs":
                exp = [(i, 1)]
            if exp and MUT == "no_cause_translation":
                exp = [(i, 2)]
            taken(t, lab, mode, f"{nm} delegated, {mode}-mode, vsstatus.SIE={vsie}", exp)
            reset(t)
    w(t, HIDELEG, "hideleg", 0x4)
    w(t, HIE, "hie", 0x44)
    w(t, HVIP, "hvip", 0x44)
    cs(t, VSSTATUS, "vsstatus.SIE", SIE, True)
    lab = int_window(t, "VS", "mixed", n=2)
    taken(t, lab, "VS", "VSSI delegated and VSTI not, both pending in VS-mode", [(6, 1), (1, 2)])
    reset(t)
    tests.append(t)

    # ---- hideleg_trans ----
    t = new("hideleg_trans")
    t.describe(
        source=HYP,
        rule_text="When a virtual supervisor external interrupt (code 10) is delegated to VS-mode, it is "
        "automatically translated by the machine into a supervisor external interrupt (code 9) for VS-mode, "
        "including the value written to vscause on an interrupt trap. Likewise, a virtual supervisor timer interrupt "
        "(6) is translated into a supervisor timer interrupt (5) for VS-mode, and a virtual supervisor software "
        "interrupt (2) is translated into a supervisor software interrupt (1) for VS-mode.",
        context="The trap log holds vscause and vstval of each VS-mode trap. With vstvec in Vectored mode (when "
        "vstvec accepts it, probed), an interrupt enters at BASE + 4 x cause, and the framework's trampoline records "
        "the entry it came through (bits 10:6 of the log's first word, (offset x 3) >> 5 where offset = "
        "4 x XLEN + 12 x (vector + 1)); the vector must be the translated cause. RV64 records only vectors 1 and 5 "
        "unambiguously in five bits, so vector 9 (VSEI) is not checked.",
        plan="1. Direct mode: each of VSSI, VSTI, VSEI delegated and taken in VS-mode reports vscause = interrupt | "
        "1, 5, 9 and vstval = 0.\n"
        "2. Inside VS-mode, with the interrupt pending and vsstatus.SIE = 0, a read of sip shows bit 1, 5 or 9, not "
        "bit 2, 6 or 10.\n"
        "3. Vectored vstvec (when it accepts Vectored with the same BASE): VSSI and VSTI enter through vectors 1 and 5.",
    )
    reset(t)
    for nm, i in VS_INTS:
        w(t, HIDELEG, "hideleg", 1 << i)
        w(t, HIE, "hie", 1 << i)
        w(t, HVIP, "hvip", 1 << i)
        lab = t.window("VS", [f"csrr x8, {hex(SIP)}  // sip (V=1: vsip)"], "ok", f"read sip with {nm} pending")
        vb, _ = vs_alias_bits(i)
        t.check_masked("x8", STD, 1 << vb, lab, f"VS-mode sip with {nm} pending and delegated")
        cs(t, VSSTATUS, "vsstatus.SIE", SIE, True)
        lab = int_window(t, "VS", nm)
        code = i if MUT == "no_cause_translation" else i - 1
        taken(t, lab, "VS", f"{nm} delegated to VS-mode", [(code, 2)])
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.check("x15", 0, lab, f"{nm} delegated to VS-mode: vstval is 0")
        reset(t)
    # vectored
    t.comment("vectored vstvec: probe Vectored mode with the same BASE")
    t.emit(f"csrr x6, {hex(VSTVEC)}  // vstvec")
    t.emit("ori x7, x6, 1")
    t.emit(f"csrw {hex(VSTVEC)}, x7")
    t.emit(f"csrr x8, {hex(VSTVEC)}")
    t.emit("xor x1, x8, x7")
    t.emit("seqz x1, x1  // x1 = Vectored accepted with the same BASE")
    t.emit(f"csrw {hex(VSTVEC)}, x6  // restore")

    def vectored() -> None:
        for nm, i in VS_INTS:
            vec = i if MUT == "vector_untranslated" else i - 1

            def field(xlen: int, v: int) -> int:
                off = 4 * xlen + 12 * (v + 1)
                return ((off * 3) >> 5) & 0x1F

            if i == 10:
                continue  # RV64 cannot represent vector 9 in five bits; RV32 case below
            t.emit(f"csrr x6, {hex(VSTVEC)}")
            t.emit("ori x6, x6, 1")
            t.emit(f"csrw {hex(VSTVEC)}, x6  // vstvec Vectored")
            w(t, HIDELEG, "hideleg", 1 << i)
            w(t, HIE, "hie", 1 << i)
            w(t, HVIP, "hvip", 1 << i)
            cs(t, VSSTATUS, "vsstatus.SIE", SIE, True)
            lab = int_window(t, "VS", nm)
            taken(t, lab, "VS", f"{nm} delegated, vstvec Vectored", [(i - 1, 2)])
            t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
            t.emit("srli x15, x15, 6")
            t.emit("andi x15, x15, 0x1F")
            t.check(
                "x15",
                X(field(32, vec), field(64, vec)),
                lab,
                f"{nm} delegated, vstvec Vectored: entered through vector {i - 1} (trampoline index field)",
            )
            t.emit(f"csrr x6, {hex(VSTVEC)}")
            t.emit("andi x6, x6, -4")
            t.emit(f"csrw {hex(VSTVEC)}, x6  // vstvec Direct")
            reset(t)

    t.either("x1", vectored, lambda: None)
    tests.append(t)
    return tests


def gen_alias() -> list[TestFile]:
    tests = []
    for nm, i, rule, sname in (
        ("VSSI", 2, "vsip_vsie_ssi", "SSIP"),
        ("VSTI", 6, "vsip_vsie_sti", "STIP"),
        ("VSEI", 10, "vsip_vsie_sei", "SEIP"),
    ):
        vb, _ = vs_alias_bits(i)
        t = new(rule)
        sie_name = sname[:-1] + "E"
        t.describe(
            source=HYP,
            rule_text=f"When bit {i} of hideleg is zero, vsip.{sname} and vsie.{sie_name} are read-only zeros. Else, "
            f"vsip.{sname} and vsie.{sie_name} are aliases of hip.{nm}P and hie.{nm}E.",
            context=f"vsip.{sname} and vsie.{sie_name} are bit {i - 1}; hip.{nm}P and hie.{nm}E are bit {i}. "
            + (
                "hip.VSSIP is writable, so vsip.SSIP is writable when aliased. "
                if i == 2
                else f"hip.{nm}P is read-only, so vsip.{sname} is read-only. "
            )
            + "Accessed as vsip/vsie from HS-mode and as sip/sie from VS-mode.",
            plan=f"1. hideleg bit {i} = 0: with hvip.{nm}P = 1 and hie.{nm}E = 1, vsip and vsie read 0 in bits 12:0; "
            f"setting vsie.{sie_name} (and vsip.{sname}) leaves hie (and hvip) unchanged and the bits still read 0.\n"
            f"2. hideleg bit {i} = 1: vsip bits 12:0 read exactly bit {i - 1} when hvip.{nm}P = 1 and 0 when it is 0; "
            f"vsie follows hie.{nm}E the same way.\n"
            f"3. hideleg bit {i} = 1: csrs/csrc of vsie.{sie_name} set and clear hie.{nm}E; "
            + (
                "csrs/csrc of vsip.SSIP set and clear hvip.VSSIP.\n"
                if i == 2
                else f"csrs of vsip.{sname} with hvip.{nm}P = 0 leaves it 0.\n"
            )
            + f"4. hideleg = bit {i} only: csrw vsie = all ones sets exactly hie bit {i}, and csrw vsip = all ones sets "
            + ("exactly hvip.VSSIP " if i == 2 else "no hvip bit ")
            + "(writes to vsip/vsie bits 2, 6, 10 must not reach hip/hie: "
            "https://gitlab.com/qemu-project/qemu/-/work_items/4590).\n"
            + f"5. From VS-mode with hideleg bit {i} = 1 and vsstatus.SIE = 0: sip and sie read the aliased bits, and a "
            f"VS-mode write of sie.{sie_name} lands in hie.{nm}E.",
        )
        reset(t)
        ig = MUT == "vsip_ignores_hideleg"
        lab = here(t, "deleg0")
        w(t, HVIP, "hvip", 1 << i)
        w(t, HIE, "hie", 1 << i)
        expect_bits(t, VSIP, "vsip", STD, (1 << vb) if ig else 0, lab, f"vsip with hideleg[{i}]=0, hvip.{nm}P=1")
        expect_bits(t, VSIE, "vsie", STD, (1 << vb) if ig else 0, lab, f"vsie with hideleg[{i}]=0, hie.{nm}E=1")
        w(t, HIE, "hie", 0)
        cs(t, VSIE, "vsie", 1 << (i - 1), True)
        expect_bits(
            t,
            HIE,
            "hie",
            STD,
            (1 << i) if ig and MUT != "vsip_no_shift" else 0,
            lab,
            f"hie after setting vsie bit {i - 1} with hideleg[{i}]=0",
        )
        if i == 2:
            w(t, HVIP, "hvip", 0)
            cs(t, VSIP, "vsip", 2, True)
            expect_bits(
                t,
                HVIP,
                "hvip",
                STD,
                4 if ig and MUT != "vsip_no_shift" else 0,
                lab,
                "hvip after setting vsip.SSIP with hideleg[2]=0",
            )
        reset(t)
        w(t, HIDELEG, "hideleg", 1 << i)
        for p in (1, 0):
            lab = here(t, f"pend{p}")
            w(t, HVIP, "hvip", p << i)
            expect_bits(t, VSIP, "vsip", STD, p << vb, lab, f"vsip with hideleg[{i}]=1, hvip.{nm}P={p}")
            w(t, HIE, "hie", p << i)
            expect_bits(t, VSIE, "vsie", STD, p << vb, lab, f"vsie with hideleg[{i}]=1, hie.{nm}E={p}")
        lab = here(t, "wr")
        cs(t, VSIE, "vsie", 1 << vb, True)
        expect_bits(t, HIE, "hie", STD, 1 << i, lab, f"hie after csrs vsie bit {vb}")
        cs(t, VSIE, "vsie", 1 << vb, False)
        expect_bits(t, HIE, "hie", STD, 0, lab, f"hie after csrc vsie bit {vb}")
        cs(t, VSIP, "vsip", 1 << vb, True)
        expect_bits(t, HVIP, "hvip", STD, (1 << i) if i == 2 else 0, lab, f"hvip after csrs vsip bit {vb}")
        if i == 2:
            cs(t, VSIP, "vsip", 1 << vb, False)
            expect_bits(t, HVIP, "hvip", STD, 0, lab, f"hvip after csrc vsip bit {vb}")
        lab = here(t, "ones")
        w(t, HIE, "hie", 0)
        w(t, HVIP, "hvip", 0)
        w(t, VSIE, "vsie", -1)
        expect_bits(t, HIE, "hie", STD, 1 << i, lab, f"hie after csrw vsie = all ones with hideleg = bit {i} only")
        w(t, VSIE, "vsie", 0)
        w(t, VSIP, "vsip", -1)
        expect_bits(
            t,
            HVIP,
            "hvip",
            STD,
            (1 << i) if i == 2 else 0,
            lab,
            f"hvip after csrw vsip = all ones with hideleg = bit {i} only",
        )
        w(t, VSIP, "vsip", 0)
        # VS-mode view
        w(t, HVIP, "hvip", 1 << i)
        w(t, HIE, "hie", 1 << i)
        lab = t.window(
            "VS",
            [f"csrr x8, {hex(SIP)}  // sip (vsip)", f"csrr x9, {hex(SIE_CSR)}  // sie (vsie)"],
            "ok",
            "VS-mode reads of sip and sie",
        )
        t.check_masked("x8", STD, 1 << vb, lab, f"VS-mode sip with hideleg[{i}]=1, hvip.{nm}P=1")
        t.check_masked("x9", STD, 1 << vb, lab, f"VS-mode sie with hideleg[{i}]=1, hie.{nm}E=1")
        w(t, HVIP, "hvip", 0)
        w(t, HIE, "hie", 0)
        t.li("x6", 1 << (i - 1))
        lab = t.window("VS", [f"csrs {hex(SIE_CSR)}, x6  // sie (vsie) bit {i - 1}"], "ok", "VS-mode write of sie")
        expect_bits(
            t,
            HIE,
            "hie",
            STD,
            (1 << i) if MUT != "vsip_no_shift" else 0,
            lab,
            f"hie after a VS-mode csrs of sie bit {i - 1}",
        )
        reset(t)
        tests.append(t)

    # ---- vsip_vsie_sz_acc_op ----
    t = new("vsip_vsie_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The vsip and vsie registers are VSXLEN-bit read/write registers that are VS-mode's versions of "
        "supervisor CSRs sip and sie, formatted as shown in <<norm:vsip_img>> and <<norm:vsie_img>> respectively. "
        "When V=1, vsip and vsie substitute for the usual sip and sie, so instructions that normally read or modify "
        "sip/sie actually access vsip/vsie instead. However, interrupts directed to HS-level continue to be indicated "
        "in the HS-level sip register, not in vsip, when V=1.",
        context=ISSUE_ALIAS + " HS-level interrupts used here: SSI (sip.SSIP) and STI (mip.STIP through M-mode), "
        "with sie bits 0 so HS-mode takes nothing.",
        plan="1. hideleg = 0x444, hvip = 0: HS-level SSIP and STIP pending: a VS-mode read of sip returns 0 in bits "
        "12:0 (not HS-mode's sip), while HS-mode's sip shows them.\n"
        "2. A VS-mode csrrw of sie with 0x222 makes hie 0x444 and leaves HS-mode's sie 0; a VS-mode csrrw of sie "
        "with 0 returns 0x222 and clears hie.\n"
        "3. A VS-mode csrrs of sip with 0x2 sets hvip.VSSIP and not HS-mode's sip.SSIP (cleared beforehand).",
    )
    reset(t)
    w(t, HIDELEG, "hideleg", 0x444)
    cs(t, SIP, "sip", 2, True)
    t.tsbi_csr("SET", "MIP", imm=0x20)
    lab = t.window("VS", [f"csrr x8, {hex(SIP)}  // sip (vsip)"], "ok", "VS-mode read of sip")
    t.check_masked("x8", STD, 0, lab, "VS-mode sip with HS-level SSI and STI pending (they stay in HS sip)")
    expect_bits(t, SIP, "sip", 0x22, 0x22, lab, "HS-mode sip shows SSIP and STIP")
    cs(t, SIP, "sip", 2, False)
    t.tsbi_csr("CLEAR", "MIP", imm=0x20)
    t.li("x6", 0x222)
    lab = t.window("VS", [f"csrrw x8, {hex(SIE_CSR)}, x6  // sie (vsie)"], "ok", "VS-mode csrrw of sie")
    expect_bits(t, HIE, "hie", STD, 0x444, lab, "hie after a VS-mode write of sie = 0x222")
    expect_bits(t, SIE_CSR, "sie", STD, 0, lab, "HS-mode sie after a VS-mode write of sie")
    lab = t.window("VS", [f"csrrw x8, {hex(SIE_CSR)}, x0  // sie (vsie)"], "ok", "VS-mode csrrw of sie with 0")
    t.check_masked("x8", STD, 0x222, lab, "VS-mode csrrw of sie returns the old vsie")
    expect_bits(t, HIE, "hie", STD, 0, lab, "hie after a VS-mode write of sie = 0")
    t.li("x6", 2)
    lab = t.window("VS", [f"csrrs x8, {hex(SIP)}, x6  // sip (vsip)"], "ok", "VS-mode csrrs of sip.SSIP")
    expect_bits(t, HVIP, "hvip", STD, 4, lab, "hvip after a VS-mode csrrs of sip.SSIP")
    expect_bits(t, SIP, "sip", 2, 0, lab, "HS-mode sip.SSIP after a VS-mode csrrs of sip.SSIP")
    reset(t)
    tests.append(t)

    # ---- vsip_vsie_lcofi ----
    t = new("vsip_vsie_lcofi", ["I", "S", "H", "Sscofpmf"])
    t.describe(
        source=HYP,
        rule_text="Extension Shlcofideleg supports delegating LCOFI interrupts to VS-mode. If the Shlcofideleg "
        "extension is implemented, hideleg bit 13 is writable; otherwise, it is read-only zero. When bit 13 of "
        "hideleg is zero, vsip.LCOFIP and vsie.LCOFIE are read-only zeros. Else, vsip.LCOFIP and vsie.LCOFIE are "
        "aliases of sip.LCOFIP and sie.LCOFIE.",
        context="Sscofpmf makes sip.LCOFIP and sie.LCOFIE writable (bit 13). Whether hideleg bit 13 is writable is "
        "probed; with SHLCOFIDELEG_SUPPORTED it must be. sstatus.SIE is 0, so the pending LCOFI is not taken.",
        plan="1. hideleg[13] = 0: with sip.LCOFIP = sie.LCOFIE = 1, vsip and vsie bit 13 read 0; setting vsie bit 13 "
        "leaves sie.LCOFIE unchanged after clearing it.\n"
        "2. If hideleg[13] is writable: vsip/vsie bit 13 follow sip.LCOFIP and sie.LCOFIE (1 and 0), and csrs/csrc "
        "of vsie and vsip bit 13 set and clear sie.LCOFIE and sip.LCOFIP.\n"
        "3. With Shlcofideleg, hideleg[13] reads back 1.",
    )
    reset(t)
    lab = here(t, "d0")
    cs(t, SIP, "sip", 0x2000, True)
    cs(t, SIE_CSR, "sie", 0x2000, True)
    expect_bits(t, VSIP, "vsip", 0x2000, 0, lab, "vsip.LCOFIP with hideleg[13]=0")
    expect_bits(t, VSIE, "vsie", 0x2000, 0, lab, "vsie.LCOFIE with hideleg[13]=0")
    cs(t, SIE_CSR, "sie", 0x2000, False)
    cs(t, VSIE, "vsie", 0x2000, True)
    expect_bits(t, SIE_CSR, "sie", 0x2000, 0, lab, "sie.LCOFIE after setting vsie bit 13 with hideleg[13]=0")
    cs(t, HIDELEG, "hideleg", 0x2000, True)
    rd(t, "x1", HIDELEG, "hideleg")
    t.emit("srli x1, x1, 13")
    t.emit("andi x1, x1, 1")
    with t.only_if("defined(SHLCOFIDELEG_SUPPORTED)"):
        t.check("x1", 1, lab, "hideleg[13] is writable with Shlcofideleg")

    def deleg() -> None:
        for v in (1, 0):
            lab = here(t, f"d1_{v}")
            cs(t, SIP, "sip", 0x2000, bool(v))
            cs(t, SIE_CSR, "sie", 0x2000, bool(v))
            expect_bits(t, VSIP, "vsip", 0x2000, v << 13, lab, f"vsip.LCOFIP with hideleg[13]=1, sip.LCOFIP={v}")
            expect_bits(t, VSIE, "vsie", 0x2000, v << 13, lab, f"vsie.LCOFIE with hideleg[13]=1, sie.LCOFIE={v}")
        lab = here(t, "d1w")
        cs(t, VSIE, "vsie", 0x2000, True)
        expect_bits(t, SIE_CSR, "sie", 0x2000, 0x2000, lab, "sie.LCOFIE after csrs vsie bit 13")
        cs(t, VSIP, "vsip", 0x2000, True)
        expect_bits(t, SIP, "sip", 0x2000, 0x2000, lab, "sip.LCOFIP after csrs vsip bit 13")
        cs(t, VSIP, "vsip", 0x2000, False)
        expect_bits(t, SIP, "sip", 0x2000, 0, lab, "sip.LCOFIP after csrc vsip bit 13")
        cs(t, VSIE, "vsie", 0x2000, False)
        expect_bits(t, SIE_CSR, "sie", 0x2000, 0, lab, "sie.LCOFIE after csrc vsie bit 13")

    t.either("x1", deleg, lambda: None)
    cs(t, SIP, "sip", 0x2000, False)
    cs(t, SIE_CSR, "sie", 0x2000, False)
    reset(t)
    tests.append(t)
    return tests


def gen_priority() -> list[TestFile]:
    t = new("hsint_priority")
    t.describe(
        source=HYP,
        rule_text="Multiple simultaneous interrupts destined for HS-mode are handled in the following decreasing "
        "priority order: SEI, SSI, STI, SGEI, VSEI, VSSI, VSTI, LCOFI.",
        context="All interrupts are made pending and enabled with sstatus.SIE = 0, then SIE is set (or the hart "
        "enters VS-mode, where HS-level interrupts are always enabled). The framework handler masks each taken "
        "interrupt's enable bit, so the rest follow one at a time; the trap log (4 entries) records the order. "
        "SEI and STI come from mip.SEIP and mip.STIP (M-mode writes; menvcfg.STCE = 0), SSI from sip.SSIP, the "
        "VS-level interrupts from hvip, SGEI from the platform (when the framework can raise guest interrupts) and "
        "LCOFI from sip.LCOFIP (Sscofpmf). Overlapping groups chain to the full order.",
        plan="1. HS-mode: SEI, SSI, STI, VSEI pending: taken as SEI, SSI, STI, VSEI.\n"
        "2. HS-mode: STI, VSEI, VSSI, VSTI: taken as STI, VSEI, VSSI, VSTI.\n"
        "3. VS-mode (nothing delegated): VSTI, VSSI, VSEI: taken as VSEI, VSSI, VSTI.\n"
        "4. HS-mode with Sscofpmf, when sip.LCOFIP is writable (LCOFI delegated to HS-mode): LCOFI, VSTI, SSI: taken "
        "as SSI, VSTI, LCOFI.\n"
        "5. HS-mode with guest interrupts: VSEI, SGEI, STI: taken as STI, SGEI, VSEI.",
    )
    reset(t)
    order = [9, 1, 5, 12, 10, 2, 6, 13]
    if MUT == "prio_by_number":
        order = [13, 12, 10, 9, 6, 5, 2, 1]
    if MUT == "vsti_over_vssi":
        order = [9, 1, 5, 12, 10, 6, 2, 13]

    def pend(codes: list[int]) -> None:
        for c in codes:
            if c in (2, 6, 10):
                cs(t, HVIP, "hvip", 1 << c, True)
                cs(t, HIE, "hie", 1 << c, True)
            elif c == 1:
                cs(t, SIP, "sip.SSIP", 2, True)
                cs(t, SIE_CSR, "sie.SSIE", 2, True)
            elif c in (5, 9):
                t.tsbi_csr("SET", "MIP", imm=1 << c)
                cs(t, SIE_CSR, f"sie bit {c}", 1 << c, True)
            elif c == 13:
                cs(t, SIP, "sip.LCOFIP", 1 << 13, True)
                cs(t, SIE_CSR, "sie.LCOFIE", 1 << 13, True)
            elif c == 12:
                t.li("x7", 2)
                t.emit(f"csrw {hex(HGEIE)}, x7  // hgeie = bit 1")
                raise_gei(t, 1, True)
                cs(t, HIE, "hie.SGEIE", 1 << 12, True)

    def cleanup() -> None:
        t.tsbi_csr("CLEAR", "MIP", imm=0x220)
        t.li("x7", 0x2222)
        t.emit(f"csrc {hex(SIP)}, x7  // sip")
        t.emit(f"csrc {hex(SIE_CSR)}, x7  // sie")
        reset(t)

    def group(codes: list[int], mode: str, desc: str) -> None:
        no_hs_sie(t)
        pend(codes)
        lab = int_window(t, mode, desc, n=len(codes))
        seq = [(c, 1) for c in order if c in codes]
        taken(t, lab, mode, desc, seq)
        cleanup()

    group([9, 1, 5, 10], "S", "SEI, SSI, STI, VSEI pending in HS-mode")
    group([5, 10, 2, 6], "S", "STI, VSEI, VSSI, VSTI pending in HS-mode")
    group([6, 2, 10], "VS", "VSTI, VSSI, VSEI pending in VS-mode, none delegated")
    with t.only_if("defined(SSCOFPMF_SUPPORTED)"):
        t.comment("sip.LCOFIP is writable only if mideleg[13] = 1 (or mvien[13] with the AIA): probe")
        cs(t, SIP, "sip.LCOFIP", 1 << 13, True)
        rd(t, "x1", SIP, "sip")
        cs(t, SIP, "sip.LCOFIP", 1 << 13, False)
        t.emit("srli x1, x1, 13")
        t.emit("andi x1, x1, 1")
        t.either("x1", lambda: group([13, 6, 1], "S", "LCOFI, VSTI, SSI pending in HS-mode"), lambda: None)
    with t.only_if(SGEI):
        geilen_probe(t, "x9")
        t.either("x9", lambda: group([10, 12, 5], "S", "VSEI, SGEI, STI pending in HS-mode"), lambda: None)
        t.emit(f"csrw {hex(HGEIE)}, x0")
        raise_gei(t, 1, False)
    return [t]


def gen_m() -> list[TestFile]:
    tests = []

    # ---- mideleg_acc_H (S-mode read) and _Sm (M-mode write) ----
    t = new("mideleg_acc_H")
    t.describe(
        source="src/priv/hypervisor.adoc",
        rule_text="When the hypervisor extension is implemented, bits 10, 6, and 2 of mideleg (corresponding to the "
        "standard VS-level interrupts) are each read-only one. Furthermore, if any guest external interrupts are "
        "implemented (GEILEN is nonzero), bit 12 of mideleg (corresponding to supervisor-level guest external "
        "interrupts) is also read-only one. VS-level interrupts and guest external interrupts are always delegated "
        "past M-mode to HS-mode.",
        context="T-SBI does not give S-mode tests access to mideleg, so mideleg_acc_H_Sm reads and writes it in "
        "M-mode. This file checks the effect: VS-level interrupts reach HS-mode.",
        plan="1. Each of VSSI, VSTI, VSEI (hvip), with hideleg = 0 and hie set, is taken by the HS-mode handler (not "
        "M-mode) from VS-mode.",
    )
    reset(t)
    for nm, i in VS_INTS:
        w(t, HIE, "hie", 1 << i)
        w(t, HVIP, "hvip", 1 << i)
        lab = int_window(t, "VS", nm)
        taken(t, lab, "VS", f"{nm} from VS-mode, hideleg = 0", [(i, 1)])
        reset(t)
    tests.append(t)

    t = new("mideleg_acc_H", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source="src/priv/hypervisor.adoc",
        rule_text="When the hypervisor extension is implemented, bits 10, 6, and 2 of mideleg (corresponding to the "
        "standard VS-level interrupts) are each read-only one. Furthermore, if any guest external interrupts are "
        "implemented (GEILEN is nonzero), bit 12 of mideleg (corresponding to supervisor-level guest external "
        "interrupts) is also read-only one.",
        context="M-mode part: writes of mideleg. mideleg is restored afterwards.",
        plan="0. mideleg bits 2, 6, 10 read 1, and bit 12 reads 1 when GEILEN > 0.\n"
        "1. csrc mideleg 0x1444 and csrw mideleg 0: bits 2, 6, 10 still read 1, and bit 12 reads 1 when GEILEN > 0 "
        "(hgeie bit 1 writable).\n"
        "2. Every CSR form that writes zeros (csrrw, csrrc, csrrci) leaves bits 2, 6, 10 set.",
    )
    t.emit("csrr x1, mideleg  // save")
    geilen_probe(t, "x9")
    t.emit("andi x9, x9, 2")
    lab = here(t, "rd")
    t.emit("csrr x8, mideleg")
    t.check_masked("x8", 0x444, 0x444, lab, "mideleg bits 2, 6, 10")
    t.either("x9", lambda: t.check_masked("x8", 0x1000, 0x1000, lab, "mideleg bit 12 with GEILEN > 0"), lambda: None)
    ro = 0 if MUT == "mideleg_vs_writable" else 0x444
    for asm, d in (
        ("csrc mideleg, x6", "csrc 0x1444"),
        ("csrw mideleg, x0", "csrw 0"),
        ("csrrc x0, mideleg, x6", "csrrc 0x1444"),
        ("csrrci x0, mideleg, 4", "csrrci 4"),
    ):
        lab = here(t, "w")
        t.li("x6", 0x1444)
        t.emit(asm)
        t.emit("csrr x8, mideleg")
        t.check_masked("x8", 0x444, ro, lab, f"mideleg bits 2, 6, 10 after {d}")
        t.either(
            "x9",
            lambda lab=lab, d=d: t.check_masked("x8", 0x1000, 0x1000, lab, f"mideleg bit 12 after {d}, GEILEN > 0"),
            lambda: None,
        )
        t.emit("csrw mideleg, x1  // restore")
    tests.append(t)

    # ---- mideleg_hroz (M-mode: T-SBI does not give S-mode access to mideleg) ----
    t = new("mideleg_hroz", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="For bits of mideleg that are zero, the corresponding bits in hideleg, hip, and hie are read-only "
        "zeros.",
        context="M-mode accesses mideleg and the H CSRs directly, with mstatus.MIE = 0 so nothing is taken. With "
        "Sscofpmf, mideleg bit 13 (LCOFI) is writable: with mideleg[13] = 0, hideleg[13] and hie[13] must be "
        "read-only zero; with mideleg[13] = 1, hideleg[13] is writable iff Shlcofideleg. hvip is 0, so W(hip) is the "
        "writable VSSIP bit only.",
        plan="1. (W(hideleg) | W(hie) | W(hip)) & ~mideleg = 0 over all bits, where W(x) is x after writing all "
        "ones. With Smaia, bits set in mvien are excluded (AIA, MSLevel.adoc: a bit that is zero in both mideleg and "
        "mvien is read-only zero in hideleg, hip and hie; otherwise hideleg may be writable for interrupts 13-63).\n"
        "2. With Sscofpmf, mideleg[13] = 0: writing 1 to hideleg[13], hie[13] and hip[13] reads back 0.\n"
        "3. With Shlcofideleg and mideleg[13] = 1: hideleg[13] reads back 1.",
    )
    t.li("x7", 8)
    t.emit("csrc mstatus, x7  // MIE = 0")
    t.emit(f"csrw {hex(HVIP)}, x0")
    t.emit("csrr x6, mideleg")
    with t.only_if("defined(SMAIA_SUPPORTED)"):
        t.emit("csrr x7, 0x308  // mvien: with the AIA, a bit set here may also make hideleg writable")
        t.emit("or x6, x6, x7")
    t.emit("not x6, x6  // ~(mideleg | mvien)")
    t.emit("li x7, -1")
    t.emit("li x8, 0")
    for num, nm in ((HIDELEG, "hideleg"), (HIE, "hie"), (HIP, "hip")):
        t.emit(f"csrw {hex(num)}, x7  // {nm} = all ones")
        t.emit(f"csrr x9, {hex(num)}")
        t.emit("or x8, x8, x9")
        t.emit(f"csrw {hex(num)}, x0")
    lab = here(t, "hroz")
    t.emit("and x8, x8, x6")
    t.check("x8", 0, lab, "bits of hideleg, hie or hip that are writable where mideleg is zero")
    t.emit("csrr x1, mideleg  // save")
    with t.only_if("defined(SSCOFPMF_SUPPORTED)"):
        t.li("x6", 0x2000)
        t.emit("csrc mideleg, x6")
        lab = here(t, "m0")
        for num, nm in ((HIDELEG, "hideleg"), (HIE, "hie"), (HIP, "hip")):
            t.emit(f"csrs {hex(num)}, x6  // {nm} bit 13")
            t.emit(f"csrr x8, {hex(num)}")
            t.check_masked("x8", 0x2000, 0, lab, f"{nm}[13] with mideleg[13] = 0")
            t.emit(f"csrc {hex(num)}, x6")
    with t.only_if("defined(SSCOFPMF_SUPPORTED) && defined(SHLCOFIDELEG_SUPPORTED)"):
        t.emit("csrs mideleg, x6")
        t.emit(f"csrs {hex(HIDELEG)}, x6")
        t.emit(f"csrr x8, {hex(HIDELEG)}")
        t.check_masked("x8", 0x2000, 0x2000, lab, "hideleg[13] with mideleg[13] = 1 and Shlcofideleg")
        t.emit(f"csrc {hex(HIDELEG)}, x6")
    t.emit("csrw mideleg, x1  // restore")
    tests.append(t)

    # ---- mip_mie_vs (M-mode) ----
    t = new("mip_mie_vs", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="The hypervisor extension gives registers mip and mie additional active bits for the "
        "hypervisor-added interrupts. <<hypervisor-mipreg-standard>> and <<hypervisor-miereg-standard>> show the "
        "standard portions (bits 15:0) of registers mip and mie when the hypervisor extension is implemented.",
        context="M-mode with mstatus.MIE = 0, so nothing is taken. mie bits 2, 6, 10 are writable (their hie aliases "
        "are, hie_acc); bit 12 is writable when GEILEN > 0. In mip, VSSIP is writable (alias of hvip.VSSIP), VSTIP, "
        "VSEIP and SGEIP are read-only (hvip, hgeip and Sstc are their sources).",
        plan="1. mie: set bits 2, 6, 10, 12: bits 2, 6, 10 read 1; bit 12 reads 1 when GEILEN > 0.\n"
        "2. mip with hvip = 0: csrs of bits 2, 6, 10, 12 reads back only bit 2; csrc clears it.\n"
        "3. hvip = 0x444 shows as mip bits 2, 6, 10.",
    )
    t.li("x7", 8)
    t.emit("csrc mstatus, x7  // MIE = 0")
    t.emit("csrr x1, mie  // save")
    geilen_probe(t, "x9")
    t.emit("andi x9, x9, 2")
    t.emit(f"csrw {hex(HVIP)}, x0")
    lab = here(t, "mie")
    t.li("x6", 0x1444)
    t.emit("csrs mie, x6")
    t.emit("csrr x8, mie")
    t.check_masked("x8", 0x444, 0x444, lab, "mie bits 2, 6, 10 after setting them")
    t.either("x9", lambda: t.check_masked("x8", 0x1000, 0x1000, lab, "mie bit 12 with GEILEN > 0"), lambda: None)
    t.emit("csrw mie, x1  // restore")
    lab = here(t, "mip")
    t.emit("csrs mip, x6")
    t.emit("csrr x8, mip")
    e = 0x444 if MUT == "mip_vstip_writable" else 0x4
    t.check_masked("x8", 0x1444, e, lab, "mip VS-level bits after csrs 0x1444 (hvip = 0, hgeip = 0)")
    t.emit("csrc mip, x6")
    t.emit("csrr x8, mip")
    t.check_masked("x8", 0x1444, 0, lab, "mip VS-level bits after csrc 0x1444")
    t.emit(f"csrw {hex(HVIP)}, x6")
    t.emit("csrr x8, mip")
    t.check_masked("x8", 0x444, 0x444, lab, "mip bits 2, 6, 10 with hvip = 0x444")
    t.emit(f"csrw {hex(HVIP)}, x0")
    tests.append(t)

    # ---- mip_mie_alias ----
    t = new("mip_mie_alias")
    t.describe(
        source=HYP,
        rule_text="Bits SGEIP, VSEIP, VSTIP, and VSSIP in mip are aliases for the same bits in hypervisor CSR hip, "
        "while SGEIE, VSEIE, VSTIE, and VSSIE in mie are aliases for the same bits in hie.",
        context="mip and mie are accessed in M-mode through T-SBI; hip, hie and hvip in HS-mode. hip.VSSIP is writable "
        "(so mip.VSSIP is); hip.VSTIP/VSEIP are read-only, so M-mode writes of mip.VSTIP/VSEIP have no effect "
        "(QEMU: https://gitlab.com/qemu-project/qemu/-/work_items/4809).",
        plan="1. Each of hvip.VSSIP/VSTIP/VSEIP alone: mip shows the same bit (bits 12:0 & 0x1444).\n"
        "2. M-mode csrs/csrc of mip.VSSIP: hip and hvip follow.\n"
        "3. M-mode csrs of mip.VSTIP and mip.VSEIP with hvip = 0: hip stays 0.\n"
        "4. Each hie bit alone: mie shows it; M-mode csrs/csrc of mie bits 2, 6, 10 show in hie.",
    )
    reset(t)
    for nm, i in VS_INTS:
        lab = here(t, nm)
        w(t, HVIP, "hvip", 1 << i)
        m_read(t, "mip")
        t.check_masked("a0", 0x1444, 1 << i, lab, f"mip with hvip = {nm}P only")
        w(t, HVIP, "hvip", 0)
        w(t, HIE, "hie", 1 << i)
        m_read(t, "mie")
        t.check_masked("a0", 0x1444, 1 << i, lab, f"mie with hie = {nm}E only")
        w(t, HIE, "hie", 0)
        t.tsbi_csr("SET", "MIE", imm=1 << i)
        expect_bits(t, HIE, "hie", STD, 1 << i, lab, f"hie after M-mode csrs of mie bit {i}")
        t.tsbi_csr("CLEAR", "MIE", imm=1 << i)
        expect_bits(t, HIE, "hie", STD, 0, lab, f"hie after M-mode csrc of mie bit {i}")
    lab = here(t, "mipw")
    t.tsbi_csr("SET", "MIP", imm=4)
    expect_bits(t, HIP, "hip", STD, 4, lab, "hip after M-mode csrs of mip.VSSIP")
    expect_bits(t, HVIP, "hvip", STD, 4, lab, "hvip after M-mode csrs of mip.VSSIP")
    t.tsbi_csr("CLEAR", "MIP", imm=4)
    expect_bits(t, HVIP, "hvip", STD, 0, lab, "hvip after M-mode csrc of mip.VSSIP")
    t.tsbi_csr("SET", "MIP", imm=0x440)
    e = 0x440 if MUT == "mip_vstip_writable" else 0
    expect_bits(t, HIP, "hip", STD, e, lab, "hip after M-mode csrs of mip.VSTIP and mip.VSEIP (read-only)")
    t.tsbi_csr("CLEAR", "MIP", imm=0x440)
    reset(t)
    tests.append(t)
    return tests


def gen_gei() -> list[TestFile]:
    tests = []

    # ---- geilen ----
    t = new("geilen")
    t.describe(
        source=HYP,
        rule_text="The number of bits implemented in hgeip and hgeie for guest external interrupts is UNSPECIFIED and "
        "may be zero. This number is known as GEILEN. The least-significant bits are implemented first, apart from "
        "bit 0. Hence, if GEILEN is nonzero, bits GEILEN:1 shall be writable in hgeie, and all other bit positions "
        "shall be read-only zeros in both hgeip and hgeie.",
        context="R = hgeie after writing all ones. GEILEN is at most 31 (RV32) or 63 (RV64).",
        plan="1. R bit 0 is 0, and R >> 1 is of the form 2^k - 1 (contiguous from bit 1).\n"
        "2. hgeip has no bit outside R (hgeip & ~R = 0) and bit 0 is 0.\n"
        "3. Writing each single bit 1 to XLEN-1 to hgeie reads back that bit if it is in R, else 0 (sampled: bits 1, "
        "2, 5, 31 and on RV64 32, 62, 63).",
    )
    geilen_probe(t, "x9")
    lab = here(t, "r")
    t.emit("andi x5, x9, 1")
    t.check("x5", 0, lab, "hgeie bit 0 is read-only zero")
    t.emit("srli x8, x9, 1")
    t.emit("addi x6, x8, 1")
    t.emit("and x5, x8, x6  // (R>>1) & ((R>>1)+1) == 0 iff R>>1 = 2^k - 1")
    t.check("x5", 0, lab, "hgeie writable bits are contiguous from bit 1")
    t.emit(f"csrr x8, {hex(HGEIP)}  // hgeip")
    t.emit("not x6, x9")
    t.emit("and x5, x8, x6")
    t.check("x5", 0, lab, "hgeip has no bit outside hgeie's writable bits GEILEN:1")
    t.emit("andi x5, x8, 1")
    t.check("x5", 0, lab, "hgeip bit 0 is zero")
    for b in (1, 2, 5, 31):
        lab = here(t, f"b{b}")
        t.li("x7", 1)
        t.emit(f"slli x7, x7, {b}")
        t.emit(f"csrw {hex(HGEIE)}, x7")
        t.emit(f"csrr x8, {hex(HGEIE)}")
        t.emit("and x7, x7, x9  // expected: the bit if writable")
        eqb(t, "x8", "x7")
        t.check_bool("x5", lab, f"hgeie after writing bit {b} alone")
    with t.rv64_only():
        for b in (32, 62, 63):
            lab = here(t, f"b{b}")
            t.li("x7", 1)
            t.emit(f"slli x7, x7, {b}")
            t.emit(f"csrw {hex(HGEIE)}, x7")
            t.emit(f"csrr x8, {hex(HGEIE)}")
            t.emit("and x7, x7, x9")
            eqb(t, "x8", "x7")
            t.check_bool("x5", lab, f"hgeie after writing bit {b} alone")
    t.emit(f"csrw {hex(HGEIE)}, x0")
    tests.append(t)

    # ---- hgeie_sz_acc_op ----
    t = new("hgeie_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The hgeie register is an HSXLEN-bit read/write register, formatted as shown in "
        "<<norm:hgeie_img>>, that contains enable bits for the guest external interrupts at this hart.",
        context="R = writable bits (all ones written). Values are masked by R for the expectation.",
        plan="1. Write 0x55..55, 0xAA..AA and a random value: each reads back as value & R.\n"
        "2. csrrw returns the old value; csrrs and csrrc change only bits in R.",
    )
    geilen_probe(t, "x9")
    for v in (X(0x55555555, 0x5555555555555555), X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA), t.rand_x()):
        lab = here(t, "v")
        t.load("x6", v, "value")
        t.emit(f"csrw {hex(HGEIE)}, x6")
        t.emit(f"csrr x8, {hex(HGEIE)}")
        t.emit("and x7, x6, x9")
        eqb(t, "x8", "x7")
        t.check_bool("x5", lab, "hgeie reads back value & writable bits")
    lab = here(t, "forms")
    t.emit("li x6, -1")
    t.emit(f"csrrw x8, {hex(HGEIE)}, x6  // old value: last random & R")
    t.emit(f"csrrc x6, {hex(HGEIE)}, x9  // returns R, clears all")
    eqb(t, "x6", "x9")
    t.check_bool("x5", lab, "csrrc of hgeie returns the value written by csrrw (all writable bits)")
    t.emit(f"csrr x8, {hex(HGEIE)}")
    t.check("x8", 0, lab, "hgeie after csrrc of all writable bits")
    t.emit(f"csrw {hex(HGEIE)}, x0")
    tests.append(t)

    # ---- hgeip_sz_acc_op ----
    t = new("hgeip_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="The hgeip register is an HSXLEN-bit read-only register, formatted as shown in <<hgeipreg>>, that "
        "indicates pending guest external interrupts for this hart.",
        context="hgeip is at 0xE12, a read-only CSR address: every write form raises illegal-instruction in HS-mode "
        "and the value is unchanged.",
        plan="1. HS-mode reads succeed; csrrw, csrrs/csrrc with a nonzero rs1 register (holding 0) and csrrwi raise "
        "illegal-instruction with xtval 0 or the instruction bits.\n"
        "2. hgeip reads the same before and after the attempted writes.",
    )
    from hlib import FORMS, csr_window

    t.emit(f"csrr x8, {hex(HGEIP)}  // hgeip")
    t.emit("mv x9, x8")
    for form in FORMS:
        t.emit("li x6, 0")
        csr_window(t, "S", "hgeip", form, "illegal" if form[5] else "ok", "HS-mode")
    lab = here(t, "same")
    t.emit(f"csrr x8, {hex(HGEIP)}")
    eqb(t, "x8", "x9")
    t.check_bool("x5", lab, "hgeip unchanged by attempted writes")
    tests.append(t)

    # ---- guest interrupts through the platform ----
    def gei_test(rule: str, text: str, ctx: str, plan: str, body: Callable[[TestFile], object]) -> TestFile:
        t = new(rule)
        t.describe(
            source=HYP,
            rule_text=text,
            context=ctx + " Guest external interrupts are raised through the "
            "platform (RVTEST_SET_GUEST_EXT_INT_S), which the framework provides when the DUT implements guest "
            "interrupt files (RVTEST_SGEI_INTR_IMPL); without it the test only checks that hgeip is 0.",
            plan=plan,
        )
        reset(t)
        with t.only_if(SGEI):
            geilen_probe(t, "x9")
            t.emit("andi x9, x9, 2")
            t.either("x9", lambda: body(t), lambda: None)
            t.emit(f"csrw {hex(HGEIE)}, x0")
            vgein(t, 0)
            reset(t)
        lab = here(t, "end")
        t.emit(f"csrr x8, {hex(HGEIP)}")
        t.check("x8", 0, lab, "hgeip is 0 with no guest interrupt raised")
        return t

    def b_fields(t: TestFile) -> None:
        lab = here(t, "set")
        raise_gei(t, 1, True)
        expect_bits(t, HGEIP, "hgeip", -1, 2, lab, "hgeip after raising guest external interrupt 1")
        raise_gei(t, 1, False)
        expect_bits(t, HGEIP, "hgeip", -1, 0, lab, "hgeip after clearing guest external interrupt 1")

    def b_sgeip(t: TestFile, take: bool) -> None:
        raise_gei(t, 1, True)
        for he, e in ((0, 0), (2, 1), (4, 0), (6, 1)):
            lab = here(t, f"hgeie{he}")
            t.li("x7", he)
            t.emit(f"csrw {hex(HGEIE)}, x7  // hgeie")
            expect_bits(t, HIP, "hip", 0x1000, e << 12, lab, f"hip.SGEIP with hgeip = 2, hgeie = {he}")
        if take:
            t.li("x7", 2)
            t.emit(f"csrw {hex(HGEIE)}, x7")
            cs(t, HIP, "hip.SGEIP (read-only)", 0x1000, False)
            expect_bits(t, HIP, "hip", 0x1000, 0x1000, lab, "hip.SGEIP after csrc (read-only)")
            w(t, HIE, "hie", 0x1000)
            lab = int_window(t, "VS", "SGEI")
            taken(t, lab, "VS", "SGEI pending (hgeip & hgeie), hie.SGEIE = 1, VS-mode", [(12, 1)])
        raise_gei(t, 1, False)
        t.emit(f"csrw {hex(HGEIE)}, x0")

    tests.append(
        gei_test(
            "hgeip_hgeie_fields",
            "Guest external interrupt number i corresponds with bit i in both hgeip and hgeie.",
            "Interrupt number 1 exists whenever GEILEN > 0.",
            "1. Raising guest external interrupt 1 sets exactly hgeip bit 1; clearing it clears hgeip.\n"
            "2. hgeie bit 1 (with hie.SGEIE) makes it an SGEI: hip.SGEIP = 1 with hgeie = 2, 0 with hgeie = 4 or 0.",
            lambda t: (b_fields(t), b_sgeip(t, False)),
        )
    )

    tests.append(
        gei_test(
            "hip_sgeip_sgeie_acc_op",
            "Bits hip.SGEIP and hie.SGEIE are the interrupt-pending and interrupt-enable bits for guest external "
            "interrupts at supervisor level (HS-level). SGEIP is read-only in hip, and is 1 if and only if the bitwise "
            "logical-AND of CSRs hgeip and hgeie is nonzero in any bit.",
            "Guest interrupt 1 is raised; hgeie bits beyond GEILEN read 0, so hgeie = 4 enables nothing when GEILEN = 1.",
            "1. hip.SGEIP = 1 iff hgeip & hgeie != 0: hgeie = 0, 2, 4, 6 give 0, 1, 0 (bit 2 not pending), 1.\n"
            "2. csrc of hip.SGEIP leaves it 1 (read-only).\n"
            "3. With hie.SGEIE = 1 the SGEI is taken in HS-mode from VS-mode (cause 12; hideleg bit 12 is read-only "
            "zero).",
            lambda t: b_sgeip(t, True),
        )
    )

    def b_vseip(t: TestFile) -> None:
        raise_gei(t, 1, True)
        for vg, he, e in ((0, 0, 0), (1, 0, 1), (1, 2, 1), (0, 2, 0)):
            lab = here(t, f"vg{vg}")
            vgein(t, vg)
            t.li("x7", he)
            t.emit(f"csrw {hex(HGEIE)}, x7  // hgeie")
            if MUT == "vgein_ignored":
                e = 0
            if MUT == "hgeie_gates_vseip" and he == 0:
                e = 0
            expect_bits(t, HIP, "hip", 0x400, e << 10, lab, f"hip.VSEIP with hgeip = 2, VGEIN = {vg}, hgeie = {he}")
        vgein(t, 1)
        t.emit(f"csrw {hex(HGEIE)}, x0")
        w(t, HIDELEG, "hideleg", 0x400)
        w(t, HIE, "hie", 0x400)
        cs(t, VSSTATUS, "vsstatus.SIE", SIE, True)
        lab = int_window(t, "VS", "VSEI from hgeip")
        taken(t, lab, "VS", "VSEI from hgeip[VGEIN=1], delegated, VS-mode", [(9, 2)])
        raise_gei(t, 1, False)
        vgein(t, 0)

    tests.append(
        gei_test(
            "hgeie_op",
            "Register hgeie selects the subset of guest external interrupts that cause a supervisor-level (HS-level) "
            "guest external interrupt. The enable bits in hgeie do not affect the VS-level external interrupt signal "
            "selected from hgeip by hstatus.VGEIN.",
            "Guest interrupt 1 is raised.",
            "1. hip.VSEIP with hgeip = 2: VGEIN = 0 gives 0, VGEIN = 1 gives 1 with hgeie = 0 and with hgeie = 2.\n"
            "2. hip.SGEIP follows hgeie (hip_sgeip_sgeie_acc_op).\n"
            "3. With VGEIN = 1, hgeie = 0, hideleg[10] = 1 and vsstatus.SIE = 1, VS-mode takes a supervisor external "
            "interrupt (cause 9).",
            b_vseip,
        )
    )

    def b_vgein_op(t: TestFile) -> None:
        raise_gei(t, 1, True)
        lab = here(t, "vg1")
        vgein(t, 1)
        expect_bits(
            t, HIP, "hip", 0x400, 0x400 if MUT != "vgein_ignored" else 0, lab, "hip.VSEIP with VGEIN = 1, hgeip = 2"
        )
        t.emit(f"csrr x8, {hex(HSTATUS)}")
        t.emit("srli x8, x8, 12")
        t.emit("andi x8, x8, 0x3F")
        t.check("x8", 1, lab, "hstatus.VGEIN reads back 1")
        t.li("x7", -1)
        t.emit(f"csrw {hex(HGEIE)}, x7")
        rd(t, "x6", HGEIE, "hgeie")
        t.emit(f"csrw {hex(HGEIE)}, x0")
        t.emit("andi x6, x6, 4  // GEILEN >= 2")

        def two() -> None:
            lab = here(t, "vg2")
            vgein(t, 2)
            expect_bits(t, HIP, "hip", 0x400, 0, lab, "hip.VSEIP with VGEIN = 2 and only hgeip bit 1")

        t.either("x6", two, lambda: None)
        raise_gei(t, 1, False)
        lab = here(t, "cl")
        vgein(t, 1)
        expect_bits(t, HIP, "hip", 0x400, 0, lab, "hip.VSEIP with VGEIN = 1 after clearing guest interrupt 1")

    tests.append(
        gei_test(
            "hstatus_vgein_op",
            "The VGEIN (Virtual Guest External Interrupt Number) field selects a guest external interrupt source for "
            "VS-level external interrupts.",
            "Guest interrupt 1 is raised; hvip.VSEIP is 0.",
            "1. VGEIN = 1 with hgeip bit 1: hip.VSEIP = 1, and VGEIN reads back 1.\n"
            "2. With GEILEN >= 2, VGEIN = 2: hip.VSEIP = 0.\n"
            "3. After clearing guest interrupt 1, VGEIN = 1: hip.VSEIP = 0.",
            b_vgein_op,
        )
    )

    def b_zero(t: TestFile) -> None:
        raise_gei(t, 1, True)
        t.li("x7", 2)
        t.emit(f"csrw {hex(HGEIE)}, x7")
        lab = here(t, "z")
        vgein(t, 0)
        expect_bits(t, HIP, "hip", 0x400, 0, lab, "hip.VSEIP with VGEIN = 0, hgeip = hgeie = 2")
        w(t, HIDELEG, "hideleg", 0)
        w(t, HIE, "hie", 0x400)
        lab = int_window(t, "VS", "VGEIN = 0")
        taken(t, lab, "VS", "VGEIN = 0, guest interrupt 1 pending, hie.VSEIE = 1 (hie.SGEIE = 0)", [])
        raise_gei(t, 1, False)

    tests.append(
        gei_test(
            "hstatus_vgein_zero",
            "When VGEIN=0, no guest external interrupt source is selected for VS-level external interrupts.",
            "Guest interrupt 1 is raised and enabled in hgeie (so it is pending as SGEI, but hie.SGEIE = 0).",
            "1. VGEIN = 0: hip.VSEIP = 0.\n2. With hie.VSEIE = 1, VS-mode takes no interrupt.",
            b_zero,
        )
    )

    # ---- hstatus_vgein_wlrl (no platform needed) ----
    t = new("hstatus_vgein_wlrl")
    t.describe(
        source=HYP,
        rule_text="VGEIN is a WLRL field that must be able to hold values between zero and the maximum guest external "
        "interrupt number (known as GEILEN), inclusive.",
        context="GEILEN is the highest writable hgeie bit. Only legal values (0 to GEILEN) are written. GEILEN = 0 "
        "allows VGEIN to be read-only zero (hstatus_vgein_acc), which writing 0 is consistent with.",
        plan="1. VGEIN = 0 reads back 0.\n"
        "2. For each j from 1 to XLEN-1 with hgeie bit j writable (j <= GEILEN), VGEIN = j reads back j.",
    )
    geilen_probe(t, "x9")
    lab = here(t, "z")
    vgein(t, 0)
    t.emit(f"csrr x8, {hex(HSTATUS)}")
    t.li("x7", 0x3F000)
    t.emit("and x8, x8, x7")
    t.check("x8", 0, lab, "hstatus.VGEIN reads back 0")
    for j in list(range(1, 32)) + [None]:
        if j is None:
            with t.rv64_only():
                for jj in range(32, 64):
                    lab = here(t, f"j{jj}")
                    t.emit(f"srli x6, x9, {jj}")
                    t.emit("andi x6, x6, 1")

                    def chk_rv64(jj: int = jj, lab: str = lab) -> None:
                        vgein(t, jj)
                        t.emit(f"csrr x8, {hex(HSTATUS)}")
                        t.emit("srli x8, x8, 12")
                        t.emit("andi x8, x8, 0x3F")
                        t.check("x8", jj, lab, f"hstatus.VGEIN = {jj} (<= GEILEN) reads back")

                    t.either("x6", chk_rv64, lambda: None)
            continue
        lab = here(t, f"j{j}")
        t.emit(f"srli x6, x9, {j}")
        t.emit("andi x6, x6, 1")

        def chk(j: int = j, lab: str = lab) -> None:
            vgein(t, j)
            t.emit(f"csrr x8, {hex(HSTATUS)}")
            t.emit("srli x8, x8, 12")
            t.emit("andi x8, x8, 0x3F")
            t.check("x8", j, lab, f"hstatus.VGEIN = {j} (<= GEILEN) reads back")

        t.either("x6", chk, lambda: None)
    vgein(t, 0)
    tests.append(t)

    # ---- hip_vseip_vseie_op (hvip and hgeip sources; writes ignored) ----
    t = new("hip_vseip_vseie_op")
    t.describe(
        source=HYP,
        rule_text="Bits hip.VSEIP and hie.VSEIE are the interrupt-pending and interrupt-enable bits for VS-level "
        "external interrupts. VSEIP is read-only in hip, and is the logical-OR of these interrupt sources: bit VSEIP "
        "of hvip; the bit of hgeip selected by hstatus.VGEIN; and any other platform-specific external interrupt "
        "signal directed to VS-level.",
        context="No platform-specific VS-level source is active. The hgeip source needs the framework's guest "
        "interrupt support (RVTEST_SGEI_INTR_IMPL) and GEILEN > 0.",
        plan="1. hvip.VSEIP = 1 / 0 gives hip.VSEIP = 1 / 0.\n"
        "2. Read-only: csrs of hip.VSEIP with hvip = 0 leaves 0; csrc with hvip.VSEIP = 1 leaves 1.\n"
        "3. OR of sources: with guest interrupt 1 pending and VGEIN = 1, hip.VSEIP = 1 for hvip.VSEIP = 0 and 1; "
        "clearing hvip.VSEIP does not clear it.\n"
        "4. hie.VSEIE enables it: taken in HS-mode from VU-mode with hie.VSEIE = 1 (cause 10).",
    )
    reset(t)
    lab = here(t, "hvip")
    for v in (1, 0):
        w(t, HVIP, "hvip", v << 10)
        expect_bits(t, HIP, "hip", 0x400, v << 10, lab, f"hip.VSEIP with hvip.VSEIP = {v}")
    cs(t, HIP, "hip", 0x400, True)
    e = 0x400 if MUT == "hip_vstip_writable" else 0
    expect_bits(t, HIP, "hip", 0x400, e, lab, "hip.VSEIP after csrs of hip (hvip = 0)")
    w(t, HVIP, "hvip", 0x400)
    cs(t, HIP, "hip", 0x400, False)
    e = 0 if MUT == "hip_vstip_writable" else 0x400
    expect_bits(t, HIP, "hip", 0x400, e, lab, "hip.VSEIP after csrc of hip (hvip.VSEIP = 1)")
    w(t, HIE, "hie", 0x400)
    lab = int_window(t, "VU", "VSEI")
    taken(t, lab, "VU", "hvip.VSEIP = 1, hie.VSEIE = 1, VU-mode", [(10, 1)])
    reset(t)
    with t.only_if(SGEI):
        geilen_probe(t, "x9")
        t.emit("andi x9, x9, 2")

        def orsrc() -> None:
            raise_gei(t, 1, True)
            vgein(t, 1)
            for v in (0, 1, 0):
                lab = here(t, f"or{v}")
                w(t, HVIP, "hvip", v << 10)
                expect_bits(
                    t,
                    HIP,
                    "hip",
                    0x400,
                    0x400 if MUT != "vgein_ignored" or v else 0,
                    lab,
                    f"hip.VSEIP with hgeip[VGEIN=1] = 1, hvip.VSEIP = {v}",
                )
            raise_gei(t, 1, False)
            vgein(t, 0)

        t.either("x9", orsrc, lambda: None)
    reset(t)
    tests.append(t)
    return tests
