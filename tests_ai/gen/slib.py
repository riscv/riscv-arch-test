# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the supervisor-mode (S) rule-derived tests (gen_S.py).

Tests boot to S-mode (HS-mode with H). U-mode is entered with sret (TestFile.enter) and left with a T-SBI GOTO.
M-level CSRs (mstatus, mie, mip, mcounteren, menvcfg) are reached through T-SBI. Traps and interrupts are checked
in the framework trap log. Supervisor-level interrupts are raised as follows:
  SSI: S-mode writes sip.SSIP (writable in sip, sip_ssip_sie_ssie);
  STI: M-mode writes mip.STIP through the framework (rvtest_set_stime_int_su; menvcfg.STCE is 0 at boot);
  SEI: the framework's platform hook or M-mode mip.SEIP (rvtest_set_sext_int_su).
The STI and SEI hooks are called with jal, so tests that raise them keep x1 out of their register pool.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
SUP = "src/priv/supervisor.adoc"
MAC = "src/priv/machine.adoc"

# sstatus fields
SIE, SPIE, UBE, SPP = 1 << 1, 1 << 5, 1 << 6, 1 << 8
VS, FS, XS = 3 << 9, 3 << 13, 3 << 15
SUM, MXR, SPELP, SDT = 1 << 18, 1 << 19, 1 << 23, 1 << 24
UXL = 3 << 32
SD = X(1 << 31, 1 << 63)
# mstatus-only fields (bit positions that are WPRI in sstatus)
MIE, MPIE, MPP, MPRV, TVM, TW, TSR = 1 << 3, 1 << 7, 3 << 11, 1 << 17, 1 << 20, 1 << 21, 1 << 22
# WPRI bits of sstatus, per the sstatusreg figures
WPRI32 = (1 << 0) | (7 << 2) | (1 << 7) | (3 << 11) | (1 << 17) | (7 << 20) | (0x3F << 25)
WPRI64 = (1 << 0) | (7 << 2) | (1 << 7) | (3 << 11) | (1 << 17) | (7 << 20) | (0x7F << 25) | (((1 << 29) - 1) << 34)
WPRI = X(WPRI32, WPRI64)

# senvcfg fields
FIOM, LPE, SSE, CBIE, CBCFE, CBZE = 1 << 0, 1 << 2, 1 << 3, 3 << 4, 1 << 6, 1 << 7
ENV_WPRI = X((1 << 1) | (0xFFFFFF << 8), (1 << 1) | (0xFFFFFF << 8) | (((1 << 30) - 1) << 34))

ILLEGAL, BREAKPOINT, ECALL_U, ECALL_S = 2, 3, 8, 9
SRET, WFI, EBREAK, ECALL, UNIMP = 0x10200073, 0x10500073, 0x00100073, 0x00000073, 0xC0001073
C_EBREAK = 0x9002
C = "defined(C_SUPPORTED) || defined(ZCA_SUPPORTED)"
NO_C = "!defined(C_SUPPORTED) && !defined(ZCA_SUPPORTED)"
H = "defined(H_SUPPORTED)"
S1P12 = "defined(S1P12P0_OR_LATER_SUPPORTED)"
POOL_INT = ["x6", "x7", "x8", "x9"]  # tests that call the framework's jal interrupt hooks (they clobber x1)


def icause(code: int) -> X:
    """xcause of interrupt `code`."""
    return X((1 << 31) | code, (1 << 63) | code)


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


def cbo(op: str, rs1: int) -> int:
    """CBO.{inval,clean,flush,zero} encoding with base register rs1."""
    imm = {"inval": 0, "clean": 1, "flush": 2, "zero": 4}[op]
    return (imm << 20) | (rs1 << 15) | (2 << 12) | 0x0F


# ---------------------------------------------------------------- code helpers
def delay(t: TestFile, n: int = 50, reg: str = "x9") -> None:
    """Bounded wait loop (no checks inside)."""
    loop = t.label("delay")
    t.li(reg, n)
    t.emit(f"{loop}:", 0)
    t.emit(f"addi {reg}, {reg}, -1", n)
    t.emit(f"bnez {reg}, {loop}", n)


def bits(t: TestFile, csr: str, mask: int, on: bool, reg: str = "x6") -> None:
    """S-mode csrs/csrc of a constant mask (32-bit signed-safe)."""
    t.li(reg, mask)
    t.emit(f"{'csrs' if on else 'csrc'} {csr}, {reg}")


def m_bits(t: TestFile, csr: str, mask: int, on: bool) -> None:
    """M-mode (T-SBI) set or clear of mask in M-level CSR csr."""
    t.comment(f"M-mode: {csr} {'|=' if on else '&= ~'}{hex(mask)}")
    t.tsbi_csr("SET" if on else "CLEAR", csr.upper(), imm=mask)


def poll_sip(t: TestFile, bit: int, until: int, n: int = 200, reg: str = "x8") -> None:
    """Read sip & bit into reg until it is nonzero (until=1) or zero (until=0), at most n times."""
    loop, done = t.label("wait"), t.label("waitdone")
    t.li("x9", n)
    t.li("x5", bit)
    t.emit(f"{loop}:", 0)
    t.emit(f"csrr {reg}, sip", n)
    t.emit(f"and {reg}, {reg}, x5", n)
    t.emit(f"{'bnez' if until else 'beqz'} {reg}, {done}", n)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)
    t.emit(f"{done}:", 0)


# ---------------------------------------------------------------- interrupt sources
SRC = {"SSI": 1, "STI": 5, "SEI": 9}
PRIO = ["SEI", "SSI", "STI"]  # decreasing priority (sip_sie_priority_bit_order)


def raise_int(t: TestFile, src: str) -> None:
    """Raise src with sstatus.SIE cleared first (an SRET may have left SIE=1), so it is not taken in S-mode here."""
    t.comment(f"raise {src}")
    bits(t, "sstatus", SIE, False)
    if src == "SSI":
        t.emit("csrsi sip, 2  // sip.SSIP = 1")
    elif src == "STI":
        t.emit("RVTEST_SET_STIME_INT_S  // M-mode mip.STIP = 1 (T-SBI)", 130)
    else:
        t.emit("RVTEST_SET_SEXT_INT_S  // platform SEI or M-mode mip.SEIP = 1", 150)
    poll_sip(t, 1 << SRC[src], 1)


def lower_int(t: TestFile, src: str) -> None:
    t.comment(f"lower {src}")
    if src == "SSI":
        t.emit("csrci sip, 2  // sip.SSIP = 0")
    elif src == "STI":
        t.emit("RVTEST_CLR_STIME_INT_S  // M-mode mip.STIP = 0 (T-SBI)", 130)
    else:
        t.emit("RVTEST_CLR_SEXT_INT_S", 150)
    poll_sip(t, 1 << SRC[src], 0)


def probe_ie(t: TestFile, src: str, reg: str = "x7") -> None:
    """reg = 1 if sie bit of src is writable (the interrupt is implemented, sie_acc), else 0. sie bit left 0."""
    b = 1 << SRC[src]
    t.comment(f"probe: is sie bit {SRC[src]} ({src}) writable?")
    t.li(reg, b)
    t.emit(f"csrs sie, {reg}")
    t.emit(f"csrr {reg}, sie")
    t.emit(f"csrc sie, {reg}")
    t.emit(f"srli {reg}, {reg}, {SRC[src]}")
    t.emit(f"andi {reg}, {reg}, 1")


def with_src(t: TestFile, src: str, body: Callable[[], object]) -> None:
    """Run body only when the src interrupt is implemented (its sie bit is writable)."""
    probe_ie(t, src)
    t.either("x7", body, lambda: t.comment(f"{src} not implemented: nothing to check"))


def with_srcs(t: TestFile, srcs: list[str], body: Callable[[], object]) -> None:
    """Run body only when every interrupt in srcs is implemented."""
    if not srcs:
        body()
        return
    with_src(t, srcs[0], lambda: with_srcs(t, srcs[1:], body))


def int_window(
    t: TestFile,
    srcs: list[str],
    mode: str,
    sie: int,
    en: int,
    pend: int,
    expect: Expect,
    desc: str,
    allow: int = 1,
) -> str:
    """With every interrupt in srcs enabled in sie (en) and pending (pend), run a 50-iteration loop in mode (S or U)
    with sstatus.SIE = sie and check the outcome (expect: "ok" or a cause). In S-mode SIE is set at the start of the
    window; in U-mode SPIE is set so the sret into U copies it into SIE. Returns the window label."""
    mask = sum(1 << SRC[s] for s in srcs)
    t.comment(f"{desc}: sie={hex(mask) if en else 0}, pending={pend}")
    t.li("x6", mask)
    t.emit(f"{'csrs' if en else 'csrc'} sie, x6")
    if pend:
        for s in srcs:
            raise_int(t, s)
    lab = t.label(f"int{mode}")
    if mode == "S":
        t.li("x6", SIE)
        t.allow(allow)
        t.emit(f"{lab}:", 0)
        if sie:
            t.emit("csrs sstatus, x6")
        delay(t)
    else:
        bits(t, "sstatus", SPIE, bool(sie))
        t.allow(allow)
        t.enter("U")
        t.emit(f"{lab}:", 0)
        delay(t)
        t.leave()
    bits(t, "sstatus", SIE, False)
    bits(t, "sie", mask, False)
    t.outcome(expect, lab, desc, epc=False, origin=mode)
    if pend:
        for s in srcs:
            lower_int(t, s)
    return lab


def log_word(t: TestFile, reg: str, back: int, word: str) -> None:
    """reg = word (TRAPLOG_*) of the trap log entry `back` entries before the last one (0 = last)."""
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, {-1 - back}")
    t.emit("andi x5, x5, RVTEST_TRAP_LOG_N-1")
    t.emit("slli x5, x5, TRAPLOG_ENTRY_SHIFT")
    t.emit("LA(x4, rvtest_trap_log)", 2)
    t.emit("add x4, x4, x5")
    t.emit(f"LREG {reg}, ({word})*REGWIDTH(x4)")


def vect(code: int, xlen: int, m0: int = 0) -> int:
    """Vector field (trap log word 0 bits 10:6) of a trap that entered the trampoline's stub `code`
    (rvtest_trap_handler.h sv_<MODE>vect): offset = stub return address - xtvec_new, where xtvec_new is the
    trampoline base plus the framework's MODE bits m0."""
    off = 4 * xlen + 12 * (code + 1) - m0
    return ((off * 3) >> 5) & 0x1F
