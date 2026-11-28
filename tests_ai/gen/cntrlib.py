# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the counter suites: Smcdeleg/Ssccfg (gen_Smcdeleg.py), Smcntrpmf (gen_Smcntrpmf.py) and
Sscounterenw/Shcounterenw (gen_Sscounterenw.py).

S-mode tests (boot="S") reach M-level CSRs (menvcfg, mcounteren, mcountinhibit, mhpmevent/mhpmcounter with
Sscofpmf) through T-SBI; M-mode tests (boot="M") access them directly. m_op() picks the path from t.boot.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, Value

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
H = "defined(H_SUPPORTED)"

# CSR numbers
SISELECT, VSISELECT, MISELECT = 0x150, 0x250, 0x350
SIREG = {1: 0x151, 2: 0x152, 3: 0x153, 4: 0x155, 5: 0x156, 6: 0x157}
VSIREG = {k: v + 0x100 for k, v in SIREG.items()}
SCOUNTINHIBIT, SCOUNTOVF = 0x120, 0xDA0
MCYCLECFG, MINSTRETCFG, MCYCLECFGH, MINSTRETCFGH = 0x321, 0x322, 0x721, 0x722
SIREG_NAME = {1: "sireg", 2: "sireg2", 3: "sireg3", 4: "sireg4", 5: "sireg5", 6: "sireg6"}

ALL32 = 0xFFFFFFFF
HPM_MASK = 0xFFFFFFF8  # HPM3..HPM31
CTR_MASK = 0xFFFFFFFD  # CY, IR, HPM3..31 (bit 1, TM, has no counter-inhibit bit)
LCOF = 1 << 13

# xINH bits of mcyclecfg/minstretcfg/mhpmevent, as bits of the high word (bit 63 = bit 31 of the high word)
INH_HI = {"M": 1 << 30, "S": 1 << 29, "U": 1 << 28, "VS": 1 << 27, "VU": 1 << 26}
MODES = ("M", "S", "U", "VS", "VU")
MODE_COND = {"M": None, "S": "defined(S_SUPPORTED)", "U": "defined(U_SUPPORTED)", "VS": H, "VU": H}

# CSR instruction forms: (asm template, funct3, rd, rs1-or-uimm, kind). rd x7, rs x6, uimm 0x15.
Form = tuple[str, int, int, int, str]
FORMS: list[Form] = [
    ("csrrs x7, {c}, x0", 2, 7, 0, "read (csrrs rs1=x0)"),
    ("csrrw x0, {c}, x6", 1, 0, 6, "write (csrrw rd=x0)"),
    ("csrrw x7, {c}, x6", 1, 7, 6, "swap (csrrw)"),
    ("csrrs x7, {c}, x6", 2, 7, 6, "set (csrrs)"),
    ("csrrc x7, {c}, x6", 3, 7, 6, "clear (csrrc)"),
    ("csrrwi x7, {c}, 0x15", 5, 7, 0x15, "write immediate (csrrwi)"),
    ("csrrsi x7, {c}, 0", 6, 7, 0, "read (csrrsi uimm=0)"),
    ("csrrci x7, {c}, 0x15", 7, 7, 0x15, "clear immediate (csrrci)"),
]
READ = FORMS[0]
WRITE = FORMS[1]


def icause(c: int) -> X:
    return X((1 << 31) | c, (1 << 63) | c)


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


def hx(v: int) -> X:
    """A high-word value as the register value of the high CSR (RV32) or the full CSR (RV64)."""
    return X(v, v << 32)


def inh(*modes: str) -> int:
    v = 0
    for m in modes:
        v |= INH_HI[m]
    return v


# ---------------------------------------------------------------- M-level CSR access
def m_op(t: TestFile, op: str, csr: str, src: str | None = None, imm: int | str | None = None) -> None:
    """op (READ/WRITE/SET/CLEAR) on an M-level CSR named by its CSR_* macro: T-SBI in S-boot tests (result in a0),
    direct in M-boot tests (read result in a0; uses a1)."""
    if op != "READ":
        if src is not None:
            if src != "a1":
                t.emit(f"mv a1, {src}")
        else:
            t.emit(f"LI(a1, {imm})", 2)
    if t.boot == "M":
        insn = {"READ": "csrr a0, {c}", "WRITE": "csrw {c}, a1", "SET": "csrs {c}, a1", "CLEAR": "csrc {c}, a1"}[op]
        t.emit(insn.format(c=csr))
    else:
        t.emit(f"RVTEST_TSBI_CSR_ACCESS TSBI_CSR_{op}({csr})", 120)


def cde(t: TestFile, on: bool) -> None:
    """menvcfg.CDE (bit 60; menvcfgh bit 28 on RV32)."""
    t.comment(f"menvcfg.CDE = {int(on)}")
    op = "SET" if on else "CLEAR"
    with t.rv64_only():
        t.emit("LI(a1, 1)", 2)
        t.emit("slli a1, a1, 60")
        m_op(t, op, "CSR_MENVCFG", "a1")
    with t.rv32_only():
        m_op(t, op, "CSR_MENVCFGH", imm=0x10000000)


def cde_read(t: TestFile, dst: str) -> None:
    """dst = menvcfg.CDE (0/1)."""
    with t.rv64_only():
        m_op(t, "READ", "CSR_MENVCFG")
        t.emit(f"srli {dst}, a0, 60")
    with t.rv32_only():
        m_op(t, "READ", "CSR_MENVCFGH")
        t.emit(f"srli {dst}, a0, 28")
    t.emit(f"andi {dst}, {dst}, 1")


# ---------------------------------------------------------------- scratch slots
def scratch(t: TestFile, n: int = 24) -> None:
    if not any(ln.startswith("cntr_scr:") for ln in t.extra_data):
        t.extra_data += [".p2align 3", "cntr_scr:", f"  .fill {n}, 8, 0"]


def st(t: TestFile, reg: str, slot: int) -> None:
    """Store reg in a scratch slot (clobbers x4)."""
    scratch(t)
    t.emit("LA(x4, cntr_scr)", 2)
    t.emit(f"SREG {reg}, {slot}*REGWIDTH(x4)")


def ld(t: TestFile, reg: str, slot: int) -> None:
    scratch(t)
    t.emit("LA(x4, cntr_scr)", 2)
    t.emit(f"LREG {reg}, {slot}*REGWIDTH(x4)")


def m_save(t: TestFile, csr: str, slot: int) -> None:
    m_op(t, "READ", csr)
    st(t, "a0", slot)


def m_restore(t: TestFile, csr: str, slot: int) -> None:
    ld(t, "a1", slot)
    m_op(t, "WRITE", csr, "a1")


def men_write(t: TestFile, value: int | str, slot: int | None = None) -> None:
    """mcounteren = value (M-level write); keep the value read back (WARL) in slot."""
    t.comment(f"mcounteren = {value if isinstance(value, str) else hex(value)}")
    m_op(t, "WRITE", "CSR_MCOUNTEREN", imm=value)
    if slot is not None:
        m_op(t, "READ", "CSR_MCOUNTEREN")
        st(t, "a0", slot)


# ---------------------------------------------------------------- trap windows
def cause_of(expect: str | int) -> str | int:
    return {"ok": "ok", "illegal": 2, "virtual": 22}.get(expect, expect)  # type: ignore[arg-type]


def csr_win(t: TestFile, mode: str, csr: int, name: str, form: Form, expect: str | int, desc: str) -> str:
    """One CSR instruction (by number) in `mode` inside a trap window. expect: ok, illegal, virtual (or a cause).
    Faulting instructions accept xtval = 0 or the instruction bits."""
    asm, f3, rd, rs1, kind = form
    cause = cause_of(expect)
    tval: list[Value] | None = None if cause == "ok" else [0, enc_csr(csr, f3, rd, rs1)]
    return win(t, mode, [asm.format(c=hex(csr)) + f"  // {name}"], cause, f"{kind} of {name} ({desc})", tval)


def mpv(t: TestFile, on: bool) -> None:
    """M-mode: mstatus.MPV (mstatush.MPV on RV32). Uses x14."""
    with t.rv64_only():
        t.li("x14", 1)
        t.emit("slli x14, x14, 39")
        t.emit(f"{'csrs' if on else 'csrc'} mstatus, x14  // MPV")
    with t.rv32_only():
        t.li("x14", 1 << 7)
        t.emit(f"{'csrs' if on else 'csrc'} 0x310, x14  // mstatush.MPV")


def enter(t: TestFile, mode: str) -> None:
    """Enter `mode` from t.cur: TestFile.enter, plus VS/VU from M (mret with MPV=1). Uses x14."""
    if t.cur == "M" and mode in ("VS", "VU"):
        after = t.label(f"in{mode}")
        t.la("x14", after)
        t.emit("csrw mepc, x14")
        t.emit("LI(x14, MSTATUS_MPP)", 2)
        t.emit("csrc mstatus, x14")
        if mode == "VS":
            t.emit("LI(x14, MPP_SMODE)", 2)
            t.emit("csrs mstatus, x14")
        mpv(t, True)
        t.emit("mret")
        t.emit(f"{after}:", 0)
    else:
        t.enter(mode)


def win(
    t: TestFile,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    tval: Expect | None = None,
    origin: str | None = None,
) -> str:
    """TestFile.window, entering VS/VU from M-mode too."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    if mode != t.cur:
        enter(t, mode)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if mode != t.cur:
        t.leave()
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=origin or mode)
    return lab


def run_in(t: TestFile, mode: str, lines: list[str], n: int = 1) -> None:
    """Run lines in `mode` (no trap window): enter, run, leave. n: dynamic count of lines."""
    if mode != t.cur:
        enter(t, mode)
    for ln in lines:
        t.emit(ln, n)
    if mode != t.cur:
        t.leave()


def guard(t: TestFile, cond: str | None, body: Callable[[], object]) -> None:
    if cond:
        with t.only_if(cond):
            body()
    else:
        body()


def pred_near(t: TestFile, dst: str, val: str, ref: str, bound: int) -> None:
    """dst = 1 if 0 <= val - ref < bound (unsigned), else 0. bound < 2048."""
    t.emit(f"sub {dst}, {val}, {ref}")
    t.emit(f"sltiu {dst}, {dst}, {bound}")


def _skip(t: TestFile, lo: int, hi: int) -> list[str]:
    """AI_SKIP over table entries lo..hi-1 whatever their preprocessor conditions: one AI_SKIP per distinct set of
    conditions beyond those in force, each under its own #if (XLEN conditions included)."""
    groups: dict[tuple[str, ...], int] = {}
    for _, conds in t.table[lo:hi]:
        extra = tuple(c for c in conds if c not in t._conds)
        groups[extra] = groups.get(extra, 0) + 1
    out = []
    for conds, n in groups.items():
        if conds:
            out.append("#if " + " && ".join(f"({c})" for c in conds))
        out.append(f"  AI_SKIP({n})" if n * 8 < 2048 else f"  AI_SKIP_BIG({n})")
        if conds:
            out.append("#endif")
    return out


def either(t: TestFile, reg: str, if_set: Callable[[], object], skipped: str) -> None:
    """Run-time branch on reg (nonzero: if_set; zero: a comment `skipped`). Unlike TestFile.either, if_set may hold
    table entries under further #if conditions."""
    clear, done = t.label("clear"), t.label("done")
    t.emit(f"beqz {reg}, {clear}")
    a = len(t.table)
    if_set()
    b = len(t.table)
    t.emit(f"j {done}")
    t.emit(f"{clear}:", 0)
    t.comment(f"skipped: {skipped}")
    t.code += _skip(t, a, b)
    t.emit(f"{done}:", 0)
