#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Sscounterenw and tests_ai/Shcounterenw: writable scounteren/hcounteren bits for every
hpmcounter that is not read-only zero.

The S-mode files (boot="S") find the counters that are not read-only zero by writing each mhpmcounter through
T-SBI (it has the mhpmcounters only with Sscofpmf) and, without Sscofpmf, by reading hpmcounters that hold a
nonzero value. The _Sm files (boot="M", Sm required) write every mhpmcounter directly, so they decide for every
counter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile
from cntrlib import HPM_MASK, ld, m_op, st

SUITE = "Sscounterenw"
MUT = os.environ.get("AI_MUTANT", "")
MARCH = "rv${XLEN}i_zicsr_zifencei"

MUTANTS = {
    "hpm31_ro0": "bit 31 of the counter-enable register is read-only zero even though hpmcounter31 is not",
    "en_ro0": "every HPM bit of the counter-enable register is read-only zero",
    "en_aliases_mcounteren": "a counter-enable write also writes mcounteren",
    "en_set_only": "csrc does not clear counter-enable bits",
}

PATTERNS = [HPM_MASK, 0, 0x55555555 & HPM_MASK, 0xAAAAAAAA & HPM_MASK]
NZ_SLOT, MEN_SLOT, SAVE_SLOT = 0, 1, 2


def out(name: str) -> str:
    return name if SUITE == "Sscounterenw" else SUITE


def gen() -> list[TestFile]:
    tests = []
    for which in ("s", "h"):
        tests += [t_counterenw(which, m) for m in (False, True)]
    return tests


def probe_nz(t: TestFile, sm: bool) -> None:
    """Slot NZ_SLOT = mask of HPM counters that are not read-only zero: each mhpmcounter is written with a nonzero
    value and read back (M-mode, or T-SBI with Sscofpmf). Without Sscofpmf in an S-mode test, an hpmcounter that
    reads nonzero (with its mcounteren bit set; bits that stay 0 are skipped) is not read-only zero; the others are
    left out."""
    t.comment("NZ = HPM counters that are not read-only zero")
    t.emit("li x1, 0")

    def by_write() -> None:
        for n in range(3, 32):
            csr = f"0x{0xB00 + n:x}"
            m_op(t, "WRITE", csr, imm=0x5A5)
            m_op(t, "READ", csr)
            t.emit("snez a0, a0")
            t.emit(f"slli a0, a0, {n}")
            t.emit("or x1, x1, a0")
            m_op(t, "WRITE", csr, imm=0)

    if sm:
        by_write()
    else:
        with t.only_if("defined(SSCOFPMF_SUPPORTED)"):
            by_write()
        with t.only_if("!defined(SSCOFPMF_SUPPORTED) && defined(ZIHPM_SUPPORTED)"):
            m_op(t, "WRITE", "CSR_MCOUNTEREN", imm=ALL_ONES)
            m_op(t, "READ", "CSR_MCOUNTEREN")
            t.emit("mv x7, a0")
            for n in range(3, 32):
                skip = t.label("noread")
                t.emit(f"srli x6, x7, {n}")
                t.emit("andi x6, x6, 1")
                t.emit(f"beqz x6, {skip}  // mcounteren bit {n} read-only zero: hpmcounter{n} not readable")
                t.emit(f"csrr x6, 0x{0xC00 + n:x}  // hpmcounter{n}")
                t.emit("snez x6, x6")
                t.emit(f"slli x6, x6, {n}")
                t.emit("or x1, x1, x6")
                t.emit(f"{skip}:", 0)
    st(t, "x1", NZ_SLOT)


ALL_ONES = -1


def t_counterenw(which: str, sm: bool) -> TestFile:
    reg = {"s": "scounteren", "h": "hcounteren"}[which]
    csr = {"s": "CSR_SCOUNTEREN", "h": "CSR_HCOUNTEREN"}[which]
    ext = {"s": "Sscounterenw", "h": "Shcounterenw"}[which]
    rule = {"s": "Sscounterenw_hpmcounter_scounteren", "h": "Shcounterenw_hpmcounter_hcounteren"}[which]
    req = ["I", "S", ext] + (["H"] if which == "h" else []) + (["Sm"] if sm else [])
    t = TestFile(
        out(ext), rule, required=req, march=MARCH, boot="M" if sm else "S", pool=POOL_TRAP, suffix="_Sm" if sm else ""
    )
    t.describe(
        source=f"src/priv/{ext.lower()}.adoc",
        rule_text=f"If the {ext} extension is implemented, then for any `hpmcounter` that is not read-only zero, the "
        f"corresponding bit in `{reg}` must be writable.",
        context=f"A counter that is not read-only zero is found by writing a nonzero value to its mhpmcounter and "
        f"reading it back (with event 0 the counter does not count, and a writable counter returns the value). A "
        f"writable bit of {reg} reads back what was last written to it, whatever the other bits hold, so every "
        f"pattern must read back exactly on those bits. Bits of read-only-zero counters, and CY/TM/IR, are not "
        f"constrained by this rule and are masked off."
        + (
            " This file runs in M-mode and writes every mhpmcounter directly."
            if sm
            else " This S-mode file writes the mhpmcounters through T-SBI, which offers them only with Sscofpmf; "
            "without Sscofpmf it counts as not read-only zero only an hpmcounter that reads nonzero (the _Sm file "
            "decides for every counter)."
        ),
        plan=f"1. NZ = mask of HPM counters 3-31 that are not read-only zero.\n"
        f"2. For {reg} patterns all ones, 0, 0x55555550, 0xAAAAAAA8 and a random one (HPM bits): write it with csrw "
        f"and check (read XOR pattern) AND NZ = 0.\n"
        f"3. csrs/csrc of each NZ bit alone from all zeros / all ones: the bit is set / cleared (AND NZ).\n"
        f"4. mcounteren is unchanged by the {reg} writes (similar registers must not cross)"
        + (", and so is scounteren." if which == "h" else ".")
        + f"\n{reg} and mcounteren are restored.",
    )
    t.li("x6", 2)
    t.emit("csrc sstatus, x6" if not sm else "csrc mstatus, x6")
    m_op(t, "READ", "CSR_MCOUNTEREN")
    st(t, "a0", MEN_SLOT)
    t.emit(f"csrr x6, {csr}")
    st(t, "x6", SAVE_SLOT)
    if which == "h":
        t.emit("csrr x6, CSR_SCOUNTEREN")
        st(t, "x6", 3)
    probe_nz(t, sm)
    m_restore_men(t)

    def expect_bits(desc: str, lab: str, pattern_reg: str) -> None:
        """Check ((csr read) XOR pattern) AND NZ == 0. x7 = read value."""
        ld(t, "x8", NZ_SLOT)
        if MUT == "hpm31_ro0":
            t.emit("LI(x9, 0x7FFFFFFF)", 2)
            t.emit(f"and {pattern_reg}, {pattern_reg}, x9")
        if MUT == "en_ro0":
            t.emit(f"li {pattern_reg}, 0")
        t.emit(f"xor x9, x7, {pattern_reg}")
        t.emit("and x9, x9, x8")
        t.check("x9", 0, lab, f"{reg} bits of counters that are not read-only zero after {desc}")

    pats = PATTERNS + [t.rand(32) & HPM_MASK]
    for p in pats:
        lab = t.label("pat")
        t.emit(f"LI(x6, {p:#x})", 2)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {csr}, x6")
        t.emit(f"csrr x7, {csr}")
        expect_bits(f"csrw {p:#010x}", lab, "x6")
    for n in (3, 4, 17, 30, 31):
        b = 1 << n
        lab = t.label("set")
        t.emit(f"csrw {csr}, x0")
        t.emit(f"LI(x6, {b:#x})", 2)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrs {csr}, x6")
        t.emit(f"csrr x7, {csr}")
        expect_bits(f"csrs of bit {n} from 0", lab, "x6")
        lab = t.label("clr")
        t.emit(f"LI(x6, {HPM_MASK:#x})", 2)
        t.emit(f"csrw {csr}, x6")
        t.emit(f"LI(x6, {b:#x})", 2)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrc {csr}, x6")
        t.emit(f"csrr x7, {csr}")
        t.emit(f"LI(x6, {HPM_MASK & ~b:#x})", 2)
        if MUT == "en_set_only":
            t.emit(f"LI(x6, {HPM_MASK:#x})", 2)
        expect_bits(f"csrc of bit {n} from all ones", lab, "x6")
    lab = t.label("men")
    t.emit(f"{lab}:", 0)
    t.emit(f"LI(x6, {0x55555555 & HPM_MASK:#x})", 2)
    t.emit(f"csrw {csr}, x6")
    m_op(t, "READ", "CSR_MCOUNTEREN")
    ld(t, "x7", MEN_SLOT)
    if MUT == "en_aliases_mcounteren":
        t.emit(f"LI(x8, {HPM_MASK:#x})", 2)
        t.emit("and x8, x8, x7")
        t.emit("xor x7, x7, x8")
        t.emit("or x7, x7, x6")
    t.emit("xor a0, a0, x7")
    t.check("a0", 0, lab, f"mcounteren XOR its value before the {reg} writes")
    if which == "h":
        lab = t.label("sen")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_SCOUNTEREN")
        ld(t, "x8", 3)
        t.emit("xor x7, x7, x8")
        t.check("x7", 0, lab, "scounteren XOR its value before the hcounteren writes")
    ld(t, "x6", SAVE_SLOT)
    t.emit(f"csrw {csr}, x6")
    return t


def m_restore_men(t: TestFile) -> None:
    ld(t, "a1", MEN_SLOT)
    m_op(t, "WRITE", "CSR_MCOUNTEREN", "a1")


if __name__ == "__main__":
    for t in gen():
        print(t.write())
