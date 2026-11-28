#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Smcsrind and tests_ai/Sscsrind: one test per normative rule about indirect CSR access.

The rules are in src/priv/smcsrind.adoc, plus the CSRIND bits in src/priv/smstateen.adoc. Smcsrind tests (the
M-level CSRs miselect/mireg*, and the mstateen0 gate) boot to M, or to S with T-SBI for mstateen0, and require Sm.
Sscsrind tests boot to S (HS with H) and enter U, VS and VU in trap windows; their M-mode parts are <rule>_Sm.S
files. Implemented select values come only from the extension macros (SMAIA/SSAIA, SSCTR): every other test uses
values that no extension has allocated, or checks only what holds for every legal value (WARL stability).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable
from csrindlib import (
    CSRIND,
    FORMS,
    ILLEGAL,
    ISSUE,
    M_SET,
    MARCH,
    MIREGS,
    MSB,
    READ_FORMS,
    RESERVED_SEL,
    RW_FORMS,
    S_SET,
    SIREGS,
    SMAIA,
    SMSTATEEN,
    SSAIA,
    SSCTR,
    STATEEN,
    SWEEP_SEL,
    VIRTUAL,
    VS_SET,
    VSIREGS,
    H,
    access,
    eq_check,
    form_value,
    h_csrind,
    h_probe,
    h_read_csrind,
    m_csrind,
    m_csrind_direct,
    m_read_csrind,
    macro,
    set_sel,
    sweep,
)

SUITE = "Smcsrind"
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    "siselect_8bit": "siselect holds only 8 bits (0..0xFF)",
    "vsiselect_8bit": "vsiselect holds only 8 bits (0..0xFF)",
    "miselect_4bit": "miselect holds only the low 4 bits of an AIA select value",
    "siselect_is_vsiselect": "siselect and vsiselect are one register at V=0",
    "vs_siselect_not_substituted": "a VS-mode siselect write lands in siselect, not vsiselect",
    "miselect_is_siselect": "miselect and siselect are one register",
    "select_ignored_m": "mireg accesses the same register whatever miselect holds",
    "select_ignored_s": "sireg accesses the same register whatever siselect holds",
    "vs_sireg_uses_siselect": "VS-mode sireg uses siselect rather than vsiselect",
    "read_form_writes": "csrrs/csrrc with rs1=x0 (or uimm=0) on a select CSR writes it",
    "msb_sticky": "a custom (MSB-set) siselect value leaves the MSB set after an in-range write",
    "vs_vsiselect_ok": "VS-mode may access vsiselect/vsireg* directly",
    "vu_illegal": "VU-mode access to siselect/sireg* raises illegal- instead of virtual-instruction",
    "u_virtual": "U-mode access to siselect raises virtual-instruction",
    "vs_mireg_virtual": "VS-mode access to miselect/mireg* raises virtual- instead of illegal-instruction",
    "mstateen_virtual": "mstateen0.CSRIND=0 makes VS/VU accesses raise virtual-instruction",
    "mstateen_ignored_s": "mstateen0.CSRIND=0 does not stop S-mode access to siselect",
    "mstateen_gates_m": "mstateen0.CSRIND=0 also blocks M-mode access to siselect",
    "hstateen_illegal": "hstateen0.CSRIND=0 makes VS-mode siselect accesses illegal- instead of virtual-instruction",
    "hstateen_gates_hs": "hstateen0.CSRIND=0 also blocks HS-mode access to siselect",
    "hstateen_ignored": "hstateen0.CSRIND=0 does not stop VS-mode access to siselect",
    "hstateen_direct_illegal": "hstateen0.CSRIND=0 makes VS-mode direct vsiselect/vsireg accesses illegal-instruction",
    "separate_vs_entries": "vsireg* at vsiselect 0x200-0x2FF reaches a separate set of CTR entries from sireg*",
    "hstateen_not_ro0": "hstateen0.CSRIND stays writable while mstateen0.CSRIND=0",
    "mstateen_bit_59": "the CSRIND gate is mstateen0 bit 59 rather than bit 60",
}

REQ_S = ["I", "S", "Sscsrind"]
REQ_SH = ["I", "S", "H", "Sscsrind"]
REQ_SHST = ["I", "S", "H", "Sscsrind", "Ssstateen"]
REQ_SM = ["I", "Sm", "Sscsrind"]
REQ_SHM = ["I", "Sm", "S", "H", "Sscsrind"]
REQ_M = ["I", "Sm", "Smcsrind"]
REQ_MS = ["I", "Sm", "S", "Smcsrind"]
REQ_MST = ["I", "Sm", "S", "Smcsrind", "Smstateen"]

ISSUE_NONE = (
    "No riscv-isa-manual issue changes this rule (searched siselect, sireg, vsiselect, miselect, Smcsrind, "
    "Sscsrind, CSRIND; the issues found concern other rules)."
)
ISS_WARL = (
    f"{ISSUE}2032 (closed) asks how a write of a reserved or unimplemented value maps; the answer is the usual WARL "
    "one (any legal value; keeping the old value is only recommended), so the test accepts whatever legal value reads "
    "back. Only miselect is declared WARL; the test treats siselect/vsiselect the same way outside 0..0xFFF."
)
ISS_UNSPEC = (
    f"{ISSUE}2542 (open) and {ISSUE}2070 (closed) restate that a VS-mode sireg* access while vsiselect holds a value "
    "not implemented at HS level is UNSPECIFIED, with illegal-instruction recommended. The test reads UNSPECIFIED here "
    "as: the access behaves as a register or raises a CSR-access exception."
)
ISS_VIRT = (
    f"{ISSUE}2070 (closed): a VS-mode access to a VS CSR by its own address is virtual-instruction, unlike a VS-mode "
    f"sireg* access. Open: {ISSUE}2554 (VU-mode sireg* with vsiselect in 0x40-0x5F and menvcfg.CDE=0) and "
    f"{ISSUE}2668 (VU-mode sireg* with an invalid hstatus.VGEIN) ask whether those may be illegal-instruction; "
    "smcsrind.adoc and smcdeleg.adoc (norm:Ssccfg_hyp_vs_or_vu_access_vsireg_illegal) say virtual-instruction for "
    "every VU-mode siselect/sireg* access, which the test follows."
)
ISS_STATEEN = (
    f"{ISSUE}2210 (closed): CSRIND gates the select and alias CSRs themselves; other bits (AIA, IMSIC, CTR) gate the "
    f"state reached through them. {ISSUE}3158 (open): CSRs not listed, such as scountinhibit, are not gated by CSRIND."
)
ISS_HSTATEEN = ISS_STATEEN + " " + ISS_VIRT
NOTE_RO = (
    " A stateen bit may be read-only zero or one, so the test probes that the bit can be both set and cleared and "
    "checks the gated cases only then."
)
NOTE_UNSPEC = (
    "The spec leaves the access UNSPECIFIED and recommends illegal-instruction. The test accepts no trap or "
    "illegal-instruction from M/HS (a virtual-instruction exception exists only at V=1), and also "
    "virtual-instruction from VS, and checks xepc, xtval (0 or the instruction bits) and the mode of any trap."
)
NOTE_ALLOC = (
    "Allocated select ranges used here only as examples of an implemented range: Smaia/Ssaia 0x30-0x3F "
    "(major-interrupt priorities; only even values exist on RV64, so 0x30, 0x32, 0x34 are used), Smctr "
    "0x200-0x2FF. Reserved values used as unimplemented: " + ", ".join(hex(v) for v in RESERVED_SEL) + "."
)


def out(suite: str) -> str:
    """The directory a test is written to: its suite, or the mutant directory."""
    return suite if SUITE == "Smcsrind" else SUITE


def new(suite: str, rule: str, required: list, boot: str = "S", suffix: str = "") -> TestFile:
    return TestFile(out(suite), rule, required=required, march=MARCH, boot=boot, pool=POOL_TRAP, suffix=suffix)


def sel_values(t: TestFile) -> list[tuple[int, str]]:
    """Edges and random values in 0..0xFFF."""
    v = [
        (0, "0"),
        (1, "1"),
        (2, "2"),
        (0x55, "0x55"),
        (0xAA, "0xAA"),
        (0x7FF, "0x7FF"),
        (0x800, "0x800"),
        (0x555, "0x555"),
        (0xAAA, "0xAAA"),
        (0xFFE, "0xFFE"),
        (0xFFF, "0xFFF"),
    ]
    return v + [(t.rand(12), "random") for _ in range(3)]


def big_values(t: TestFile) -> list[tuple[X, str]]:
    """Values outside 0..0xFFF: custom (MSB set) and reserved standard values above the minimum range."""
    return [
        (MSB, "MSB only (custom)"),
        (X((1 << 31) | 0x30, (1 << 63) | 0x30), "MSB | 0x30 (custom)"),
        (X((1 << 31) | 0xFFF, (1 << 63) | 0xFFF), "MSB | 0xFFF (custom)"),
        (X(0xFFFFFFFF, (1 << 64) - 1), "all ones (custom)"),
        (X(0x1000, 0x1000), "0x1000 (standard, above 0xFFF)"),
        (X(1 << 30, 1 << 62), "bit XLEN-2 (standard)"),
        (X(0x7FFFFFFF, (1 << 63) - 1), "MAX: all ones but the MSB (standard)"),
        (X(0x80000123, 0x80000123), "0x80000123 (custom on RV32, standard on RV64)"),
        (X(t.rand(32) | (1 << 31), t.rand(64) | (1 << 63)), "random with MSB set"),
    ]


def readback(t: TestFile, csr: str, value: int | X, note: str, reg: str = "x7") -> None:
    lab = t.label("rd")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr {reg}, {macro(csr)}")
    t.check(reg, value, lab, f"{csr} reads back {note}")


def exact_values(t: TestFile, csr: str, values: list[tuple[int, str]], width_mut: int | None = None) -> None:
    """Write each value to csr and read it back exactly (width_mut: a mutant's register width)."""
    for v, note in values:
        set_sel(t, csr, v)
        exp = v & ((1 << width_mut) - 1) if width_mut else v
        readback(t, csr, exp, f"{hex(v)} ({note})")


def forms_exact(t: TestFile, csr: str, desc: str) -> None:
    """All eight CSR forms on a select CSR, with old and rs1 values in 0..0xFFF: rd is the old value and the new
    value is exactly what the form defines (every result stays in 0..0xFFF)."""
    for form in FORMS:
        old, rs = t.rand(12), t.rand(12)
        set_sel(t, csr, old, "x7")
        t.load("x6", rs, "rs1 value")
        lab = t.label("form")
        t.emit(f"{lab}:", 0)
        t.emit(form[0].format(c=macro(csr)))
        rd, new_v = form_value(form, old, rs, 12)
        if MUT == "read_form_writes" and form[1] in (2, 6) and (form[3] == 0):
            new_v = 0
        if rd is not None:
            t.check("x7", rd, lab, f"{form[4]} of {csr} ({desc}) returns the old value {hex(old)}")
        t.emit(f"csrr x7, {macro(csr)}")
        t.check("x7", new_v, lab, f"{form[4]} of {csr} ({desc}) leaves {hex(new_v)}")


def stable(t: TestFile, csr: str, value: X, note: str, after: int | None) -> None:
    """Write value, read R; writing R back reads R (a legal value is retained). Then, when after is given, an
    in-range write of `after` reads back exactly (nothing of the out-of-range value sticks)."""
    t.comment(f"{csr} = {note}")
    t.load("x6", value, note)
    lab = t.label("warl")
    t.emit(f"csrw {macro(csr)}, x6")
    t.emit(f"csrr x7, {macro(csr)}")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrw {macro(csr)}, x7")
    t.emit(f"csrr x8, {macro(csr)}")
    eq_check(t, "x7", "x8", lab, f"{csr} after writing {note}: rewriting the value read back retains it", "x9")
    if after is not None:
        set_sel(t, csr, after)
        exp = after
        if MUT == "msb_sticky" and csr == "siselect":
            exp = X((1 << 31) | after, (1 << 63) | after)
        readback(t, csr, exp, f"{hex(after)} after the value {note}")


def vs_read(t: TestFile, csr: str, reg: str = "x7") -> None:
    """Read csr in VS-mode into reg (window: no trap)."""
    t.window("VS", [f"csrr {reg}, {macro(csr)}"], "ok", f"read of {csr}")


def vs_write(t: TestFile, csr: str, reg: str = "x6") -> None:
    t.window("VS", [f"csrw {macro(csr)}, {reg}"], "ok", f"write of {csr}")


# ---------------------------------------------------------------- Sscsrind: siselect
def t_siselect_min_range() -> list[TestFile]:
    rule = "siselect_min_range"
    text = "The `siselect` register will support the value range 0..0xFFF at a minimum."
    ctx = (
        "siselect (0x150) is an SRW XLEN-bit CSR, required when S-mode is implemented. The note explains that the "
        "full 0..0xFFF range is required, even where most of it is reserved or inaccessible, so that M-mode can "
        "emulate indirectly accessed registers. Machine- and supervisor-level select values are separate address "
        "spaces (note in the introduction), and vsiselect substitutes for siselect only at V=1."
    )
    t = new("Sscsrind", rule, REQ_S)
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx,
        issues=ISSUE_NONE,
        plan="1. S-mode: write 0, 1, 2, 0x55, 0xAA, 0x7FF, 0x800, 0x555, 0xAAA, 0xFFE, 0xFFF and three random "
        "12-bit values to siselect and read each back exactly.\n"
        "2. All eight CSR instruction forms on siselect with old and rs1 values in 0..0xFFF: rd is the old value, "
        "and the new value is the one the form defines (rs1=x0 and uimm=0 do not write).\n"
        "3. With H: siselect and vsiselect are separate registers in HS-mode: a write of one leaves the other.",
    )
    t.comment("1. every value in 0..0xFFF is held exactly")
    exact_values(t, "siselect", sel_values(t), 8 if MUT == "siselect_8bit" else None)
    t.comment("2. CSR instruction forms")
    forms_exact(t, "siselect", "S-mode")
    with t.only_if(H):
        t.comment("3. siselect and vsiselect are separate registers at V=0")
        set_sel(t, "vsiselect", 0x5A5)
        set_sel(t, "siselect", 0x3C3)
        readback(t, "vsiselect", 0x3C3 if MUT == "siselect_is_vsiselect" else 0x5A5, "0x5A5 after a siselect write")
        readback(t, "siselect", 0x3C3, "0x3C3")
        set_sel(t, "vsiselect", 0x0F0)
        readback(t, "siselect", 0x0F0 if MUT == "siselect_is_vsiselect" else 0x3C3, "0x3C3 after a vsiselect write")
    out_ = [t]

    t = new("Sscsrind", rule, REQ_SM, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx + " siselect is accessible from M-mode as well, with the same contents.",
        issues=ISSUE_NONE,
        plan="1. M-mode: edge and random values in 0..0xFFF written to siselect read back exactly.\n"
        "2. M-mode writes are read back in S-mode, and S-mode writes in M-mode.\n"
        "3. All eight CSR forms on siselect in M-mode.",
    )
    exact_values(t, "siselect", sel_values(t)[:8], 8 if MUT == "siselect_8bit" else None)
    for v in (0xABC, 0x123):
        set_sel(t, "siselect", v)
        t.window("S", [f"csrr x7, {macro('siselect')}"], "ok", "read of siselect")
        lab = t.label("sview")
        t.emit(f"{lab}:", 0)
        t.check("x7", v, lab, f"S-mode reads {hex(v)} written in M-mode")
    t.emit("li x6, 0x9E7")
    t.window("S", [f"csrw {macro('siselect')}, x6"], "ok", "write of siselect")
    readback(t, "siselect", 0x9E7, "0x9E7 written in S-mode (M-mode read)")
    forms_exact(t, "siselect", "M-mode")
    out_.append(t)
    return out_


def t_siselect_msb_op() -> list[TestFile]:
    t = new("Sscsrind", "siselect_msb_op", REQ_S)
    t.describe(
        rule_text="Values of `siselect` with the most-significant bit set (bit XLEN - 1 = 1) are designated only "
        "for custom use, presumably for accessing custom registers through the alias CSRs. Values of `siselect` "
        "with the most-significant bit clear are designated only for standard use and are reserved until allocated "
        "to a standard architecture extension. If XLEN is changed, the most-significant bit of `siselect` moves to "
        "the new position, retaining its value from before.",
        source=CSRIND,
        context="An implementation need not support any custom value (note on miselect), and siselect need hold "
        "values above 0xFFF only for extensions that use them (siselect_min_range), so siselect is WARL outside "
        "0..0xFFF: a write of a custom or large value may read back as any legal value. What is constrained is that "
        "the value read back is legal (rewriting it retains it) and that the MSB and the bits above 0xFFF do not "
        "stick: a following write in 0..0xFFF reads back exactly. No configuration can change SXLEN, so the XLEN "
        "change clause is not tested.",
        issues=ISS_WARL,
        plan="1. S-mode: write MSB only, MSB|0x30, MSB|0xFFF, all ones, a random MSB-set value (custom), and 0x1000, "
        "bit XLEN-2, all ones but the MSB, 0x80000123 (standard): rewriting the value read back retains it, and a "
        "following in-range write (a different one each time) reads back exactly.\n"
        "2. With H: the same in HS-mode on vsiselect.",
    )
    for i, (v, note) in enumerate(big_values(t)):
        stable(t, "siselect", v, note, 0x100 + 0x11 * i)
    with t.only_if(H):
        for i, (v, note) in enumerate(big_values(t)[:5]):
            stable(t, "vsiselect", v, note, 0x200 + 0x13 * i)
    return [t]


def t_sireg_illegal() -> list[TestFile]:
    rule = "sireg_access_on_illegal_siselect"
    text = (
        "The behavior upon accessing `sireg*` from M-mode or S-mode, while `siselect` holds a value that is not "
        "implemented at supervisor level, is UNSPECIFIED."
    )
    ctx = (
        "The recommendation is an illegal-instruction exception, so that M-mode can emulate the access. The "
        "hypervisor section adds the matching (untagged) statement for vsireg* from M/HS-mode and sireg* (really "
        "vsireg*) from VS-mode while vsiselect holds a value not implemented at HS level, with illegal-instruction "
        "recommended and virtual-instruction typical when the value is implemented at HS but not VS level. "
        + NOTE_ALLOC
    )
    t = new("Sscsrind", rule, REQ_S)
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx,
        issues=ISS_UNSPEC + " " + NOTE_UNSPEC,
        plan="1. S-mode: for each reserved siselect value, a read (csrrs rs1=x0) and a write (csrrw rd=x0) of each of "
        "sireg..sireg6: no trap or illegal-instruction.\n"
        "2. With H, HS-mode: vsireg..vsireg6 read and write with reserved vsiselect values: no trap or "
        "illegal-instruction.\n"
        "3. With H, VS-mode: sireg..sireg6 (really vsireg*) read and write with reserved vsiselect values: no trap, "
        "illegal- or virtual-instruction.",
    )
    for v in RESERVED_SEL:
        set_sel(t, "siselect", v)
        sweep(t, "S", SIREGS, RW_FORMS, ["ok", ILLEGAL], f"siselect={hex(v)} reserved")
    with t.only_if(H):
        for v in RESERVED_SEL[::2]:
            set_sel(t, "vsiselect", v)
            sweep(t, "S", VSIREGS, RW_FORMS, ["ok", ILLEGAL], f"vsiselect={hex(v)} reserved")
            sweep(t, "VS", SIREGS, RW_FORMS, ["ok", ILLEGAL, VIRTUAL], f"vsiselect={hex(v)} reserved")
    out_ = [t]

    t = new("Sscsrind", rule, REQ_SM, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx,
        issues=ISS_UNSPEC + " " + NOTE_UNSPEC,
        plan="1. M-mode: for each reserved siselect value, a read and a write of each of sireg..sireg6: no trap or "
        "illegal-instruction.\n"
        "2. With H, M-mode: vsireg..vsireg6 with reserved vsiselect values: no trap or illegal-instruction.",
    )
    for v in RESERVED_SEL:
        set_sel(t, "siselect", v)
        sweep(t, "M", SIREGS, RW_FORMS, ["ok", ILLEGAL], f"siselect={hex(v)} reserved")
    with t.only_if(H):
        for v in RESERVED_SEL[1::2]:
            set_sel(t, "vsiselect", v)
            sweep(t, "M", VSIREGS, RW_FORMS, ["ok", ILLEGAL], f"vsiselect={hex(v)} reserved")
    out_.append(t)
    return out_


def independence(t: TestFile, sel: str, reg: str, sels: list[int], mut: bool) -> None:
    """Through `reg`, write different values at each select in sels and read each back (x7, x8, x9). Then reselect
    each and require the value read back first: a write at one select must not land at another."""
    holders = ["x7", "x8", "x9"]
    for s, h in zip(sels, holders):
        set_sel(t, sel, s)
        t.load("x6", t.rand_x(), "pattern")
        t.emit(f"csrw {macro(reg)}, x6")
        t.emit(f"csrr {h}, {macro(reg)}")
    for s, h in zip(sels, holders):
        set_sel(t, sel, s)
        lab = t.label("reread")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x1, {macro(reg)}")
        exp = holders[len(sels) - 1] if mut else h
        eq_check(
            t,
            "x1",
            exp,
            lab,
            f"{reg} at {sel}={hex(s)} still holds what was written there after writes at other select values",
            "x6",
        )


def forms_dynamic(t: TestFile, reg: str, desc: str) -> None:
    """Forms that do not write (rs1=x0, uimm=0) return the current value and leave it; csrrw returns the old
    value. Values are WARL, so expectations come from reads of the register itself."""
    t.load("x6", t.rand_x(), "pattern")
    t.emit(f"csrw {macro(reg)}, x6")
    for form in READ_FORMS:
        lab = t.label("rform")
        t.emit(f"csrr x9, {macro(reg)}")
        t.emit(f"{lab}:", 0)
        t.emit(form[0].format(c=macro(reg)))
        eq_check(t, "x7", "x9", lab, f"{form[4]} of {reg} ({desc}) returns the current value", "x6")
        t.emit(f"csrr x8, {macro(reg)}")
        eq_check(t, "x8", "x9", lab, f"{form[4]} of {reg} ({desc}) does not write it", "x6")
    lab = t.label("swap")
    t.emit(f"csrr x9, {macro(reg)}")
    t.load("x6", t.rand_x(), "new value")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrrw x7, {macro(reg)}, x6")
    eq_check(t, "x7", "x9", lab, f"csrrw of {reg} ({desc}) returns the old value", "x6")


def t_sireg_legal() -> list[TestFile]:
    rule = "sireg_access_on_legal_siselect"
    text = (
        "Otherwise, attempts to access `sireg*` from M-mode or S-mode while `siselect` holds a number in a "
        "standard-defined and implemented range result in specific behavior that, for each combination of "
        "`siselect` and `sireg__i__`, is defined by the extension to which the `siselect` value is allocated."
    )
    ctx = (
        "The behavior itself belongs to the extension that owns the range (Ssaia, Ssccfg, Ssctr suites). What is "
        "common to every such range is that siselect selects the register sireg accesses, so writes at one select "
        "value do not land at another, and that sireg obeys the CSR instruction forms. " + NOTE_ALLOC + " Without "
        "Ssaia the test checks nothing. The values held are WARL (priority fields may be read-only), so "
        "expectations come from reading the registers."
    )
    t = new("Sscsrind", rule, REQ_S)
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx,
        issues=ISSUE_NONE,
        plan="With Ssaia, S-mode:\n"
        "1. siselect 0x30, 0x32, 0x34: sireg reads without a trap.\n"
        "2. Write a different random value through sireg at each, read each back, then reselect each: sireg returns "
        "the value read back at that select, not the last one written.\n"
        "3. At 0x30: csrrs/csrrc rs1=x0 and csrrsi/csrrci uimm=0 return the current value and do not write it; "
        "csrrw returns the old value.\n"
        "4. Restore zero at each.",
    )
    with t.only_if(SSAIA):
        for s in (0x30, 0x32, 0x34):
            set_sel(t, "siselect", s)
            access(t, "S", "sireg", FORMS[0], "ok", f"siselect={hex(s)} (Ssaia)")
        independence(t, "siselect", "sireg", [0x30, 0x32, 0x34], MUT == "select_ignored_s")
        set_sel(t, "siselect", 0x30)
        forms_dynamic(t, "sireg", "siselect=0x30")
        for s in (0x30, 0x32, 0x34):
            set_sel(t, "siselect", s)
            t.emit(f"csrw {macro('sireg')}, x0")
    out_ = [t]

    t = new("Sscsrind", rule, REQ_SM, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx,
        issues=ISSUE_NONE,
        plan="With Ssaia:\n"
        "1. M-mode, siselect 0x30, 0x32, 0x34: writes through sireg land only at their own select value.\n"
        "2. M-mode and S-mode access the same register: an M-mode write through sireg at siselect=0x30 is read in "
        "S-mode, and an S-mode write is read in M-mode.\n"
        "3. M-mode CSR forms on sireg at 0x30 (rs1=x0 and uimm=0 do not write; csrrw returns the old value).",
    )
    with t.only_if(SSAIA):
        independence(t, "siselect", "sireg", [0x30, 0x32, 0x34], MUT == "select_ignored_s")
        set_sel(t, "siselect", 0x30)
        t.load("x6", t.rand_x(), "pattern")
        t.emit(f"csrw {macro('sireg')}, x6")
        t.emit(f"csrr x9, {macro('sireg')}")
        t.window("S", [f"csrr x7, {macro('sireg')}"], "ok", "read of sireg at siselect=0x30")
        lab = t.label("ms")
        t.emit(f"{lab}:", 0)
        eq_check(t, "x7", "x9", lab, "S-mode sireg read at siselect=0x30 returns the M-mode write", "x6")
        t.load("x6", t.rand_x(), "pattern")
        t.window("S", [f"csrw {macro('sireg')}, x6", f"csrr x7, {macro('sireg')}"], "ok", "write of sireg")
        lab = t.label("sm")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x9, {macro('sireg')}")
        eq_check(t, "x7", "x9", lab, "M-mode sireg read at siselect=0x30 returns the S-mode write", "x6")
        forms_dynamic(t, "sireg", "M-mode, siselect=0x30")
        for s in (0x30, 0x32, 0x34):
            set_sel(t, "siselect", s)
            t.emit(f"csrw {macro('sireg')}, x0")
    out_.append(t)
    return out_


# ---------------------------------------------------------------- Sscsrind: vsiselect and V=1
def t_vsiselect_min_range() -> list[TestFile]:
    t = new("Sscsrind", "vsiselect_min_range", REQ_SH)
    t.describe(
        rule_text="The `vsiselect` register will support the value range 0..0xFFF at a minimum.",
        source=CSRIND,
        context="vsiselect (0x250) is an HRW XLEN-bit CSR, required with H. It substitutes for siselect in VS-mode, "
        "so a VS-mode siselect access reads and writes vsiselect, and HS-mode's siselect is untouched.",
        issues=ISSUE_NONE,
        plan="1. HS-mode: edge and random values in 0..0xFFF written to vsiselect read back exactly.\n"
        "2. All eight CSR forms on vsiselect in HS-mode.\n"
        "3. VS-mode writes of siselect (0x7FF, 0xFFF, 0x800, random) read back in VS-mode and in HS-mode through "
        "vsiselect, and leave HS-mode's siselect (0x0A5).\n"
        "4. HS-mode writes of vsiselect (0xFFE, 0x001, random) read back in VS-mode through siselect.\n"
        "5. All eight CSR forms on siselect in VS-mode, with the old value set through vsiselect in HS-mode and the "
        "result read through vsiselect.",
    )
    t.comment("1. HS-mode: every value in 0..0xFFF is held exactly")
    exact_values(t, "vsiselect", sel_values(t), 8 if MUT == "vsiselect_8bit" else None)
    t.comment("2. CSR instruction forms in HS-mode")
    forms_exact(t, "vsiselect", "HS-mode")
    t.comment("3. VS-mode siselect writes land in vsiselect")
    set_sel(t, "siselect", 0x0A5)
    for v in (0x7FF, 0xFFF, 0x800, t.rand(12)):
        t.emit(f"li x6, {v}")
        t.window("VS", [f"csrw {macro('siselect')}, x6", f"csrr x7, {macro('siselect')}"], "ok", "siselect write")
        lab = t.label("vs")
        t.emit(f"{lab}:", 0)
        exp_v = v & 0xFF if MUT == "vsiselect_8bit" else v
        t.check("x7", exp_v, lab, f"VS-mode siselect reads back {hex(v)}")
        t.emit(f"csrr x7, {macro('vsiselect')}")
        t.check(
            "x7",
            0 if MUT == "vs_siselect_not_substituted" else exp_v,
            lab,
            f"HS-mode vsiselect reads {hex(v)} written by VS-mode siselect",
        )
        t.emit(f"csrr x7, {macro('siselect')}")
        t.check(
            "x7",
            v if MUT == "vs_siselect_not_substituted" else 0x0A5,
            lab,
            "HS-mode siselect is unchanged (0x0A5) by the VS-mode write",
        )
        if MUT == "vs_siselect_not_substituted":
            set_sel(t, "siselect", 0x0A5)
    t.comment("4. HS-mode vsiselect writes are read by VS-mode siselect")
    for v in (0xFFE, 0x001, t.rand(12)):
        set_sel(t, "vsiselect", v)
        vs_read(t, "siselect")
        lab = t.label("vsr")
        t.emit(f"{lab}:", 0)
        t.check(
            "x7",
            0x0A5 if MUT == "vs_siselect_not_substituted" else v,
            lab,
            f"VS-mode siselect reads {hex(v)} written to vsiselect",
        )
    t.comment("5. CSR forms on siselect in VS-mode")
    for form in FORMS:
        old, rs = t.rand(12), t.rand(12)
        set_sel(t, "vsiselect", old, "x7")
        t.load("x6", rs, "rs1 value")
        lab = t.window("VS", [form[0].format(c=macro("siselect"))], "ok", f"{form[4]} of siselect")
        rd, new_v = form_value(form, old, rs, 12)
        if rd is not None:
            t.check("x7", rd, lab, f"VS-mode {form[4]} of siselect returns the old vsiselect {hex(old)}")
        t.emit(f"csrr x7, {macro('vsiselect')}")
        t.check("x7", new_v, lab, f"VS-mode {form[4]} of siselect leaves vsiselect = {hex(new_v)}")
    return [t]


def t_vsiselect_msb_op() -> list[TestFile]:
    t = new("Sscsrind", "vsiselect_msb_op", REQ_SH)
    t.describe(
        rule_text="Values of `vsiselect` with the most-significant bit set (bit XLEN - 1 = 1) are designated only "
        "for custom use, presumably for accessing custom registers through the alias CSRs. Values of `vsiselect` "
        "with the most-significant bit clear are designated only for standard use and are reserved until allocated "
        "to a standard architecture extension. If XLEN is changed, the most-significant bit of `vsiselect` moves to "
        "the new position, retaining its value from before.",
        source=CSRIND,
        context="As for siselect_msb_op: custom values need not be supported and vsiselect is WARL outside "
        "0..0xFFF, so the test checks that the value read back is legal (rewriting it retains it) and that nothing "
        "sticks after an in-range write. VSXLEN cannot change on any configuration, so the XLEN-change clause is "
        "not tested.",
        issues=ISS_WARL,
        plan="1. HS-mode: write custom (MSB-set) and standard values above 0xFFF to vsiselect: rewriting the value "
        "read back retains it, and a following in-range write reads back exactly.\n"
        "2. VS-mode: the same through siselect (really vsiselect) for MSB only and all ones; the HS-mode vsiselect "
        "read matches the VS-mode read.",
    )
    for i, (v, note) in enumerate(big_values(t)):
        stable(t, "vsiselect", v, note, 0x300 + 0x17 * i)
    for v, note in big_values(t)[:4:3]:
        t.load("x6", v, note)
        t.window(
            "VS",
            [
                f"csrw {macro('siselect')}, x6",
                f"csrr x7, {macro('siselect')}",
                f"csrw {macro('siselect')}, x7",
                f"csrr x8, {macro('siselect')}",
            ],
            "ok",
            f"siselect = {note}",
        )
        lab = t.label("vsmsb")
        t.emit(f"{lab}:", 0)
        eq_check(t, "x7", "x8", lab, f"VS-mode siselect after {note}: rewriting the value read back retains it", "x9")
        t.emit(f"csrr x8, {macro('vsiselect')}")
        eq_check(t, "x7", "x8", lab, f"HS-mode vsiselect matches the VS-mode siselect read after {note}", "x9")
        set_sel(t, "vsiselect", 0x456)
        readback(t, "vsiselect", 0x456, f"0x456 after {note}")
    return [t]


def t_virtual_inst_fault() -> list[TestFile]:
    t = new("Sscsrind", "Sscsrind_virtual_inst_fault", REQ_SH)
    t.describe(
        rule_text="A virtual-instruction exception is raised for attempts from VS-mode or VU-mode to directly "
        "access `vsiselect` or `vsireg*`, or attempts from VU-mode to access `siselect` or `sireg*`.",
        source=CSRIND,
        context="The hypervisor's usual HS-qualified rule does not apply to sireg*/vsireg*; this section's rules do. "
        "With Smstateen, mstateen0.CSRIND=0 overrides this with illegal-instruction (Sscsrind_csrs_access_control); "
        "the framework boots with mstateen0.CSRIND=1 and hstateen0.CSRIND=1, so the virtual-instruction rule "
        "applies. U-mode (V=0) accesses are illegal-instruction (S- and HS-level CSRs from U-mode), and from "
        "VS-mode siselect (really vsiselect) is accessible. Select values are swept for VU-mode because the rule "
        "does not depend on them.",
        issues=ISS_VIRT,
        plan="1. VS-mode: vsiselect and vsireg..vsireg6 with all eight CSR forms: virtual-instruction.\n"
        "2. VU-mode: siselect and vsiselect with all eight forms, sireg*, vsireg* with a read and a write: "
        "virtual-instruction.\n"
        "3. VU-mode sireg read with vsiselect = 0, 0x30, 0x40, 0x70, 0x200, 0xFFF: virtual-instruction.\n"
        "4. Contrasts: VS-mode siselect read and HS-mode vsiselect read succeed; U-mode siselect, sireg, vsiselect "
        "and vsireg reads raise illegal-instruction.\n"
        "Each trap: xepc, xtval 0 or the instruction bits, and the mode it came from.",
    )
    set_sel(t, "vsiselect", 0)
    vs_direct = "ok" if MUT == "vs_vsiselect_ok" else VIRTUAL
    t.comment("1. VS-mode direct access to vsiselect/vsireg*")
    sweep(t, "VS", ["vsiselect"], FORMS, vs_direct, "VS-mode, direct VS CSR")
    sweep(t, "VS", VSIREGS, FORMS, vs_direct, "VS-mode, direct VS CSR")
    t.comment("2. VU-mode")
    vu = ILLEGAL if MUT == "vu_illegal" else VIRTUAL
    sweep(t, "VU", ["siselect"], FORMS, vu, "VU-mode")
    sweep(t, "VU", ["vsiselect"], FORMS, VIRTUAL, "VU-mode")
    sweep(t, "VU", SIREGS, RW_FORMS, vu, "VU-mode")
    sweep(t, "VU", VSIREGS, RW_FORMS, VIRTUAL, "VU-mode")
    t.comment("3. VU-mode, whatever vsiselect holds")
    for v in SWEEP_SEL:
        set_sel(t, "vsiselect", v)
        access(t, "VU", "sireg", FORMS[0], vu, f"VU-mode, vsiselect={hex(v)}")
    t.comment("4. contrasts")
    vs_read(t, "siselect")
    access(t, "S", "vsiselect", FORMS[0], "ok", "HS-mode")
    u = VIRTUAL if MUT == "u_virtual" else ILLEGAL
    for c in ("siselect", "sireg", "vsiselect", "vsireg"):
        access(t, "U", c, FORMS[0], u, "U-mode (V=0)")
    return [t]


def ctr_freeze(t: TestFile, on: bool, machine: bool = False) -> None:
    """Set (and clear sctrctl/vsctrctl, and mctrctl in M-mode) or clear sctrstatus.FROZEN (bit 31)."""
    t.comment(f"sctrstatus.FROZEN = {int(on)}")
    t.emit("li x6, 1")
    t.emit("slli x6, x6, 31")
    t.emit(f"{'csrs' if on else 'csrc'} CSR_SCTRSTATUS, x6")
    if on:
        t.emit("csrw CSR_SCTRCTL, x0")
        t.emit("csrw CSR_VSCTRCTL, x0")
        if machine:
            t.emit("csrw CSR_MCTRCTL, x0")


def t_vsireg_legal() -> list[TestFile]:
    text = (
        "Otherwise, while `vsiselect` holds a number in a standard-defined and implemented range, attempts "
        "to access `vsireg*` from a sufficiently privileged mode, or to access `sireg*` (really `vsireg*`) from "
        "VS-mode, result in specific behavior that, for each combination of `vsiselect` and `vsireg__i__`, is "
        "defined by the extension to which the `vsiselect` value is allocated."
    )
    t = new("Sscsrind", "vsireg_access_on_legal_vsiselect", REQ_SH)
    t.describe(
        rule_text=text,
        source=CSRIND,
        context="The behavior per value belongs to the owning extension. What every range shares is the VS "
        "substitution: a VS-mode sireg* access is a vsireg* access selected by vsiselect, not by siselect. The only "
        "VS-level range that holds plain register state on the configurations is Smctr's 0x200-0x2FF (CTR entry "
        "registers: sireg/vsireg = ctrsource, sireg2/vsireg2 = ctrtarget, with one set of entries for both), used "
        "here with entry 0 selected by vsiselect and entry 1 by siselect. Without Ssctr the test checks nothing. "
        "Entry fields are WARL, so expectations come from reading the registers. Recorded transfers push entries "
        "down (smctr.adoc norm:ctr_stack), and the windows' xRET and T-SBI ecall are transfers, so the test first "
        'freezes CTR (sctrstatus.FROZEN=1, "inhibit transfer recording") and clears sctrctl and vsctrctl.',
        issues=ISSUE_NONE,
        plan="With Ssctr, after freezing CTR, for sireg/vsireg and sireg2/vsireg2:\n"
        "1. HS-mode: siselect=0x201, write a random value through sireg* and read it back (R1); vsiselect=0x200, "
        "write a different value through vsireg* and read it back (R0).\n"
        "2. VS-mode sireg* read returns R0 (vsireg* at vsiselect), not R1.\n"
        "3. VS-mode write of a third value through sireg*, read back in VS-mode: HS-mode vsireg* reads the same, and "
        "HS-mode sireg* (siselect=0x201) still reads R1.\n"
        "4. Restore zero in both entries.",
    )
    with t.only_if(SSCTR):
        ctr_freeze(t, True)
        for sreg, vreg in (("sireg", "vsireg"), ("sireg2", "vsireg2")):
            t.comment(f"{sreg} in VS-mode is {vreg}")
            set_sel(t, "siselect", 0x201)
            t.load("x6", t.rand_x(), "entry 1 pattern")
            t.emit(f"csrw {macro(sreg)}, x6")
            t.emit(f"csrr x9, {macro(sreg)}")
            set_sel(t, "vsiselect", 0x200)
            t.load("x6", t.rand_x(), "entry 0 pattern")
            t.emit(f"csrw {macro(vreg)}, x6")
            t.emit(f"csrr x8, {macro(vreg)}")
            vs_read(t, sreg)
            lab = t.label("vsr")
            t.emit(f"{lab}:", 0)
            exp = "x9" if MUT == "vs_sireg_uses_siselect" else "x8"
            eq_check(t, "x7", exp, lab, f"VS-mode {sreg} reads {vreg} at vsiselect=0x200, not {sreg} at siselect", "x6")
            t.load("x6", t.rand_x(), "VS pattern")
            t.window("VS", [f"csrw {macro(sreg)}, x6", f"csrr x7, {macro(sreg)}"], "ok", f"write of {sreg}")
            lab = t.label("vsw")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x8, {macro(vreg)}")
            eq_check(t, "x7", "x8", lab, f"HS-mode {vreg} reads what VS-mode wrote through {sreg}", "x6")
            t.emit(f"csrr x8, {macro(sreg)}")
            eq_check(t, "x8", "x9", lab, f"HS-mode {sreg} at siselect=0x201 is unchanged by the VS-mode write", "x6")
            t.emit(f"csrw {macro(sreg)}, x0")
            t.emit(f"csrw {macro(vreg)}, x0")
        ctr_freeze(t, False)
    out_ = [t]

    t = new("Sscsrind", "vsireg_access_on_legal_vsiselect", REQ_SHM, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=CSRIND,
        context="M-mode is a sufficiently privileged mode for vsireg*. With Smctr, vsiselect 0x200-0x2FF reaches "
        'the same CTR entry registers as siselect 0x200-0x2FF (smctr.adoc norm:vsiselect_op, "There is not a '
        'separate set of entry registers for V=1"), so an M-mode write through vsireg* is read through sireg* at '
        "the same entry and the reverse. CTR is frozen and mctrctl, vsctrctl cleared first. Entry fields are WARL, "
        "so expectations come from reads. Without Ssctr the test checks nothing.",
        issues=ISSUE_NONE,
        plan="With Ssctr, M-mode, for vsireg/sireg and vsireg2/sireg2:\n"
        "1. Zero entry 3 through sireg* (siselect=0x203) and write entry 4 (siselect=0x204). vsiselect=0x203: write "
        "a random value through vsireg* and read it back (R); siselect=0x203: sireg* reads R.\n"
        "2. Write another value through sireg* and read it back (S): vsireg* reads S.\n"
        "3. siselect=0x204: sireg* reads its own value, not S (the select picks the entry).\n"
        "4. Restore zero.",
    )
    with t.only_if(SSCTR):
        ctr_freeze(t, True, machine=True)
        for sreg, vreg in (("sireg", "vsireg"), ("sireg2", "vsireg2")):
            t.comment(f"M-mode {vreg} and {sreg} reach the same entry")
            set_sel(t, "siselect", 0x203)
            t.emit(f"csrw {macro(sreg)}, x0")
            set_sel(t, "siselect", 0x204)
            t.load("x6", t.rand_x(), "entry 4 pattern")
            t.emit(f"csrw {macro(sreg)}, x6")
            t.emit(f"csrr x9, {macro(sreg)}")
            set_sel(t, "vsiselect", 0x203)
            t.load("x6", t.rand_x(), "entry 3 pattern")
            t.emit(f"csrw {macro(vreg)}, x6")
            t.emit(f"csrr x8, {macro(vreg)}")
            set_sel(t, "siselect", 0x203)
            lab = t.label("mv")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {macro(sreg)}")
            if MUT == "separate_vs_entries":
                t.check("x7", 0, lab, f"M-mode {sreg} at siselect=0x203 keeps its own (zero) entry")
            else:
                eq_check(
                    t, "x7", "x8", lab, f"M-mode {sreg} at siselect=0x203 reads the {vreg} write at vsiselect=0x203"
                )
            t.load("x6", t.rand_x(), "second pattern")
            t.emit(f"csrw {macro(sreg)}, x6")
            t.emit(f"csrr x8, {macro(sreg)}")
            lab = t.label("ms")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {macro(vreg)}")
            eq_check(t, "x7", "x8", lab, f"M-mode {vreg} at vsiselect=0x203 reads the {sreg} write at siselect=0x203")
            set_sel(t, "siselect", 0x204)
            lab = t.label("sel")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {macro(sreg)}")
            eq_check(t, "x7", "x9", lab, f"M-mode {sreg} at siselect=0x204 still reads its own entry")
            t.emit(f"csrw {macro(sreg)}, x0")
            set_sel(t, "siselect", 0x203)
            t.emit(f"csrw {macro(sreg)}, x0")
        ctr_freeze(t, False)
    out_.append(t)
    return out_


def t_hyp_access_control() -> list[TestFile]:
    t = new("Sscsrind", "hypervisor_impl_csrs_access_control", REQ_SHST)
    t.describe(
        rule_text="If the hypervisor extension is implemented, the same bit is defined also in hypervisor CSR "
        "`hstateen0`, but controls access to only `siselect` and `sireg*` (really `vsiselect` and `vsireg*`), which "
        "is the state potentially accessible to a virtual machine executing in VS or VU-mode. When `hstateen0`[60]=0 "
        "and `mstateen0`[60]=1, all attempts from VS or VU-mode to access `siselect` or `sireg*` raise a "
        "virtual-instruction exception, not an illegal-instruction exception, regardless of the value of "
        "`vsiselect` or any other mstateen bit.",
        source=CSRIND,
        context="hstateen0.CSRIND is bit 60 (hstateen0h bit 28 on RV32). The framework boots with "
        "mstateen0.CSRIND=1 (when Smstateen is visible) and hstateen0.CSRIND=1. An hstateen bit may be read-only "
        "zero, or one if the mstateen bit is, so the test probes that it can be set and cleared and checks the gated "
        "cases only then. hstateen0 does not control HS-mode access. VS/VU-mode direct accesses to vsiselect/vsireg* "
        'stay virtual-instruction: "regardless of any other mstateen bits, if mstateen0[60] = 1, a '
        "virtual-instruction exception is raised ... for all attempts from VS-mode or VU-mode to directly access "
        'vsiselect or vsireg*" (same section).',
        issues=ISS_HSTATEEN,
        plan="With hstateen0.CSRIND cleared (when it can be):\n"
        "1. VS-mode: siselect and sireg with all eight forms, sireg2..sireg6 with a read and a write: "
        "virtual-instruction.\n"
        "2. VS-mode sireg read with vsiselect = 0, 0x30, 0x40, 0x70, 0x200, 0xFFF: virtual-instruction.\n"
        "3. VU-mode: siselect and sireg..sireg6 read and write, vsiselect read: virtual-instruction.\n"
        "4. VS-mode vsiselect and vsireg read and write (direct access): still virtual-instruction.\n"
        "5. With Smstateen: mstateen0 bits 63 and 0-59 other than CSRIND cleared where writable (AIA, IMSIC, "
        "CONTEXT, CTR, ...): VS-mode siselect, sireg and vsiselect reads still virtual-instruction; then restored "
        "(the other hstateen0 bits are then UNSPECIFIED; only CSRIND is relied on afterwards).\n"
        "6. Negative dependencies: HS-mode siselect, sireg (siselect reserved; any outcome but virtual) and vsiselect "
        "are unaffected (siselect and vsiselect read and write without a trap); U-mode siselect stays "
        "illegal-instruction.\n"
        "7. Transition: hstateen0.CSRIND set again: VS-mode siselect reads and writes without a trap.",
    )
    h_probe(t, "x1")  # x1 = 1 when the bit can be set and cleared (kept for the later branches); left clear
    vs = ILLEGAL if MUT == "hstateen_illegal" else ("ok" if MUT == "hstateen_ignored" else VIRTUAL)
    ro1 = "hstateen0.CSRIND is read-only: nothing gated to check"

    def gated() -> None:
        set_sel(t, "vsiselect", 0)
        t.comment("1. VS-mode siselect/sireg*")
        sweep(t, "VS", ["siselect", "sireg"], FORMS, vs, "hstateen0.CSRIND=0")
        sweep(t, "VS", SIREGS[1:], RW_FORMS, vs, "hstateen0.CSRIND=0")
        t.comment("2. regardless of vsiselect")
        for v in SWEEP_SEL:
            set_sel(t, "vsiselect", v)
            access(t, "VS", "sireg", FORMS[0], vs, f"hstateen0.CSRIND=0, vsiselect={hex(v)}")
        t.comment("3. VU-mode")
        sweep(t, "VU", S_SET, RW_FORMS, VIRTUAL, "hstateen0.CSRIND=0")
        access(t, "VU", "vsiselect", FORMS[0], VIRTUAL, "VU-mode, hstateen0.CSRIND=0")
        t.comment("4. direct VS CSR access stays virtual-instruction")
        direct = ILLEGAL if MUT == "hstateen_direct_illegal" else VIRTUAL
        set_sel(t, "vsiselect", 0)
        sweep(t, "VS", ["vsiselect", "vsireg"], RW_FORMS, direct, "VS-mode direct access, hstateen0.CSRIND=0")
        t.comment("6. negative dependencies")
        hs = ILLEGAL if MUT == "hstateen_gates_hs" else "ok"
        sweep(t, "S", ["siselect", "vsiselect"], RW_FORMS, hs, "HS-mode, hstateen0.CSRIND=0")
        set_sel(t, "siselect", 0x000)
        access(t, "S", "sireg", FORMS[0], ["ok", ILLEGAL], "HS-mode, hstateen0.CSRIND=0, siselect reserved")
        access(t, "U", "siselect", FORMS[0], ILLEGAL, "U-mode, hstateen0.CSRIND=0")

    def other_bits() -> None:
        t.comment("5. regardless of the other mstateen0 bits")
        t.tsbi_csr("READ", "MSTATEEN0")
        t.emit("mv x9, a0")
        with t.rv64_only():
            t.li("a1", 1)
            t.emit("slli a1, a1, 60")
            t.emit("not a1, a1")
            t.tsbi_csr("CLEAR", "MSTATEEN0", "a1")
        with t.rv32_only():
            t.emit("li a1, -1")
            t.tsbi_csr("CLEAR", "MSTATEEN0", "a1")
            t.tsbi_csr("READ", "MSTATEEN0H")
            t.emit("mv x8, a0")
            t.li("a1", ~(1 << 28))
            t.tsbi_csr("CLEAR", "MSTATEEN0H", "a1")
        set_sel(t, "vsiselect", 0x30)
        access(t, "VS", "siselect", FORMS[0], vs, "hstateen0.CSRIND=0, other mstateen0 bits clear")
        access(t, "VS", "sireg", FORMS[0], vs, "hstateen0.CSRIND=0, other mstateen0 bits clear")
        access(t, "VS", "vsiselect", FORMS[0], VIRTUAL, "direct access, hstateen0.CSRIND=0, other mstateen0 bits clear")
        t.tsbi_csr("WRITE", "MSTATEEN0", "x9")
        with t.rv32_only():
            t.tsbi_csr("WRITE", "MSTATEEN0H", "x8")

    def again() -> None:
        t.comment("7. set hstateen0.CSRIND again")
        h_csrind(t, True)
        sweep(t, "VS", ["siselect"], RW_FORMS, "ok", "hstateen0.CSRIND=1 again")

    t.either("x1", gated, lambda: t.comment(ro1))
    with t.only_if(SMSTATEEN):
        t.either("x1", other_bits, lambda: t.comment(ro1))
    t.either("x1", again, lambda: t.comment(ro1))
    h_csrind(t, True)
    return [t]


def t_hstateen0_csrind_op() -> list[TestFile]:
    t = new("Sscsrind", "hstateen0_csrind_op", REQ_SHST)
    t.describe(
        rule_text="The CSRIND bit in `hstateen0` controls access to the `siselect` and the `sireg*`, (really "
        "`vsiselect` and `vsireg*`) CSRs provided by the Sscsrind extensions.",
        source=STATEEN,
        context="CSRIND is hstateen0 bit 60 (hstateen0h bit 28 on RV32). Clear, a VS/VU-mode access raises "
        "virtual-instruction (hypervisor_impl_csrs_access_control). It controls only V=1 accesses. With "
        "Smstateen, the bit is read-only zero while mstateen0.CSRIND=0 (mstateen_lower_priv_roz), and VS-mode "
        "accesses then raise illegal-instruction (Sscsrind_csrs_access_control). The bit may be read-only (one only "
        "if the mstateen0 bit is), so the test probes that it can be set and cleared. After mstateen0.CSRIND returns to 1, hstateen0.CSRIND "
        "holds an UNSPECIFIED value (field modulation), so the test writes it before relying on it.",
        issues=ISS_STATEEN,
        plan="1. HS-mode: clear, set, clear, set hstateen0.CSRIND and read it back (when it can be cleared); the other "
        "hstateen0 bits are unchanged.\n"
        "2. Transitions: VS-mode siselect read and write succeed with the bit set, raise virtual-instruction with "
        "it clear, and succeed again once set.\n"
        "3. The bit does not control HS-mode siselect or vsiselect.\n"
        "4. With Smstateen and mstateen0.CSRIND writable: with mstateen0.CSRIND=0, hstateen0.CSRIND reads 0 and an "
        "HS-mode write of 1 is ignored; a VS-mode siselect read raises illegal-instruction; then mstateen0.CSRIND "
        "and hstateen0.CSRIND are restored.",
    )
    h_probe(t, "x7")

    def writable() -> None:
        for on in (False, True, False, True):
            with t.rv64_only():
                t.emit("csrr x9, CSR_HSTATEEN0")
            with t.rv32_only():
                t.emit("csrr x9, CSR_HSTATEEN0H")
            h_csrind(t, on)
            lab = t.label("hbit")
            t.emit(f"{lab}:", 0)
            h_read_csrind(t, "x7")
            t.check("x7", int(on), lab, f"hstateen0.CSRIND reads {int(on)} after HS-mode {'set' if on else 'clear'}")
            with t.rv64_only():
                t.emit("csrr x8, CSR_HSTATEEN0")
                t.li("x6", 1)
                t.emit("slli x6, x6, 60")
            with t.rv32_only():
                t.emit("csrr x8, CSR_HSTATEEN0H")
                t.li("x6", 1 << 28)
            t.emit("xor x8, x8, x9")
            t.emit("not x6, x6")
            t.emit("and x8, x8, x6")
            t.check("x8", 0, lab, "other hstateen0 bits are unchanged")
            vs = "ok" if on else (ILLEGAL if MUT == "hstateen_illegal" else VIRTUAL)
            if MUT == "hstateen_ignored" and not on:
                vs = "ok"
            sweep(t, "VS", ["siselect"], RW_FORMS, vs, f"hstateen0.CSRIND={int(on)}")
            if not on:
                hs = ILLEGAL if MUT == "hstateen_gates_hs" else "ok"
                sweep(t, "S", ["siselect", "vsiselect"], [FORMS[0]], hs, "HS-mode, hstateen0.CSRIND=0")

    t.either("x7", writable, lambda: t.comment("hstateen0.CSRIND is read-only"))
    h_csrind(t, True)
    with t.only_if(SMSTATEEN):
        t.comment("4. mstateen0.CSRIND=0 makes hstateen0.CSRIND read-only zero")
        m_csrind(t, False)
        m_read_csrind(t, "x7")
        t.emit("xori x7, x7, 1")

        def m_clear() -> None:
            lab = t.label("ro0")
            t.emit(f"{lab}:", 0)
            h_read_csrind(t, "x7")
            t.check("x7", 0, lab, "hstateen0.CSRIND reads 0 while mstateen0.CSRIND=0")
            h_csrind(t, True)
            h_read_csrind(t, "x7")
            t.check(
                "x7",
                1 if MUT == "hstateen_not_ro0" else 0,
                lab,
                "an HS-mode write of 1 to hstateen0.CSRIND is ignored while mstateen0.CSRIND=0",
            )
            access(
                t, "VS", "siselect", FORMS[0], VIRTUAL if MUT == "mstateen_virtual" else ILLEGAL, "mstateen0.CSRIND=0"
            )

        t.either("x7", m_clear, lambda: t.comment("mstateen0.CSRIND is read-only one"))
        m_csrind(t, True)
        h_csrind(t, True)
    return [t]


# ---------------------------------------------------------------- Smcsrind: miselect and mireg*
def t_miselect_warl() -> list[TestFile]:
    t = new("Smcsrind", "miselect_warl", REQ_M, boot="M")
    t.describe(
        rule_text="`miselect` is a WARL register.",
        source=CSRIND,
        context="Any value may be written and a legal value is read. miselect need hold only the implemented "
        "values (miselect_min_sz) and may be read-only zero without extensions that use it, so the legal set is "
        "unknown. Constrained: the value read back is legal, so rewriting it retains it; csrrw returns the current "
        "value; forms with rs1=x0 or uimm=0 do not write. Machine- and supervisor-level select values are separate "
        "address spaces, so miselect and siselect are separate registers.",
        issues=ISS_WARL,
        plan="1. M-mode: write 0, 1, 0x30, 0x3E, 0x3F, 0x70, 0xFF, 0x100, 0xFFF, 0x1000, 0x55.., 0xAA.., the MSB, "
        "all ones but the MSB, all ones and random values. For each, read R; csrrw of R returns R, and R reads back "
        "(retained).\n"
        "2. csrrs/csrrc rs1=x0 and csrrsi/csrrci uimm=0 return the current value and leave it.\n"
        "3. With S: miselect and siselect are separate registers (each write leaves the other's value).",
    )
    vals: list[X] = [
        X(0, 0),
        X(1, 1),
        X(0x30, 0x30),
        X(0x3E, 0x3E),
        X(0x3F, 0x3F),
        X(0x70, 0x70),
        X(0xFF, 0xFF),
        X(0x100, 0x100),
        X(0xFFF, 0xFFF),
        X(0x1000, 0x1000),
        X(0x55555555, 0x5555555555555555),
        X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA),
        MSB,
        X(0x7FFFFFFF, (1 << 63) - 1),
        X(0xFFFFFFFF, (1 << 64) - 1),
        t.rand_x(),
        t.rand_x(),
    ]
    for v in vals:
        t.load("x6", v, "value")
        t.emit(f"csrw {macro('miselect')}, x6")
        t.emit(f"csrr x9, {macro('miselect')}")
        lab = t.label("warl")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrrw x7, {macro('miselect')}, x9")
        eq_check(t, "x7", "x9", lab, "csrrw of miselect returns the value read", "x6")
        t.emit(f"csrr x8, {macro('miselect')}")
        eq_check(t, "x8", "x9", lab, "miselect retains the legal value read back", "x6")
    t.load("x6", t.rand_x(), "value")
    t.emit(f"csrw {macro('miselect')}, x6")
    for form in READ_FORMS:
        t.emit(f"csrr x9, {macro('miselect')}")
        lab = t.label("rform")
        t.emit(f"{lab}:", 0)
        t.emit(form[0].format(c=macro("miselect")))
        eq_check(t, "x7", "x9", lab, f"{form[4]} of miselect returns the current value", "x6")
        t.emit(f"csrr x8, {macro('miselect')}")
        eq_check(t, "x8", "x9", lab, f"{form[4]} of miselect does not write it", "x6")
    with t.only_if("defined(S_SUPPORTED)"):
        t.comment("3. miselect and siselect are separate")
        set_sel(t, "siselect", 0x123)
        t.emit(f"csrr x9, {macro('miselect')}")
        for v in (0x30, 0x3A5, 0xFFF):
            lab = t.label("sep")
            set_sel(t, "miselect", v)
            t.emit(f"csrr x9, {macro('miselect')}")
            set_sel(t, "siselect", 0x123 ^ v)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x8, {macro('miselect')}")
            if MUT == "miselect_is_siselect":
                t.check("x8", 0x123 ^ v, lab, "miselect reads the siselect write")
            else:
                eq_check(t, "x8", "x9", lab, f"miselect is unchanged by a siselect write ({hex(0x123 ^ v)})", "x6")
            set_sel(t, "miselect", v ^ 0x7)
            readback(t, "siselect", 0x123 ^ v, f"{hex(0x123 ^ v)} after a miselect write")
    return [t]


def t_miselect_min_sz() -> list[TestFile]:
    t = new("Smcsrind", "miselect_min_sz", REQ_M, boot="M")
    t.describe(
        rule_text="The `miselect` register implements at least enough bits to support all implemented `miselect` "
        "values (corresponding to the implemented extensions that utilize `miselect`/`mireg*` to indirectly access "
        "register state).",
        source=CSRIND,
        context="miselect may be read-only zero when no extension uses it. The only M-level range on the "
        "configurations is Smaia's 0x30-0x3F (major-interrupt priorities; on RV64 only even registers exist). The AIA "
        'spec sets the implemented values: "When an IMSIC is not implemented, miselect must be able to hold at least '
        'any 6-bit value in the range 0 to 0x3F" (riscv-aia CSRs.adoc), at both XLENs. IMSIC values 0x70-0xFF '
        "exist only with an IMSIC, which no macro reveals, so they are not used. Without Smaia the test checks "
        "nothing.",
        issues=ISSUE_NONE,
        plan="With Smaia: write every value 0x30..0x3F, and 0, 1, 0x15, 0x2A, 0x2F, to miselect and read each back "
        "exactly.",
    )
    with t.only_if(SMAIA):
        for v in [*range(0x30, 0x40), 0x00, 0x01, 0x15, 0x2A, 0x2F]:
            set_sel(t, "miselect", v)
            readback(t, "miselect", v & 0xF if MUT == "miselect_4bit" else v, hex(v))
    return [t]


def t_miselect_msb_op() -> list[TestFile]:
    t = new("Smcsrind", "miselect_msb_op", REQ_M, boot="M")
    t.describe(
        rule_text="Values of `miselect` with the most-significant bit set (bit XLEN - 1 = 1) are designated only "
        "for custom use, presumably for accessing custom registers through the alias CSRs. Values of `miselect` "
        "with the most-significant bit clear are designated only for standard use and are reserved until allocated "
        "to a standard architecture extension. If XLEN is changed, the most-significant bit of `miselect` moves to "
        "the new position, retaining its value from before.",
        source=CSRIND,
        context="An implementation is not required to support any custom value (note), so a custom write may read "
        "back as any legal value (miselect_warl). Constrained: the value read back is legal (rewriting it retains "
        "it), and with Smaia a following write of 0x30 reads back exactly (the MSB does not stick). MXLEN is fixed "
        "on every configuration, so the XLEN-change clause is not tested.",
        issues=ISS_WARL,
        plan="1. M-mode: write MSB-set (custom) and large standard values to miselect: rewriting the value read back "
        "retains it.\n"
        "2. With Smaia, after each, a write of an even value in 0x30..0x3E reads back exactly.",
    )
    for i, (v, note) in enumerate(big_values(t)):
        stable(t, "miselect", v, note, None)
        with t.only_if(SMAIA):
            after = 0x30 + 2 * (i % 8)
            set_sel(t, "miselect", after)
            readback(t, "miselect", after, f"{hex(after)} after the value {note}")
    return [t]


def t_miselect_op() -> list[TestFile]:
    t = new("Smcsrind", "miselect_op", REQ_M, boot="M")
    t.describe(
        rule_text="The value of `miselect` determines which register is accessed upon read or write of each of the "
        "machine indirect alias CSRs (`mireg*`).",
        source=CSRIND,
        context="Shown with an implemented M-level range: Smaia's 0x30-0x3F (iprio0, iprio2, iprio4 at 0x30, 0x32, "
        "0x34, valid at both XLENs). Their fields are WARL (a priority may be read-only), so expectations come from "
        "reading each register; a hart whose fields are all read-only passes trivially. Without Smaia the test "
        "checks nothing.",
        issues=ISSUE_NONE,
        plan="With Smaia:\n"
        "1. Write a different random value through mireg at miselect 0x30, 0x32, 0x34 and read each back.\n"
        "2. Reselect each in turn: mireg returns the value read back at that select (a write at one select value does "
        "not land at another, and selecting does not change the register).\n"
        "3. Repeat with new values in the opposite order.\n"
        "4. Restore zero at each.",
    )
    with t.only_if(SMAIA):
        independence(t, "miselect", "mireg", [0x30, 0x32, 0x34], MUT == "select_ignored_m")
        independence(t, "miselect", "mireg", [0x34, 0x32, 0x30], MUT == "select_ignored_m")
        for s in (0x30, 0x32, 0x34):
            set_sel(t, "miselect", s)
            t.emit(f"csrw {macro('mireg')}, x0")
    return [t]


def t_mireg_legal() -> list[TestFile]:
    rule = "mireg_access_on_legal_miselect"
    text = (
        "Attempts to access `mireg*` while `miselect` holds a number in an allocated and implemented range results "
        "in a specific behavior that, for each combination of `miselect` and `mireg__i__`, is defined by the "
        "extension to which the `miselect` value is allocated."
    )
    t = new("Smcsrind", rule, REQ_M, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=CSRIND,
        context="The behavior belongs to the owning extension (the Smaia suite tests the priority registers). What "
        "holds for every range: mireg obeys the CSR instruction forms. The spec leaves an access while miselect "
        "holds an unimplemented value UNSPECIFIED (untagged sentence before this rule), with illegal-instruction "
        "expected. " + NOTE_ALLOC,
        issues=ISSUE_NONE + " " + NOTE_UNSPEC,
        plan="1. With Smaia, miselect=0x30: mireg reads without a trap; csrrs/csrrc rs1=x0 and csrrsi/csrrci uimm=0 "
        "return the current value and do not write; csrrw returns the old value.\n"
        "2. Contrast: miselect written with values no extension allocates (0, 0x100, 0xFFF): a read and a write of "
        "mireg..mireg6 raise no trap or illegal-instruction. miselect may hold another legal value instead (WARL), "
        "and the outcome set is the same.",
    )
    with t.only_if(SMAIA):
        set_sel(t, "miselect", 0x30)
        access(t, "M", "mireg", FORMS[0], "ok", "miselect=0x30 (Smaia)")
        forms_dynamic(t, "mireg", "miselect=0x30")
        t.emit(f"csrw {macro('mireg')}, x0")
    for v in (0x000, 0x100, 0xFFF):
        set_sel(t, "miselect", v)
        sweep(t, "M", MIREGS, RW_FORMS, ["ok", ILLEGAL], f"miselect={hex(v)} reserved")
    out_ = [t]

    t = new("Smcsrind", rule, REQ_MS)
    t.describe(
        rule_text=text,
        source=CSRIND,
        context="miselect and mireg* are MRW CSRs: from any less-privileged mode they raise illegal-instruction "
        "whatever miselect holds, including from VS and VU-mode, where M-level CSRs are not HS-qualified "
        "(virtual-instruction applies only to accesses HS-mode could make).",
        issues=ISSUE_NONE,
        plan="miselect=0x30 with Smaia (else 0), set through T-SBI:\n"
        "1. S-mode: miselect and mireg with all eight forms, mireg2..mireg6 with a read and a write: "
        "illegal-instruction.\n"
        "2. U-mode: miselect and mireg..mireg6 reads: illegal-instruction.\n"
        "3. With H, VS- and VU-mode: miselect and mireg..mireg6, read and write: illegal-instruction.",
    )
    t.emit("#ifdef SMAIA_SUPPORTED", 0)
    t.li("a1", 0x30)
    t.emit("#else", 0)
    t.li("a1", 0)
    t.emit("#endif", 0)
    t.tsbi_csr("WRITE", "MISELECT", "a1")
    sweep(t, "S", ["miselect", "mireg"], FORMS, ILLEGAL, "S-mode")
    sweep(t, "S", MIREGS[1:], RW_FORMS, ILLEGAL, "S-mode")
    sweep(t, "U", M_SET, [FORMS[0]], ILLEGAL, "U-mode")
    with t.only_if(H):
        vs = VIRTUAL if MUT == "vs_mireg_virtual" else ILLEGAL
        sweep(t, "VS", M_SET, RW_FORMS, vs, "VS-mode")
        sweep(t, "VU", M_SET, RW_FORMS, ILLEGAL, "VU-mode")
    out_.append(t)
    return out_


# ---------------------------------------------------------------- Smcsrind: mstateen0.CSRIND
def probe_m_csrind(t: TestFile) -> None:
    """Set, then clear mstateen0.CSRIND (T-SBI); x1 = 1 when it read 1 and then 0 (writable both ways). The bit is
    left clear; x1 is kept for later branches."""
    m_csrind(t, True)
    m_read_csrind(t, "x1")
    m_csrind(t, False)
    m_read_csrind(t, "x6")
    t.emit("xori x6, x6, 1")
    t.emit("and x1, x1, x6")


def branches(t: TestFile, sections: list[tuple[str | None, Callable[[], None]]], ro1: str) -> None:
    """Run each section only when x1 is set (the probed bit cleared). A section with a condition is emitted under
    only_if(cond); a run-time branch cannot hold entries under a preprocessor condition of its own."""
    for cond, fn in sections:
        if cond:
            with t.only_if(cond):
                t.either("x1", fn, lambda: t.comment(ro1))
        else:
            t.either("x1", fn, lambda: t.comment(ro1))


def m_probe_direct(t: TestFile) -> None:
    """M-mode: set, then clear mstateen0.CSRIND; x1 = 1 when it read 1 and then 0. The bit is left clear."""

    def read(reg: str) -> None:
        with t.rv64_only():
            t.emit(f"csrr {reg}, {macro('mstateen0')}")
            t.emit(f"srli {reg}, {reg}, 60")
        with t.rv32_only():
            t.emit(f"csrr {reg}, {macro('mstateen0h')}")
            t.emit(f"srli {reg}, {reg}, 28")
        t.emit(f"andi {reg}, {reg}, 1")

    m_csrind_direct(t, True)
    read("x1")
    m_csrind_direct(t, False)
    read("x6")
    t.emit("xori x6, x6, 1")
    t.emit("and x1, x1, x6")


def t_csrs_access_control() -> list[TestFile]:
    rule = "Sscsrind_csrs_access_control"
    text = (
        "If extension Smstateen is implemented together with Smcsrind, bit 60 of state-enable register `mstateen0` "
        "controls access to `siselect`, `sireg*`, `vsiselect`, and `vsireg*`. When `mstateen0`[60]=0, an attempt to "
        "access one of these CSRs from a privilege mode less privileged than M-mode results in an "
        "illegal-instruction exception."
    )
    ctx = (
        "Bit 60 is mstateen0h bit 28 on RV32. The bit takes precedence over the virtual-instruction rules of the "
        "hypervisor section, so VS and VU-mode accesses also raise illegal-instruction. mstateen bits may be "
        "read-only zero or one, so the test probes that the bit can be set and cleared and checks the gated cases only "
        "then. The state-enable "
        "CSRs never affect M-mode."
    )
    t = new("Smcsrind", rule, REQ_MST)
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx + " While mstateen0.CSRIND=0, hstateen0.CSRIND is read-only zero; after the bit is restored "
        "hstateen0.CSRIND holds an UNSPECIFIED value, so the test sets it again.",
        issues=ISS_STATEEN,
        plan="With mstateen0.CSRIND cleared through T-SBI:\n"
        "1. S-mode: siselect and sireg with all eight forms, sireg2..sireg6 with a read and a write; with H the same "
        "for vsiselect/vsireg*: illegal-instruction (siselect and vsiselect hold 0x30).\n"
        "2. U-mode: siselect, sireg*, vsiselect, vsireg* reads: illegal-instruction.\n"
        "3. With H, VS-mode: siselect and sireg with all eight forms, the rest with a read and a write: "
        "illegal-instruction, not virtual (also for vsiselect/vsireg*, which are virtual-instruction when the bit is "
        "set).\n"
        "4. With H, VU-mode: all of them, read and write: illegal-instruction.\n"
        "5. Restore the bit (and hstateen0.CSRIND): S-mode siselect reads and writes without a trap, VS-mode siselect "
        "too.",
    )
    set_sel(t, "siselect", 0x030)
    with t.only_if(H):
        set_sel(t, "vsiselect", 0x030)
    probe_m_csrind(t)

    s = "ok" if MUT == "mstateen_ignored_s" else ILLEGAL
    low = VIRTUAL if MUT == "mstateen_virtual" else ILLEGAL
    RO1 = "mstateen0.CSRIND is read-only: nothing gated to check"

    def s_mode() -> None:
        t.comment("1. S-mode")
        sweep(t, "S", ["siselect", "sireg"], FORMS, s, "mstateen0.CSRIND=0")
        sweep(t, "S", SIREGS[1:], RW_FORMS, ILLEGAL, "mstateen0.CSRIND=0")
        t.comment("2. U-mode")
        sweep(t, "U", S_SET, [FORMS[0]], ILLEGAL, "U-mode, mstateen0.CSRIND=0")

    def h_modes() -> None:
        sweep(t, "S", ["vsiselect", "vsireg"], FORMS, ILLEGAL, "HS-mode, mstateen0.CSRIND=0")
        sweep(t, "S", VSIREGS[1:], RW_FORMS, ILLEGAL, "HS-mode, mstateen0.CSRIND=0")
        sweep(t, "U", VS_SET, [FORMS[0]], ILLEGAL, "U-mode, mstateen0.CSRIND=0")
        t.comment("3. VS-mode")
        sweep(t, "VS", ["siselect", "sireg"], FORMS, low, "VS-mode, mstateen0.CSRIND=0")
        sweep(t, "VS", SIREGS[1:] + VS_SET, RW_FORMS, low, "VS-mode, mstateen0.CSRIND=0")
        t.comment("4. VU-mode")
        sweep(t, "VU", S_SET + VS_SET, RW_FORMS, low, "VU-mode, mstateen0.CSRIND=0")

    def restore() -> None:
        t.comment("5. restore")
        m_csrind(t, True)
        sweep(t, "S", ["siselect"], RW_FORMS, "ok", "mstateen0.CSRIND=1 again")

    def restore_h() -> None:
        h_csrind(t, True)
        sweep(t, "VS", ["siselect"], RW_FORMS, "ok", "mstateen0.CSRIND=1 again")

    branches(t, [(None, s_mode), (H, h_modes), (None, restore), (H, restore_h)], RO1)
    m_csrind(t, True)
    with t.only_if(H):
        h_csrind(t, True)
    out_ = [t]

    t = new("Smcsrind", rule, REQ_MST, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=CSRIND,
        context=ctx,
        issues=ISS_STATEEN,
        plan="M-mode, mstateen0.CSRIND cleared (when it can be):\n"
        "1. siselect (and vsiselect with H) with all eight forms: no trap; a written value reads back.\n"
        "2. S-mode siselect read: illegal-instruction; U-mode: illegal-instruction.\n"
        "3. Restore the bit.",
    )
    m_probe_direct(t)
    m = ILLEGAL if MUT == "mstateen_gates_m" else "ok"

    def m_gated() -> None:
        sweep(t, "M", ["siselect"], FORMS, m, "M-mode, mstateen0.CSRIND=0")
        if m == "ok":
            set_sel(t, "siselect", 0x6D2)
            readback(t, "siselect", 0x6D2, "0x6D2 written in M-mode with mstateen0.CSRIND=0")
        access(t, "S", "siselect", FORMS[0], ILLEGAL, "S-mode, mstateen0.CSRIND=0")
        access(t, "U", "siselect", FORMS[0], ILLEGAL, "U-mode, mstateen0.CSRIND=0")

    def m_gated_h() -> None:
        sweep(t, "M", ["vsiselect"], FORMS, m, "M-mode, mstateen0.CSRIND=0")

    branches(t, [(None, m_gated), (H, m_gated_h)], "mstateen0.CSRIND is read-only")
    m_csrind_direct(t, True)
    out_.append(t)
    return out_


def t_mstateen0_csrind_op() -> list[TestFile]:
    rule = "mstateen0_csrind_op"
    text = (
        "The CSRIND bit in `mstateen0` controls access to the `siselect`, `sireg*`, `vsiselect`, and the `vsireg*` "
        "CSRs provided by the Sscsrind extensions."
    )
    t = new("Smcsrind", rule, REQ_MST)
    t.describe(
        rule_text=text,
        source=STATEEN,
        context="CSRIND is mstateen0 bit 60 (mstateen0h bit 28 on RV32); clear, accesses from below M-mode raise "
        "illegal-instruction (Sscsrind_csrs_access_control). The bit may be read-only, so it is probed (set, then clear). It "
        "controls only these CSRs: miselect/mireg* are M-level (unaffected), and S-level CSRs controlled by no "
        "stateen bit (sscratch) stay accessible.",
        issues=ISS_STATEEN,
        plan="1. M-mode (T-SBI): clear, set, clear, set mstateen0.CSRIND and read it back; the other bits of "
        "mstateen0 (mstateen0h on RV32) are unchanged.\n"
        "2. Transitions in S-mode: siselect read succeeds with the bit set, raises illegal-instruction with it clear, "
        "and succeeds again when set; with H the same for vsiselect.\n"
        "3. With the bit clear, S-mode sscratch reads without a trap.",
    )
    probe_m_csrind(t)

    RO1 = "mstateen0.CSRIND is read-only"

    def toggle(on: bool) -> None:
        with t.rv64_only():
            t.tsbi_csr("READ", "MSTATEEN0")
        with t.rv32_only():
            t.tsbi_csr("READ", "MSTATEEN0H")
        t.emit("mv x9, a0")
        m_csrind(t, on)
        lab = t.label("mbit")
        t.emit(f"{lab}:", 0)
        with t.rv64_only():
            t.tsbi_csr("READ", "MSTATEEN0")
            t.emit("mv x8, a0")
            t.emit(f"srli x7, a0, {59 if MUT == 'mstateen_bit_59' else 60}")
            t.li("x6", 1)
            t.emit("slli x6, x6, 60")
        with t.rv32_only():
            t.tsbi_csr("READ", "MSTATEEN0H")
            t.emit("mv x8, a0")
            t.emit(f"srli x7, a0, {27 if MUT == 'mstateen_bit_59' else 28}")
            t.li("x6", 1 << 28)
        t.emit("andi x7, x7, 1")
        t.check("x7", int(on), lab, f"mstateen0.CSRIND reads {int(on)} after M-mode {'set' if on else 'clear'}")
        t.emit("xor x8, x8, x9")
        t.emit("not x6, x6")
        t.emit("and x8, x8, x6")
        t.check("x8", 0, lab, "other mstateen0 bits are unchanged")
        s = "ok" if on or MUT == "mstateen_ignored_s" else ILLEGAL
        access(t, "S", "siselect", FORMS[0], s, f"mstateen0.CSRIND={int(on)}")
        if not on:
            access(t, "S", "sscratch", FORMS[0], "ok", "mstateen0.CSRIND=0 (sscratch is not controlled)")

    def h_access(on: bool) -> None:
        access(t, "S", "vsiselect", FORMS[0], "ok" if on else ILLEGAL, f"HS-mode, mstateen0.CSRIND={int(on)}")

    for on in (False, True, False, True):
        branches(t, [(None, lambda on=on: toggle(on)), (H, lambda on=on: h_access(on))], RO1)
    m_csrind(t, True)
    with t.only_if(H):
        h_csrind(t, True)
    out_ = [t]

    t = new("Smcsrind", rule, REQ_MST, boot="M", suffix="_Sm")
    t.describe(
        rule_text=text,
        source=STATEEN,
        context="The state-enable CSRs never restrict M-mode, and CSRIND controls only the S-level and VS-level "
        "indirect CSRs.",
        issues=ISS_STATEEN,
        plan="M-mode, mstateen0.CSRIND cleared (when it can be set and cleared):\n"
        "1. miselect and siselect read and write without a trap, and a siselect write reads back.\n"
        "2. With Smaia, mireg at miselect=0x30; with Ssaia, sireg at siselect=0x30: read and write without a trap.\n"
        "3. With H, vsiselect reads and writes without a trap and a write reads back.\n"
        "4. The bit is restored.",
    )
    m_probe_direct(t)
    m = ILLEGAL if MUT == "mstateen_gates_m" else "ok"

    def m_gated() -> None:
        sweep(t, "M", ["miselect"], RW_FORMS, "ok", "M-mode, mstateen0.CSRIND=0")
        sweep(t, "M", ["siselect"], RW_FORMS, m, "M-mode, mstateen0.CSRIND=0")
        if m == "ok":
            set_sel(t, "siselect", 0x5B4)
            readback(t, "siselect", 0x5B4, "0x5B4 written in M-mode with mstateen0.CSRIND=0")

    def s_aia() -> None:
        set_sel(t, "siselect", 0x30)
        sweep(t, "M", ["sireg"], RW_FORMS, m, "M-mode, mstateen0.CSRIND=0, siselect=0x30")
        t.emit(f"csrw {macro('sireg')}, x0")

    def m_h() -> None:
        sweep(t, "M", ["vsiselect"], RW_FORMS, m, "M-mode, mstateen0.CSRIND=0")
        if m == "ok":
            set_sel(t, "vsiselect", 0x4C3)
            readback(t, "vsiselect", 0x4C3, "0x4C3 written in M-mode with mstateen0.CSRIND=0")

    def m_aia() -> None:
        set_sel(t, "miselect", 0x30)
        sweep(t, "M", ["mireg"], RW_FORMS, "ok", "M-mode, mstateen0.CSRIND=0, miselect=0x30")
        t.emit(f"csrw {macro('mireg')}, x0")

    branches(t, [(None, m_gated), (SMAIA, m_aia), (SSAIA, s_aia), (H, m_h)], "mstateen0.CSRIND is read-only")
    m_csrind_direct(t, True)
    out_.append(t)
    return out_


def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    for f in (
        t_siselect_min_range,
        t_siselect_msb_op,
        t_sireg_illegal,
        t_sireg_legal,
        t_vsiselect_min_range,
        t_vsiselect_msb_op,
        t_virtual_inst_fault,
        t_vsireg_legal,
        t_hyp_access_control,
        t_hstateen0_csrind_op,
        t_miselect_warl,
        t_miselect_min_sz,
        t_miselect_msb_op,
        t_miselect_op,
        t_mireg_legal,
        t_csrs_access_control,
        t_mstateen0_csrind_op,
    ):
        tests += f()
    return tests


if __name__ == "__main__":
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(Path(__file__).resolve().parents[2])}: ~{t.ninst} instructions")
